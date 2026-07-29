"""Prompt templates and structured-output schemas for the agent nodes."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Structured outputs (used with ChatGoogleGenerativeAI.with_structured_output)
# ---------------------------------------------------------------------------


class RouteDecision(BaseModel):
    """Primary Orchestrator classification of the user's message."""

    route: Literal["data_query", "clarify", "smalltalk", "out_of_scope"] = Field(
        description="data_query = answerable from the database; clarify = ambiguous/underspecified; "
        "smalltalk = greeting/thanks/meta; out_of_scope = not about the firm's data."
    )
    reason: str = Field(description="Brief justification.")
    reply: Optional[str] = Field(
        default=None,
        description="For smalltalk/out_of_scope/clarify: the message to send back to the user.",
    )


class SourceChoice(BaseModel):
    """Which domain database to query (single-domain routing)."""

    source: str = Field(description="The exact name of the single best-fit data source.")
    reason: str = Field(description="Brief justification for the choice.")


class Intent(BaseModel):
    """Structured understanding of a data question."""

    goal: str = Field(description="One-sentence restatement of what the user wants.")
    candidate_tables: list[str] = Field(
        default_factory=list, description="Table names likely needed to answer."
    )
    metrics: list[str] = Field(
        default_factory=list, description="Measures/aggregations requested (e.g. headcount, revenue)."
    )
    filters: list[str] = Field(
        default_factory=list, description="Filter conditions in plain language (e.g. 'London office')."
    )
    group_by: list[str] = Field(default_factory=list, description="Dimensions to group by.")
    time_range: Optional[str] = Field(default=None, description="Any time scope mentioned.")
    ambiguous: bool = Field(default=False, description="True if the request is too vague to answer.")
    clarification: Optional[str] = Field(
        default=None, description="If ambiguous, the question to ask the user."
    )


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

ORCHESTRATOR_SYSTEM = """You are the Primary Orchestrator of a text-to-SQL analytics \
assistant for a professional-services firm (audit, tax, accounting, advisory + HR).

Classify the user's latest message:
- data_query: a question that can be answered by querying the firm's database.
- clarify: about the data but too ambiguous/underspecified to write a correct query.
- smalltalk: greetings, thanks, or questions about you/your capabilities.
- out_of_scope: unrelated to the firm's data (e.g. general knowledge, coding help).

For smalltalk, out_of_scope, and clarify, also write a short, friendly `reply`.
Prefer data_query when a reasonable query could answer the question."""

ROUTER_SYSTEM = """You route a data question to exactly ONE database. Each database
covers a distinct business domain; pick the single best fit for answering the
question. Choose the `source` from these names only:

{sources}

If the question could touch several, choose the one holding the primary facts it
asks about (e.g. salaries -> HR; billable hours -> audit; tax filings -> tax;
invoices/revenue -> billing)."""

INTENT_SYSTEM = """You are the Intent Analysis step of a text-to-SQL agent.
Extract a precise, structured intent from the user's question about the firm's database.
Use the available tables/columns and business glossary to choose candidate_tables and
metrics. Only set ambiguous=true if you truly cannot proceed without more information
(e.g. an undefined term or missing time period that changes the answer materially).

Available tables and business context:
{schema_overview}

{correction_block}"""

SQL_GENERATION_SYSTEM = """You are an expert PostgreSQL analyst. Write ONE read-only \
SELECT query that answers the user's question. Rules:
- PostgreSQL dialect only. Output SQL and nothing else (no prose, no markdown fences).
- SELECT only. Never write INSERT/UPDATE/DELETE/DDL.
- Only use tables and columns that appear in the schema below.
- Prefer the provided METRIC DEFINITIONS and GLOSSARY for business terms.
- For an employee's "current" salary, use the latest compensation row per employee.
- Fiscal year runs Jul 1 - Jun 30; 'FY2025' ends 30 Jun 2025. Engagements carry a
  fiscal_year label; use it for FY filters. Use CURRENT_DATE for relative dates.
- Qualify columns with table names/aliases in joins. Add ORDER BY for "top/most/least".

=== SCHEMA & BUSINESS CONTEXT ===
{schema_context}

=== STRUCTURED INTENT ===
{intent}

{few_shot_block}
{correction_block}"""

SELF_CORRECTION_SYSTEM = """You are the Self-Correction step of a text-to-SQL agent.
A generated PostgreSQL query failed. Diagnose the root cause and give concrete, specific
guidance for the next attempt (correct table/column names, join keys, casts, filters).
Do NOT rewrite the whole query yourself — produce a short set of correction notes that
the Intent Analysis and SQL generation steps will use.

Schema (names you must respect):
{schema_overview}

Failed SQL:
{sql}

Error:
{error}"""

ANSWER_SYSTEM = """You explain query results to a business user in the professional-services \
firm. Given the question, the SQL, and the result rows, write a concise, direct answer.
- Lead with the answer. Use specific numbers from the rows.
- If many rows, summarize the top ones; don't dump the whole table.
- Format currency and large numbers readably. Do not invent data not in the rows.
- Keep it to a few sentences."""


def render_few_shots(few_shots: list[dict[str, str]]) -> str:
    if not few_shots:
        return ""
    blocks = ["=== EXAMPLES (question -> SQL) ==="]
    for ex in few_shots:
        blocks.append(f"Q: {ex['question']}\nSQL:\n{ex['sql']}")
    return "\n\n".join(blocks)


def render_correction_block(notes: str | None) -> str:
    if not notes:
        return ""
    return f"=== CORRECTION NOTES FROM PREVIOUS ATTEMPT ===\n{notes}"
