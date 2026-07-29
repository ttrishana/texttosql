"""SQL Execution node: guardrail-validate, then run read-only against Postgres."""

from __future__ import annotations

from ...config import get_settings
from ...knowledge.registry import get_registry
from ..guardrails import validate_sql
from ..state import AgentState


def sql_execution(state: AgentState) -> dict:
    settings = get_settings()
    source = get_registry().get(state.get("data_source"))
    catalog = source.catalog()
    attempts = state.get("attempts", 0) + 1

    result = validate_sql(state["sql"], set(catalog.all_table_names()), settings.result_row_cap)
    if not result.ok:
        # a validation failure is treated as an error the self-correction loop can fix
        return {"attempts": attempts, "validation_error": result.error,
                "exec_error": None, "rows": None, "columns": None, "row_count": None}

    try:
        columns, rows = source.run_query(result.sql, settings.result_row_cap)
        return {"attempts": attempts, "sql": result.sql, "columns": columns, "rows": rows,
                "row_count": len(rows), "exec_error": None, "validation_error": None}
    except Exception as e:  # DB error -> feedback for self-correction
        return {"attempts": attempts, "sql": result.sql, "exec_error": str(e),
                "validation_error": None, "rows": None, "columns": None, "row_count": None}
