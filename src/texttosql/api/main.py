"""FastAPI Interaction Layer.

Run:  uvicorn texttosql.api.main:app --reload
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import text

from ..agent.graph import build_graph, run_query
from ..config import get_settings
from ..knowledge.registry import get_registry
from .schemas import QueryRequest, QueryResponse, SourceInfo, TableInfo


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.langsmith_tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    # Compile the graph and warm the registry (engines + schema introspection) once.
    app.state.graph = build_graph()
    app.state.registry = get_registry()
    yield


app = FastAPI(title="Text-to-SQL Agent", version="0.1.0", lifespan=lifespan)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")


@app.get("/health")
def health() -> dict:
    registry = app.state.registry
    status: dict[str, bool] = {}
    for name in registry.names():
        try:
            with registry.get(name).engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            status[name] = True
        except Exception:
            status[name] = False
    return {"status": "ok" if all(status.values()) else "degraded", "sources": status}


@app.get("/sources", response_model=list[SourceInfo])
def sources() -> list[SourceInfo]:
    """The domain databases the router can choose from."""
    return [SourceInfo(**s) for s in app.state.registry.summary()]


@app.get("/schema", response_model=list[TableInfo])
def schema(source: str | None = Query(default=None, description="Data source name; default = first.")) -> list[TableInfo]:
    catalog = app.state.registry.get(source).catalog()
    return [TableInfo(**t) for t in catalog.table_summary()]


@app.post("/query", response_model=QueryResponse, dependencies=[Depends(require_api_key)])
def query(req: QueryRequest) -> QueryResponse:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="`question` must not be empty.")
    if req.source and req.source not in app.state.registry.names():
        raise HTTPException(status_code=400, detail=f"Unknown source '{req.source}'.")
    thread_id = req.thread_id or str(uuid.uuid4())

    state = run_query(req.question, thread_id=thread_id, app=app.state.graph, data_source=req.source)

    return QueryResponse(
        thread_id=thread_id,
        route=state.get("route"),
        data_source=state.get("data_source"),
        answer=state.get("answer") or "",
        sql=state.get("sql"),
        columns=state.get("columns"),
        rows=state.get("rows"),
        row_count=state.get("row_count"),
        attempts=state.get("attempts", 0),
        error=state.get("validation_error") or state.get("exec_error"),
    )
