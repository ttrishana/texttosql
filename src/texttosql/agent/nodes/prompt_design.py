"""Prompt Design node: assemble knowledge-layer context and generate the SQL.

Faithful to the diagram, this node both *designs the prompt* (pulling relevant
schema + few-shots from the Semantic Metadata) and produces the candidate SQL
that flows into SQL Execution.
"""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from ...knowledge.registry import get_registry
from ...llm import get_llm
from ..prompts import (
    SQL_GENERATION_SYSTEM,
    render_correction_block,
    render_few_shots,
)
from ..state import AgentState


def prompt_design(state: AgentState) -> dict:
    catalog = get_registry().get(state.get("data_source")).catalog()
    question = state["question"]

    schema_context = catalog.render_schema_context()  # full schema (default mode)
    few_shots = catalog.get_few_shots(question, k=6)

    system = SQL_GENERATION_SYSTEM.format(
        schema_context=schema_context,
        intent=json.dumps(state.get("intent") or {}, indent=2, default=str),
        few_shot_block=render_few_shots(few_shots),
        correction_block=render_correction_block(state.get("correction_notes")),
    )
    llm = get_llm("main")
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=question)])
    sql = resp.content if isinstance(resp.content, str) else str(resp.content)

    return {"sql": sql, "schema_context": schema_context, "few_shots": few_shots}
