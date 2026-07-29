"""SQLAlchemy engines and a safe read-only query runner.

Two engines for the single-DB path:
  * admin  -> DDL + seeding (scripts/init_db.py only)
  * readonly -> the default source at query time

Multi-DB sources build their own read-only engines via ``make_readonly_engine``
(see knowledge/registry.py).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, text

from ..config import get_settings


def make_readonly_engine(url: str) -> Engine:
    """Read-only engine for `url`, with a hard per-statement timeout."""
    settings = get_settings()
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"options": f"-c statement_timeout={settings.statement_timeout_ms}"},
    )


@lru_cache
def get_admin_engine(dbname: str | None = None) -> Engine:
    """Engine for the admin role (DDL + seed). Never used at query time."""
    settings = get_settings()
    if settings.embedded_db:
        from .embedded import ADMIN_ROLE, DB_NAME, embedded_url

        return create_engine(embedded_url(ADMIN_ROLE, dbname or DB_NAME), pool_pre_ping=True)
    return create_engine(settings.admin_database_url, pool_pre_ping=True)


@lru_cache
def get_readonly_engine() -> Engine:
    """Read-only engine for the default (single-DB) source."""
    settings = get_settings()
    if settings.embedded_db:
        from .embedded import READONLY_ROLE, embedded_url

        return make_readonly_engine(embedded_url(READONLY_ROLE))
    return make_readonly_engine(settings.readonly_database_url)


def run_query_on(engine: Engine, sql: str, row_cap: int | None = None) -> tuple[list[str], list[dict[str, Any]]]:
    """Execute `sql` on `engine`, returning (columns, rows-as-dicts). Errors propagate."""
    settings = get_settings()
    cap = settings.result_row_cap if row_cap is None else row_cap
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(row) for row in result.mappings().fetchmany(cap)]
    return columns, rows


def run_readonly_query(sql: str, row_cap: int | None = None) -> tuple[list[str], list[dict[str, Any]]]:
    """Execute against the default read-only engine (single-DB helper / tests)."""
    return run_query_on(get_readonly_engine(), sql, row_cap)
