"""Shared graph state for the text-to-SQL agent."""

from __future__ import annotations

from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # conversation (enables multi-turn follow-ups via the checkpointer)
    messages: Annotated[list, add_messages]

    # the question under analysis this turn
    question: str

    # orchestrator decision: data_query | clarify | smalltalk | out_of_scope
    route: Optional[str]

    # which data source (domain database) the router selected
    data_source: Optional[str]

    # structured intent from intent_analysis
    intent: Optional[dict[str, Any]]

    # knowledge-layer context assembled for prompt_design
    schema_context: Optional[str]
    few_shots: Optional[list[dict[str, str]]]

    # generated + executed SQL
    sql: Optional[str]
    validation_error: Optional[str]
    exec_error: Optional[str]
    columns: Optional[list[str]]
    rows: Optional[list[dict[str, Any]]]
    row_count: Optional[int]

    # self-correction loop control
    attempts: int
    max_attempts: int
    correction_notes: Optional[str]

    # final natural-language answer returned to the Interaction Layer
    answer: Optional[str]
