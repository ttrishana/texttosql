"""Respond node: synthesize the natural-language answer (Success path back up).

Also handles the non-data routes (smalltalk/clarify/out_of_scope) whose reply was
set by the orchestrator, and the graceful-failure case when self-correction is
exhausted.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ...llm import get_llm
from ..prompts import ANSWER_SYSTEM
from ..state import AgentState

_PREVIEW_ROWS = 20


def _preview(columns: list[str] | None, rows: list[dict] | None) -> str:
    if not rows:
        return "(no rows)"
    cols = columns or list(rows[0].keys())
    lines = [" | ".join(cols)]
    for r in rows[:_PREVIEW_ROWS]:
        lines.append(" | ".join(str(r.get(c)) for c in cols))
    if len(rows) > _PREVIEW_ROWS:
        lines.append(f"... (+{len(rows) - _PREVIEW_ROWS} more rows)")
    return "\n".join(lines)


def respond(state: AgentState) -> dict:
    route = state.get("route")

    # non-data routes already carry a reply from the orchestrator
    if route != "data_query":
        answer = state.get("answer") or "I'm not sure how to help with that."
        return {"answer": answer, "messages": [AIMessage(content=answer)]}

    error = state.get("validation_error") or state.get("exec_error")
    if error or state.get("rows") is None:
        answer = (
            f"I wasn't able to produce a working query after {state.get('attempts', 0)} attempt(s). "
            f"Last issue: {error or 'no result'}. Could you rephrase or add a bit more detail?"
        )
        return {"answer": answer, "messages": [AIMessage(content=answer)]}

    # success: summarize the rows
    human = (
        f"Question: {state['question']}\n\n"
        f"SQL:\n{state.get('sql')}\n\n"
        f"Result rows ({state.get('row_count', 0)}):\n"
        f"{_preview(state.get('columns'), state.get('rows'))}"
    )
    llm = get_llm("fast")
    resp = llm.invoke([SystemMessage(content=ANSWER_SYSTEM), HumanMessage(content=human)])
    answer = resp.content if isinstance(resp.content, str) else str(resp.content)
    return {"answer": answer, "messages": [AIMessage(content=answer)]}
