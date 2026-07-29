"""Embedded PostgreSQL for Docker-free local testing (via `pgserver`).

`pgserver` ships a real Postgres (with pgvector) as a pip wheel. The server runs
only while a Python process holds it, but the data directory persists on disk, so
seeding once and running the API later both work. Supports multiple databases on
one cluster (used by multi-DB mode). Activated by ``EMBEDDED_DB=true``.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import make_url

from ..config import get_settings

# Module-level singletons: keep the server handle alive for the process lifetime.
_SERVER = None
_SOCKET_DIR: str | None = None

ADMIN_ROLE = "texttosql_admin"
READONLY_ROLE = "texttosql_readonly"
DB_NAME = "firmdb"  # single-DB default


def _superuser_url() -> str:
    return f"postgresql+psycopg://postgres@/postgres?host={_SOCKET_DIR}"


def ensure_embedded_server() -> str:
    """Start (once) the embedded server + the two roles; return its socket dir."""
    global _SERVER, _SOCKET_DIR
    if _SOCKET_DIR is not None:
        return _SOCKET_DIR

    try:
        import pgserver
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "EMBEDDED_DB=true but `pgserver` is not installed. "
            'Run:  pip install -e ".[embedded]"   (or: pip install pgserver)'
        ) from e

    settings = get_settings()
    pgdata = Path(settings.embedded_pgdata).resolve()
    pgdata.mkdir(parents=True, exist_ok=True)

    _SERVER = pgserver.get_server(pgdata)
    _SOCKET_DIR = dict(make_url(_SERVER.get_uri()).query)["host"]

    from .bootstrap import ensure_roles

    ensure_roles(
        _superuser_url(),
        admin_role=ADMIN_ROLE, admin_pw=None,
        readonly_role=READONLY_ROLE, readonly_pw=None,
        statement_timeout=f"{settings.statement_timeout_ms}ms",
        create_extension=True,
    )
    return _SOCKET_DIR


def ensure_database(dbname: str) -> None:
    """Create a database (owned by admin, read-only granted) on the embedded server."""
    ensure_embedded_server()
    from .bootstrap import ensure_database as _ensure_db

    _ensure_db(_superuser_url(), dbname, ADMIN_ROLE, READONLY_ROLE, create_extension=True)


def embedded_url(role: str, dbname: str = DB_NAME) -> str:
    """SQLAlchemy URL for `role` against `dbname` over the embedded server's socket."""
    sock = ensure_embedded_server()
    return f"postgresql+psycopg://{role}@/{dbname}?host={sock}"
