"""Primary Orchestrator node: classify the request and route the graph."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ...llm import get_llm
from ..prompts import ORCHESTRATOR_SYSTEM, RouteDecision
from ..state import AgentState


def orchestrator(state: AgentState) -> dict:
    history = state.get("messages") or [HumanMessage(content=state["question"])]
    llm = get_llm("fast").with_structured_output(RouteDecision)
    decision: RouteDecision = llm.invoke([SystemMessage(content=ORCHESTRATOR_SYSTEM), *history])

    update: dict = {"route": decision.route}
    if decision.route in ("smalltalk", "out_of_scope", "clarify"):
        update["answer"] = decision.reply or "Could you clarify what you'd like to know about the firm's data?"
    return update
