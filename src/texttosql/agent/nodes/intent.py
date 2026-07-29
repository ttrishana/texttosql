"""Intent Analysis node: extract structured intent from a data question."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ...knowledge.registry import get_registry
from ...llm import get_llm
from ..prompts import INTENT_SYSTEM, Intent, render_correction_block
from ..state import AgentState


def intent_analysis(state: AgentState) -> dict:
    catalog = get_registry().get(state.get("data_source")).catalog()
    schema_overview = "\n".join(
        f"- {t['table']}: {t['description']}" for t in catalog.table_summary()
    )
    system = INTENT_SYSTEM.format(
        schema_overview=schema_overview,
        correction_block=render_correction_block(state.get("correction_notes")),
    )
    history = state.get("messages") or [HumanMessage(content=state["question"])]
    llm = get_llm("fast").with_structured_output(Intent)
    intent: Intent = llm.invoke([SystemMessage(content=system), *history])
    return {"intent": intent.model_dump()}
