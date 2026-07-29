"""Data-source router: pick which domain database answers the question.

Single-domain routing — chooses exactly one source. With only one source
registered (single-DB mode) it selects it without an LLM call.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ...knowledge.registry import get_registry
from ...llm import get_llm
from ..prompts import ROUTER_SYSTEM, SourceChoice
from ..state import AgentState


def router(state: AgentState) -> dict:
    registry = get_registry()
    names = registry.names()
    if state.get("data_source") in names:  # caller pinned a source (e.g. API override)
        return {"data_source": state["data_source"]}
    if len(names) == 1:
        return {"data_source": names[0]}

    system = ROUTER_SYSTEM.format(sources=registry.render_descriptions())
    history = state.get("messages") or [HumanMessage(content=state["question"])]
    llm = get_llm("fast").with_structured_output(SourceChoice)
    choice: SourceChoice = llm.invoke([SystemMessage(content=system), *history])

    selected = choice.source if choice.source in names else names[0]
    return {"data_source": selected}
