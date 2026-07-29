"""Create the read/read-only roles and per-domain databases on any superuser Postgres.

Replaces db-init/01-roles.sql for non-Docker setups (embedded, local install,
cloud). Split into `ensure_roles` (cluster-level) and `ensure_database` (per DB)
so multiple domain databases can share one pair of roles. All idempotent.
"""

from __future__ import annotations

import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from ..config import get_settings

_ROLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _normalize(url: str | URL) -> URL:
    u = make_url(url)
    if "+" not in u.drivername:  # ensure psycopg3 driver
        u = u.set(drivername="postgresql+psycopg")
    return u


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def ensure_roles(
    superuser_url: str | URL,
    admin_role: str,
    admin_pw: str | None,
    readonly_role: str,
    readonly_pw: str | None,
    statement_timeout: str = "15s",
    create_extension: bool = True,
) -> None:
    """Create the two roles (cluster-level) + read-only hardening. Idempotent."""
    for role in (admin_role, readonly_role):
        if not _ROLE_RE.match(role):
            raise ValueError(f"Unsafe role name: {role!r}")

    engine = create_engine(_normalize(superuser_url), pool_pre_ping=True)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
        if create_extension:
            try:
                c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception as e:
                print(f"  (note: pgvector extension unavailable: {str(e).splitlines()[0]})")
        for role, pw in ((admin_role, admin_pw), (readonly_role, readonly_pw)):
            if not c.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role}).scalar():
                clause = f" PASSWORD {_quote_literal(pw)}" if pw else ""
                c.execute(text(f'CREATE ROLE "{role}" LOGIN{clause}'))
        c.execute(text(f'ALTER ROLE "{readonly_role}" SET default_transaction_read_only = on'))
        c.execute(text(f'ALTER ROLE "{readonly_role}" SET statement_timeout = {_quote_literal(statement_timeout)}'))


def ensure_database(
    superuser_url: str | URL,
    dbname: str,
    admin_role: str,
    readonly_role: str,
    create_extension: bool = True,
) -> None:
    """Create `dbname` owned by admin + read-only grants. Idempotent."""
    su = _normalize(superuser_url)
    engine = create_engine(su, pool_pre_ping=True)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
        if not c.execute(text("SELECT 1 FROM pg_database WHERE datname = :d"), {"d": dbname}).scalar():
            c.execute(text(f'CREATE DATABASE "{dbname}" OWNER "{admin_role}"'))

    engine_db = create_engine(su.set(database=dbname), pool_pre_ping=True)
    with engine_db.begin() as c:
        if create_extension:
            try:
                c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception:
                pass
        c.execute(text(f'GRANT CREATE, USAGE ON SCHEMA public TO "{admin_role}"'))
        c.execute(text(f'GRANT USAGE ON SCHEMA public TO "{readonly_role}"'))
        c.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{readonly_role}"'))
        c.execute(text(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE "{admin_role}" IN SCHEMA public '
            f'GRANT SELECT ON TABLES TO "{readonly_role}"'
        ))


def bootstrap_roles(
    superuser_url: str | URL,
    admin_role: str,
    admin_pw: str | None,
    readonly_role: str,
    readonly_pw: str | None,
    dbname: str,
    statement_timeout: str = "15s",
    create_extension: bool = True,
) -> None:
    """Roles + one database, in a single call (single-DB convenience)."""
    ensure_roles(superuser_url, admin_role, admin_pw, readonly_role, readonly_pw,
                 statement_timeout, create_extension)
    ensure_database(superuser_url, dbname, admin_role, readonly_role, create_extension)


def bootstrap_from_settings(superuser_url: str | URL, create_extension: bool = True) -> None:
    """Derive role names / passwords / db name from the .env admin+readonly URLs."""
    settings = get_settings()
    admin = make_url(settings.admin_database_url)
    ro = make_url(settings.readonly_database_url)
    bootstrap_roles(
        superuser_url,
        admin_role=admin.username, admin_pw=admin.password,
        readonly_role=ro.username, readonly_pw=ro.password,
        dbname=admin.database,
        statement_timeout=f"{settings.statement_timeout_ms}ms",
        create_extension=create_extension,
    )
