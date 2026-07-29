"""Defense-in-depth SQL validation with sqlglot.

Layered on top of the read-only DB role + statement_timeout. Enforces, before a
query ever reaches the database:
  * a single statement only (blocks stacked ``SELECT 1; DROP TABLE ...``)
  * read-only: the root must be SELECT / set-operation (blocks DML & DDL)
  * every referenced table is in the known schema (CTE aliases excluded)
  * no dangerous functions (pg_sleep, lo_import, pg_read_file, ...)
  * a LIMIT is injected when absent, to cap result size
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

DIALECT = "postgres"

# Root expression types that are acceptable (read-only shapes).
_ALLOWED_ROOTS = tuple(
    c for c in (
        getattr(exp, "Select", None),
        getattr(exp, "Union", None),
        getattr(exp, "Except", None),
        getattr(exp, "Intersect", None),
        getattr(exp, "Subquery", None),
    ) if c is not None
)

# Any of these appearing anywhere is an immediate reject.
_FORBIDDEN_NODES = tuple(
    c for c in (
        getattr(exp, "Insert", None),
        getattr(exp, "Update", None),
        getattr(exp, "Delete", None),
        getattr(exp, "Drop", None),
        getattr(exp, "Create", None),
        getattr(exp, "Alter", None),
        getattr(exp, "Merge", None),
        getattr(exp, "TruncateTable", None),
        getattr(exp, "Command", None),  # COPY, SET, VACUUM, GRANT, ... parse here
    ) if c is not None
)

_BLOCKED_FUNCS = {
    "pg_sleep", "pg_read_file", "pg_read_binary_file", "lo_import", "lo_export",
    "dblink", "dblink_exec", "copy", "pg_ls_dir", "pg_stat_file", "query_to_xml",
    "txid_current", "set_config",
}

_FENCE = re.compile(r"^\s*```(?:sql)?\s*|\s*```\s*$", re.IGNORECASE)


@dataclass
class ValidationResult:
    ok: bool
    sql: str            # cleaned / limit-injected SQL (valid only when ok)
    error: str | None = None


def clean_sql(raw: str) -> str:
    """Strip markdown fences, a leading 'sql' label, and a trailing semicolon."""
    text = _FENCE.sub("", raw.strip())
    text = text.strip()
    if text.endswith(";"):
        text = text[:-1].rstrip()
    return text


def _has_limit(node: exp.Expression) -> bool:
    return node.args.get("limit") is not None


def validate_sql(raw_sql: str, allowed_tables: set[str], row_cap: int) -> ValidationResult:
    sql = clean_sql(raw_sql)
    if not sql:
        return ValidationResult(False, "", "Empty SQL.")

    # single statement only
    try:
        statements = [s for s in sqlglot.parse(sql, read=DIALECT) if s is not None]
    except Exception as e:  # parse error
        return ValidationResult(False, sql, f"Could not parse SQL: {e}")
    if len(statements) != 1:
        return ValidationResult(False, sql, "Only a single SELECT statement is allowed.")

    root = statements[0]

    # forbidden nodes anywhere
    for node_type in _FORBIDDEN_NODES:
        if root.find(node_type) is not None:
            return ValidationResult(False, sql, "Only read-only SELECT queries are allowed.")

    # root must be a read-only shape
    if not isinstance(root, _ALLOWED_ROOTS):
        return ValidationResult(False, sql, "Query must be a SELECT (or set operation of SELECTs).")

    # blocked functions
    for fn in root.find_all(exp.Anonymous, exp.Func):
        name = (fn.name or "").lower()
        if name in _BLOCKED_FUNCS:
            return ValidationResult(False, sql, f"Function '{name}' is not permitted.")

    # every real table must be known (exclude CTE names)
    cte_names = {c.alias_or_name.lower() for c in root.find_all(exp.CTE)}
    allowed = {t.lower() for t in allowed_tables}
    for tbl in root.find_all(exp.Table):
        tname = tbl.name.lower()
        if tname in cte_names:
            continue
        if tname not in allowed:
            return ValidationResult(False, sql, f"Unknown or disallowed table: '{tbl.name}'.")

    # inject LIMIT when missing
    try:
        if not _has_limit(root):
            if isinstance(root, exp.Select):
                root = root.limit(row_cap)
            else:
                root = sqlglot.parse_one(
                    f"SELECT * FROM ({root.sql(dialect=DIALECT)}) AS _capped LIMIT {row_cap}",
                    read=DIALECT,
                )
        final_sql = root.sql(dialect=DIALECT)
    except Exception as e:
        return ValidationResult(False, sql, f"Failed to finalize SQL: {e}")

    return ValidationResult(True, final_sql, None)
