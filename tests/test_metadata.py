"""Static validation of the Knowledge Layer (no database required).

Ensures the curated golden SQL parses as a single read-only SELECT over known
tables, and that the semantic model only references tables that exist.
"""

from __future__ import annotations

import yaml

from texttosql.agent.guardrails import validate_sql
from texttosql.knowledge.catalog import FEW_SHOTS_PATH, MODEL_PATH


def _few_shots():
    return yaml.safe_load(FEW_SHOTS_PATH.read_text())


def _model():
    return yaml.safe_load(MODEL_PATH.read_text())


def test_all_golden_sql_pass_guardrails(allowed_tables):
    failures = []
    for ex in _few_shots():
        r = validate_sql(ex["sql"], allowed_tables, 1000)
        if not r.ok:
            failures.append(f"{ex['question']!r}: {r.error}")
    assert not failures, "Invalid golden SQL:\n" + "\n".join(failures)


def test_semantic_model_tables_exist(allowed_tables):
    unknown = [t for t in _model().get("tables", {}) if t.lower() not in allowed_tables]
    assert not unknown, f"semantic_model.yaml references unknown tables: {unknown}"


def test_model_has_metrics_and_glossary():
    model = _model()
    assert model.get("metrics"), "metrics section missing"
    assert model.get("glossary"), "glossary section missing"
    assert model.get("database", {}).get("dialect") == "PostgreSQL"


def test_few_shots_cover_key_domains():
    tags = {t for ex in _few_shots() for t in ex.get("tags", [])}
    for expected in ("hr", "revenue", "tax", "audit", "utilization"):
        assert expected in tags, f"missing few-shot coverage for {expected}"
