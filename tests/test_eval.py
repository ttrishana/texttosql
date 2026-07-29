"""End-to-end eval harness (requires a seeded database; agent tests also need GOOGLE_API_KEY).

Works in single-DB or multi-DB mode: each golden SQL runs against whichever source
holds its tables, and the agent tests assert the router picks the expected source.

Run:  python scripts/init_db.py && pytest tests/test_eval.py -v
"""

from __future__ import annotations

import uuid

import pytest
import yaml

from texttosql.config import get_settings
from texttosql.knowledge.catalog import FEW_SHOTS_PATH, _sql_tables


def _few_shots():
    return yaml.safe_load(FEW_SHOTS_PATH.read_text())


def _source_holding(sql: str):
    """Return the registry source whose tables cover this SQL, or None."""
    from texttosql.knowledge.registry import get_registry

    need = _sql_tables(sql)
    registry = get_registry()
    for name in registry.names():
        source = registry.get(name)
        try:
            have = {t.lower() for t in source.catalog().all_table_names()}
        except Exception:
            continue
        if need <= have:
            return source
    return None


@pytest.mark.parametrize("example", _few_shots(), ids=lambda e: e["question"][:40])
def test_golden_sql_executes(example, db_available):
    """Every curated SQL runs, against the source that owns its tables."""
    if not db_available:
        pytest.skip("Postgres not reachable; run `python scripts/init_db.py`.")
    source = _source_holding(example["sql"])
    if source is None:
        pytest.skip("No single source holds this query's tables (cross-domain).")
    columns, _ = source.run_query(example["sql"])
    assert isinstance(columns, list)


# (question, expected single-domain source) — each answerable from one database.
AGENT_QUESTIONS = [
    ("How many active employees are there by grade?", "hr"),
    ("What is the total amount across all paid invoices?", "billing"),
    ("How many audit findings are still open?", "audit"),
    ("How many tax returns have been filed?", "tax"),
]


@pytest.mark.parametrize("question,expected_source", AGENT_QUESTIONS)
def test_agent_answers(question, expected_source, db_available):
    """Full graph: routes to data_query, picks the right source, returns an answer."""
    if not db_available:
        pytest.skip("Postgres not reachable.")
    if not get_settings().google_api_key:
        pytest.skip("GOOGLE_API_KEY not set; agent (LLM) tests skipped.")

    from texttosql.agent.graph import run_query

    state = run_query(question, thread_id=str(uuid.uuid4()))
    assert state.get("route") == "data_query"
    if get_settings().multi_db:
        assert state.get("data_source") == expected_source
    assert state.get("answer")
    assert state.get("rows") is not None
    assert not (state.get("validation_error") or state.get("exec_error"))
