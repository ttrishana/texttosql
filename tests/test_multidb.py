"""Multi-database split + registry config tests (no database required)."""

from __future__ import annotations

import re

import yaml

from texttosql.db.schema_split import domain_ddl
from texttosql.knowledge.registry import SOURCES_YAML


def _sources() -> dict:
    return yaml.safe_load(SOURCES_YAML.read_text())["sources"]


def test_sources_reference_only_real_tables(allowed_tables):
    for name, spec in _sources().items():
        unknown = [t for t in spec["tables"] if t.lower() not in allowed_tables]
        assert not unknown, f"source {name!r} lists unknown tables: {unknown}"


def test_domain_ddl_has_no_cross_domain_fks():
    for name, spec in _sources().items():
        keep = {t.lower() for t in spec["tables"]}
        ddl = "\n".join(domain_ddl(spec["tables"]))
        for target in re.findall(r"REFERENCES (\w+)", ddl):
            assert target.lower() in keep, f"source {name!r} keeps cross-domain FK -> {target}"


def test_domain_ddl_creates_every_listed_table():
    for name, spec in _sources().items():
        stmts = domain_ddl(spec["tables"])
        created = {re.match(r"CREATE TABLE (\w+)", s).group(1).lower()
                   for s in stmts if s.upper().startswith("CREATE TABLE")}
        assert created == {t.lower() for t in spec["tables"]}, f"source {name!r} table mismatch"


def test_tables_are_dependency_ordered():
    """A table's kept FK targets must appear earlier in its source's table list."""
    for name, spec in _sources().items():
        seen: set[str] = set()
        pos = {t.lower(): i for i, t in enumerate(spec["tables"])}
        for stmt in domain_ddl(spec["tables"]):
            m = re.match(r"CREATE TABLE (\w+)", stmt)
            if not m:
                continue
            tbl = m.group(1).lower()
            for target in re.findall(r"REFERENCES (\w+)", stmt):
                t = target.lower()
                if t != tbl:  # ignore self-reference (deferrable)
                    assert t in seen, f"{name}: {tbl} references {t} before it is created"
            seen.add(tbl)
