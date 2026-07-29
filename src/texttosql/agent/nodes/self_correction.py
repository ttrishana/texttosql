"""Self-Correction node: diagnose a failed query and write correction notes.

Per the architecture, control then loops back to Intent Analysis so the next
attempt re-grounds itself with the diagnosis in hand.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ...knowledge.registry import get_registry
from ...llm import get_llm
from ..prompts import SELF_CORRECTION_SYSTEM
from ..state import AgentState


def self_correction(state: AgentState) -> dict:
    catalog = get_registry().get(state.get("data_source")).catalog()
    schema_overview = "\n".join(
        f"- {t['table']}({', '.join(t['columns'])})" for t in catalog.table_summary()
    )
    error = state.get("validation_error") or state.get("exec_error") or "unknown error"
    system = SELF_CORRECTION_SYSTEM.format(
        schema_overview=schema_overview, sql=state.get("sql", ""), error=error
    )
    llm = get_llm("main")
    resp = llm.invoke([SystemMessage(content=system),
                       HumanMessage(content="Provide correction notes for the next attempt.")])
    notes = resp.content if isinstance(resp.content, str) else str(resp.content)
    return {"correction_notes": notes}
