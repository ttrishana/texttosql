"""Guardrail tests (sqlglot only — no database required)."""

from __future__ import annotations

import pytest

from texttosql.agent.guardrails import clean_sql, validate_sql

CAP = 1000


def test_valid_select_passes_and_gets_limit(allowed_tables):
    r = validate_sql("SELECT * FROM employees", allowed_tables, CAP)
    assert r.ok
    assert "limit" in r.sql.lower()


def test_existing_limit_is_respected(allowed_tables):
    r = validate_sql("SELECT * FROM employees LIMIT 5", allowed_tables, CAP)
    assert r.ok
    assert "5" in r.sql


def test_cte_alias_is_not_treated_as_unknown_table(allowed_tables):
    sql = "WITH t AS (SELECT employee_id FROM employees) SELECT * FROM t"
    r = validate_sql(sql, allowed_tables, CAP)
    assert r.ok, r.error


def test_union_is_allowed(allowed_tables):
    sql = "SELECT employee_id FROM employees UNION SELECT client_id FROM clients"
    r = validate_sql(sql, allowed_tables, CAP)
    assert r.ok, r.error


@pytest.mark.parametrize("sql", [
    "DELETE FROM employees",
    "UPDATE employees SET first_name = 'x'",
    "INSERT INTO employees (first_name) VALUES ('x')",
    "DROP TABLE employees",
    "ALTER TABLE employees ADD COLUMN x int",
    "CREATE TABLE hack (id int)",
    "TRUNCATE employees",
])
def test_non_select_is_rejected(sql, allowed_tables):
    r = validate_sql(sql, allowed_tables, CAP)
    assert not r.ok


def test_stacked_statements_rejected(allowed_tables):
    r = validate_sql("SELECT 1; DROP TABLE employees", allowed_tables, CAP)
    assert not r.ok


def test_unknown_table_rejected(allowed_tables):
    r = validate_sql("SELECT * FROM secret_table", allowed_tables, CAP)
    assert not r.ok
    assert "secret_table" in (r.error or "")


def test_blocked_function_rejected(allowed_tables):
    r = validate_sql("SELECT pg_sleep(10)", allowed_tables, CAP)
    assert not r.ok


def test_clean_sql_strips_fences():
    assert clean_sql("```sql\nSELECT 1;\n```") == "SELECT 1"
