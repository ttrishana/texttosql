"""Validate synthetic-data generation logic (no database required)."""

from __future__ import annotations

from datetime import date

from texttosql.db.seed import build_tables

TODAY = date(2026, 7, 28)


def _data(scale=0.2):
    return dict(build_tables(scale=scale, today=TODAY))


def test_referential_integrity():
    data = _data()
    emp = {r["employee_id"] for r in data["employees"]}
    clients = {r["client_id"] for r in data["clients"]}
    eng = {r["engagement_id"] for r in data["engagements"]}
    inv = {r["invoice_id"] for r in data["invoices"]}

    for e in data["employees"]:
        assert e["manager_id"] is None or e["manager_id"] in emp
    for c in data["compensation"]:
        assert c["employee_id"] in emp
    for en in data["engagements"]:
        assert en["client_id"] in clients
        assert en["partner_id"] is None or en["partner_id"] in emp
    for t in data["time_entries"]:
        assert t["engagement_id"] in eng and t["employee_id"] in emp
    for i in data["invoices"]:
        assert i["client_id"] in clients
    for li in data["invoice_line_items"]:
        assert li["invoice_id"] in inv
    for tr in data["tax_returns"]:
        assert tr["engagement_id"] in eng
    for af in data["audit_findings"]:
        assert af["engagement_id"] in eng


def test_reasonable_volumes_and_shape():
    data = _data()
    assert len(data["employees"]) > 50
    assert len(data["time_entries"]) > len(data["engagements"])
    # tax returns only for Tax engagements; findings only for Audit engagements
    tax_eng = {e["engagement_id"] for e in data["engagements"] if e["engagement_type"] == "Tax"}
    assert all(tr["engagement_id"] in tax_eng for tr in data["tax_returns"])


def test_deterministic():
    a = _data(0.1)
    b = _data(0.1)
    assert [r["email"] for r in a["employees"]] == [r["email"] for r in b["employees"]]
