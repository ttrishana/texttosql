"""SemanticCatalog: the Knowledge Layer.

Merges the *live* PostgreSQL schema (introspected via SQLAlchemy) with the
curated business overlay in ``semantic_model.yaml`` and the ``few_shots.yaml``
examples, and renders it all into compact context for the SQL-generation prompt.

Default mode passes the full schema (the firm schema is ~19 tables, which fits
comfortably). Few-shots are selected by lexical overlap with the question; when
``RETRIEVAL_MODE`` is on, ``indexer`` can supply embedding-based selection.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import sqlglot
import yaml
from sqlalchemy import Engine, inspect
from sqlglot import exp

_HERE = Path(__file__).resolve().parent
MODEL_PATH = _HERE / "semantic_model.yaml"
FEW_SHOTS_PATH = _HERE / "few_shots.yaml"

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


@lru_cache(maxsize=256)
def _sql_tables(sql: str) -> frozenset[str]:
    """Real tables referenced by a SQL string (CTE aliases excluded)."""
    try:
        root = sqlglot.parse_one(sql, read="postgres")
    except Exception:
        return frozenset()
    ctes = {c.alias_or_name.lower() for c in root.find_all(exp.CTE)}
    return frozenset(t.name.lower() for t in root.find_all(exp.Table) if t.name.lower() not in ctes)


class SemanticCatalog:
    def __init__(
        self,
        engine: Engine,
        model_path: Path = MODEL_PATH,
        few_shots_path: Path = FEW_SHOTS_PATH,
    ) -> None:
        self.engine = engine
        self.model: dict[str, Any] = yaml.safe_load(model_path.read_text())
        self.few_shots: list[dict[str, Any]] = yaml.safe_load(few_shots_path.read_text())
        self._schema = self._introspect()

    # ---- introspection ----
    def _introspect(self) -> dict[str, dict[str, Any]]:
        insp = inspect(self.engine)
        schema: dict[str, dict[str, Any]] = {}
        for table in insp.get_table_names():
            pk = set(insp.get_pk_constraint(table).get("constrained_columns") or [])
            fks = {}
            for fk in insp.get_foreign_keys(table):
                for local, remote in zip(fk["constrained_columns"], fk["referred_columns"]):
                    fks[local] = f"{fk['referred_table']}.{remote}"
            schema[table] = {
                "columns": [
                    {"name": c["name"], "type": str(c["type"]), "nullable": c["nullable"],
                     "pk": c["name"] in pk, "fk": fks.get(c["name"])}
                    for c in insp.get_columns(table)
                ],
            }
        return schema

    # ---- public API ----
    def all_table_names(self) -> list[str]:
        return list(self._schema.keys())

    def dialect(self) -> str:
        return self.model.get("database", {}).get("dialect", "PostgreSQL")

    def render_schema_context(self, tables: list[str] | None = None) -> str:
        """Render tables (default: all) + metrics + glossary as prompt text."""
        names = tables or self.all_table_names()
        model_tables = self.model.get("tables", {})
        blocks: list[str] = []
        db_desc = self.model.get("database", {}).get("description", "")
        if db_desc:
            blocks.append(f"DATABASE: {db_desc.strip()}")

        for name in names:
            if name not in self._schema:
                continue
            overlay = model_tables.get(name, {})
            header = f"TABLE {name}"
            if overlay.get("description"):
                header += f" — {overlay['description'].strip()}"
            lines = [header]
            if overlay.get("synonyms"):
                lines.append(f"  synonyms: {', '.join(overlay['synonyms'])}")
            lines.append("  columns:")
            col_overlay = overlay.get("columns", {})
            for col in self._schema[name]["columns"]:
                parts = [f"    {col['name']} {col['type'].lower()}"]
                if col["pk"]:
                    parts.append("PK")
                if col["fk"]:
                    parts.append(f"FK->{col['fk']}")
                co = col_overlay.get(col["name"], {})
                if co.get("description"):
                    parts.append(f"# {co['description']}")
                if co.get("enum"):
                    parts.append(f"[values: {', '.join(map(str, co['enum']))}]")
                lines.append(" ".join(parts))
            if overlay.get("joins"):
                lines.append("  joins:")
                lines.extend(f"    {j}" for j in overlay["joins"])
            if overlay.get("notes"):
                lines.append(f"  note: {overlay['notes']}")
            blocks.append("\n".join(lines))

        metrics = self.model.get("metrics", {})
        if metrics:
            mlines = ["METRIC DEFINITIONS (prefer these for the matching business terms):"]
            for mname, m in metrics.items():
                line = f"  {mname}: {m.get('description', '')}"
                if m.get("sql"):
                    line += f"  ->  {m['sql']}"
                mlines.append(line)
            blocks.append("\n".join(mlines))

        glossary = self.model.get("glossary", {})
        if glossary:
            glines = ["GLOSSARY:"]
            glines.extend(f"  {k}: {v}" for k, v in glossary.items())
            blocks.append("\n".join(glines))

        return "\n\n".join(blocks)

    def get_few_shots(self, question: str, k: int = 6) -> list[dict[str, str]]:
        """Return up to k examples most similar to the question that reference
        only tables present in this source."""
        allowed = {t.lower() for t in self.all_table_names()}
        q = _tokens(question)
        scored = []
        for ex in self.few_shots:
            if _sql_tables(ex["sql"]) - allowed:  # references a table this source lacks
                continue
            overlap = len(q & _tokens(ex["question"] + " " + " ".join(ex.get("tags", []))))
            scored.append((overlap, ex))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [{"question": ex["question"], "sql": ex["sql"].strip()} for _, ex in scored[:k]]

    def table_summary(self) -> list[dict[str, Any]]:
        """Compact catalog for the /schema endpoint."""
        model_tables = self.model.get("tables", {})
        return [
            {"table": name,
             "description": model_tables.get(name, {}).get("description", "").strip(),
             "columns": [c["name"] for c in self._schema[name]["columns"]]}
            for name in self.all_table_names()
        ]


@lru_cache
def get_catalog() -> SemanticCatalog:
    """Cached catalog built against the read-only engine."""
    from ..db.engine import get_readonly_engine

    return SemanticCatalog(get_readonly_engine())
