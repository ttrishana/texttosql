"""Request/response models for the FastAPI layer."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural-language question about the firm's data.")
    thread_id: Optional[str] = Field(
        default=None, description="Conversation id; reuse it for multi-turn follow-ups."
    )
    source: Optional[str] = Field(
        default=None, description="Pin a data source (skips the router). Omit to auto-route."
    )


class QueryResponse(BaseModel):
    thread_id: str
    route: Optional[str]
    data_source: Optional[str] = None
    answer: str
    sql: Optional[str] = None
    columns: Optional[list[str]] = None
    rows: Optional[list[dict[str, Any]]] = None
    row_count: Optional[int] = None
    attempts: int = 0
    error: Optional[str] = None


class TableInfo(BaseModel):
    table: str
    description: str
    columns: list[str]


class SourceInfo(BaseModel):
    name: str
    description: str
    tables: list[str]
