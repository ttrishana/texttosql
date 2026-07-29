"""LangGraph wiring for the SQL Agent ReAct loop.

    START -> orchestrator --(data_query)--> router -> intent_analysis -> prompt_design -> sql_execution
                         \--(else)-----------------------------------------------------> respond
    router picks the data source (domain database); single-DB mode selects it trivially.
    sql_execution --(ok)---------------------------------------------------> respond
    sql_execution --(error & attempts<max)--> self_correction -> intent_analysis   (loop)
    sql_execution --(error & attempts==max)-> respond
    respond -> END
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ..config import get_settings
from .nodes.execution import sql_execution
from .nodes.intent import intent_analysis
from .nodes.orchestrator import orchestrator
from .nodes.prompt_design import prompt_design
from .nodes.respond import respond
from .nodes.router import router
from .nodes.self_correction import self_correction
from .state import AgentState


def route_after_orchestrator(state: AgentState) -> str:
    return "router" if state.get("route") == "data_query" else "respond"


def route_after_execution(state: AgentState) -> str:
    failed = bool(state.get("validation_error") or state.get("exec_error"))
    if not failed:
        return "respond"
    if state.get("attempts", 0) < state.get("max_attempts", 3):
        return "self_correction"
    return "respond"  # exhausted -> graceful failure


def build_graph(checkpointer=None):
    builder = StateGraph(AgentState)
    builder.add_node("orchestrator", orchestrator)
    builder.add_node("router", router)
    builder.add_node("intent_analysis", intent_analysis)
    builder.add_node("prompt_design", prompt_design)
    builder.add_node("sql_execution", sql_execution)
    builder.add_node("self_correction", self_correction)
    builder.add_node("respond", respond)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges("orchestrator", route_after_orchestrator,
                                  {"router": "router", "respond": "respond"})
    builder.add_edge("router", "intent_analysis")
    builder.add_edge("intent_analysis", "prompt_design")
    builder.add_edge("prompt_design", "sql_execution")
    builder.add_conditional_edges("sql_execution", route_after_execution,
                                  {"self_correction": "self_correction", "respond": "respond"})
    builder.add_edge("self_correction", "intent_analysis")
    builder.add_edge("respond", END)

    return builder.compile(checkpointer=checkpointer or MemorySaver())


# A module-level compiled app for the dev CLI / simple reuse.
_APP = None


def get_app():
    global _APP
    if _APP is None:
        _APP = build_graph()
    return _APP


def _fresh_turn_input(question: str, data_source: str | None = None) -> dict:
    """Per-turn input that resets transient fields (checkpointer keeps `messages`)."""
    from langchain_core.messages import HumanMessage

    settings = get_settings()
    return {
        "question": question,
        "messages": [HumanMessage(content=question)],
        "attempts": 0,
        "max_attempts": settings.max_correction_attempts,
        "route": None, "data_source": data_source, "intent": None, "sql": None,
        "schema_context": None, "few_shots": None,
        "validation_error": None, "exec_error": None, "rows": None, "columns": None,
        "row_count": None, "correction_notes": None, "answer": None,
    }


def run_query(question: str, thread_id: str, app=None, data_source: str | None = None) -> AgentState:
    """Run one turn through the graph; `thread_id` groups a conversation.

    Pass `data_source` to pin the domain database (skips the LLM router).
    """
    app = app or get_app()
    settings = get_settings()
    # each correction cycle is ~4 node visits; keep headroom above the default 25
    recursion_limit = max(25, settings.max_correction_attempts * 6 + 6)
    return app.invoke(
        _fresh_turn_input(question, data_source),
        config={"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit},
    )


def _cli() -> None:
    import sys
    import uuid

    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = input("Ask a question about the firm's data: ").strip()

    result = run_query(question, thread_id=str(uuid.uuid4()))

    print("\n=== ROUTE ===\n" + str(result.get("route")))
    if result.get("data_source"):
        print("\n=== DATA SOURCE ===\n" + str(result.get("data_source")))
    if result.get("intent"):
        print("\n=== INTENT ===")
        print(result["intent"].get("goal"))
    if result.get("sql"):
        print("\n=== SQL ===\n" + result["sql"])
    if result.get("validation_error") or result.get("exec_error"):
        print("\n=== ERROR ===\n" + str(result.get("validation_error") or result.get("exec_error")))
    print(f"\n=== ATTEMPTS === {result.get('attempts')}")
    if result.get("rows") is not None:
        print(f"\n=== ROWS ({result.get('row_count')}) ===")
        for row in (result.get("rows") or [])[:10]:
            print(row)
    print("\n=== ANSWER ===\n" + str(result.get("answer")))


if __name__ == "__main__":
    _cli()
