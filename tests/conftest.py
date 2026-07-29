"""Shared test helpers."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SCHEMA_SQL = Path(__file__).resolve().parent.parent / "src" / "texttosql" / "db" / "schema.sql"

_CREATE = re.compile(r"CREATE TABLE (\w+)", re.IGNORECASE)


def schema_tables() -> set[str]:
    """Table names declared in schema.sql (no DB needed)."""
    return {m.group(1).lower() for m in _CREATE.finditer(SCHEMA_SQL.read_text())}


@pytest.fixture(scope="session")
def allowed_tables() -> set[str]:
    return schema_tables()


@pytest.fixture(scope="session")
def db_available() -> bool:
    """True if the first registry source is reachable (else DB-backed tests skip).

    Works in single-DB (source "firm") and multi-DB (first domain database) modes.
    """
    try:
        from sqlalchemy import text

        from texttosql.knowledge.registry import get_registry

        source = get_registry().get(None)
        with source.engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
