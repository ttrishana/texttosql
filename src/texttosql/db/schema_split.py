"""Generate per-domain DDL from the single schema.sql.

For a chosen subset of tables, emit their CREATE TABLE + CREATE INDEX statements
with any foreign key that points *outside* the subset removed (those columns stay
as plain logical keys — realistic for separate operational systems that share ids
but not cross-system FK constraints). The single-DB schema.sql stays the one
source of truth.
"""

from __future__ import annotations

from pathlib import Path

import sqlglot
from sqlglot import exp

SCHEMA_SQL = Path(__file__).resolve().parent / "schema.sql"


def domain_ddl(keep_tables: list[str], all_ddl: str | None = None) -> list[str]:
    """Return ordered DDL statements for `keep_tables` with cross-domain FKs stripped."""
    ddl = all_ddl if all_ddl is not None else SCHEMA_SQL.read_text()
    keep = [t.lower() for t in keep_tables]
    keepset = set(keep)

    creates: dict[str, exp.Create] = {}
    indexes: dict[str, list[exp.Create]] = {}
    for stmt in sqlglot.parse(ddl, read="postgres"):
        if not isinstance(stmt, exp.Create):
            continue
        kind = (stmt.args.get("kind") or "").upper()
        if kind == "TABLE":
            creates[stmt.this.this.name.lower()] = stmt
        elif kind == "INDEX":
            tbl = stmt.find(exp.Table)
            if tbl is not None:
                indexes.setdefault(tbl.name.lower(), []).append(stmt)

    def strip_foreign(node: exp.Expression) -> exp.Expression | None:
        # column-level `... REFERENCES other(col)`
        if isinstance(node, exp.ColumnConstraint) and isinstance(node.kind, exp.Reference):
            tgt = node.kind.find(exp.Table)
            if tgt is not None and tgt.name.lower() not in keepset:
                return None
        # table-level `FOREIGN KEY (...) REFERENCES other(...)`
        if isinstance(node, exp.ForeignKey):
            tgt = node.find(exp.Table)
            if tgt is not None and tgt.name.lower() not in keepset:
                return None
        return node

    def render(node: exp.Expression) -> str:
        node = node.copy()
        for child in node.walk():  # drop schema.sql's banner comments
            child.comments = None
        return node.sql(dialect="postgres", comments=False)

    out: list[str] = []
    for table in keep:
        create = creates.get(table)
        if create is None:
            raise KeyError(f"Table {table!r} not found in schema.sql")
        out.append(render(create.transform(strip_foreign)))
        out.extend(render(idx) for idx in indexes.get(table, []))
    return out
