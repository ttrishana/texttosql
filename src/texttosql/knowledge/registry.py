"""Data-source registry: the multi-database Knowledge Layer.

Each source is one domain database with its own read-only engine + SemanticCatalog.
The router node picks exactly one source per question (single-domain routing).

Single-DB mode (MULTI_DB=false) exposes one source, "firm", so the rest of the
agent has a single code path regardless of how many databases exist.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import Engine

from ..config import get_settings
from ..db.engine import make_readonly_engine, run_query_on
from .catalog import SemanticCatalog

SOURCES_YAML = Path(__file__).resolve().parent / "sources.yaml"


@dataclass
class DataSource:
    name: str
    description: str
    tables: list[str] = field(default_factory=list)  # build-time (schema split); runtime uses introspection
    database: str | None = None  # embedded db name
    url: str | None = None       # explicit read-only URL (external)
    url_env: str | None = None   # or an env var holding it (external)
    _engine: Engine | None = field(default=None, init=False, repr=False)
    _catalog: SemanticCatalog | None = field(default=None, init=False, repr=False)

    def _resolve_url(self) -> str:
        settings = get_settings()
        if self.url:
            return self.url
        if self.url_env:
            val = os.environ.get(self.url_env)
            if not val:
                raise RuntimeError(f"Source {self.name!r}: env var {self.url_env} is not set.")
            return val
        if settings.embedded_db and self.database:
            from ..db.embedded import READONLY_ROLE, embedded_url

            return embedded_url(READONLY_ROLE, self.database)
        # single-DB / non-embedded fallback
        return settings.readonly_database_url

    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = make_readonly_engine(self._resolve_url())
        return self._engine

    def catalog(self) -> SemanticCatalog:
        if self._catalog is None:
            self._catalog = SemanticCatalog(self.engine())
        return self._catalog

    def run_query(self, sql: str, row_cap: int | None = None) -> tuple[list[str], list[dict[str, Any]]]:
        return run_query_on(self.engine(), sql, row_cap)


class DataSourceRegistry:
    def __init__(self, sources: dict[str, DataSource]) -> None:
        if not sources:
            raise ValueError("Registry needs at least one data source.")
        self._sources = sources

    def names(self) -> list[str]:
        return list(self._sources.keys())

    def get(self, name: str | None) -> DataSource:
        if name and name in self._sources:
            return self._sources[name]
        return next(iter(self._sources.values()))  # fallback to the first source

    def render_descriptions(self) -> str:
        return "\n".join(f"- {s.name}: {s.description.strip()}" for s in self._sources.values())

    def summary(self) -> list[dict[str, Any]]:
        return [{"name": s.name, "description": s.description.strip(), "tables": s.tables}
                for s in self._sources.values()]


@lru_cache
def get_registry() -> DataSourceRegistry:
    settings = get_settings()
    if settings.multi_db:
        spec = yaml.safe_load(SOURCES_YAML.read_text())
        sources = {
            name: DataSource(
                name=name,
                description=s["description"],
                tables=s.get("tables", []),
                database=s.get("database"),
                url=s.get("url"),
                url_env=s.get("url_env"),
            )
            for name, s in spec["sources"].items()
        }
        return DataSourceRegistry(sources)

    # single-DB: one "firm" source covering everything
    firm = DataSource(
        name="firm",
        description="The firm's operational database: HR/people, client delivery, tax, and billing.",
        database="firmdb",
    )
    return DataSourceRegistry({"firm": firm})
