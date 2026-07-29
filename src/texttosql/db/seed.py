"""Deterministic synthetic data for the professional-services firm.

Generates a realistic, internally-consistent dataset (FKs wired in Python with
explicit ids, then bulk-inserted via SQLAlchemy reflection). Fiscal year runs
Jul 1 - Jun 30; "FYxxxx" is the calendar year the fiscal year ends.

Call ``seed(engine, scale=1.0)`` after the schema is created.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from faker import Faker
from sqlalchemy import Engine, MetaData

SEED = 42

# ---- reference data ----
OFFICES = [
    ("New York HQ", "New York", "United States", "Americas"),
    ("London", "London", "United Kingdom", "EMEA"),
    ("Toronto", "Toronto", "Canada", "Americas"),
    ("Singapore", "Singapore", "Singapore", "APAC"),
    ("Sydney", "Sydney", "Australia", "APAC"),
    ("Frankfurt", "Frankfurt", "Germany", "EMEA"),
]
# office cost-of-labor multiplier
OFFICE_COST = {"New York": 1.25, "London": 1.2, "Singapore": 1.1,
               "Sydney": 1.05, "Toronto": 1.0, "Frankfurt": 1.05}

SERVICE_LINES = ["Audit", "Tax", "Accounting", "Advisory"]
ENG_TYPE = {"Audit": "Audit", "Tax": "Tax", "Accounting": "Bookkeeping", "Advisory": "Advisory"}

GRADES = [  # (name, rank, base_low, base_high, billing_rate)
    ("Analyst", 1, 60_000, 80_000, 120),
    ("Senior Associate", 2, 80_000, 110_000, 180),
    ("Manager", 3, 110_000, 150_000, 275),
    ("Senior Manager", 4, 150_000, 200_000, 350),
    ("Director", 5, 200_000, 280_000, 450),
    ("Partner", 6, 300_000, 600_000, 650),
]
# grade sampling weights (pyramid: many juniors, few partners)
GRADE_WEIGHTS = [0.34, 0.28, 0.18, 0.10, 0.06, 0.04]

INDUSTRIES = ["Technology", "Manufacturing", "Retail", "Financial Services",
              "Healthcare", "Energy", "Real Estate", "Media", "Transportation"]
SIZE_SEGMENTS = ["SMB", "Mid-Market", "Enterprise"]
CERTS = ["CPA", "ACCA", "CA", "CFA", "EA"]
LEAVE_TYPES = ["annual", "sick", "parental", "unpaid"]
EXPENSE_CATS = ["travel", "meals", "software", "training", "other"]
PAY_METHODS = ["bank_transfer", "card", "check"]
JURISDICTIONS = ["US-Federal", "US-NY", "UK", "CA-Federal", "SG", "AU", "DE"]
RETURN_TYPES = ["corporate", "individual", "vat", "payroll"]
FINDING_CATS = ["revenue_recognition", "internal_controls", "inventory",
                "going_concern", "related_parties", "provisions"]


def _fy_bounds(fy: int) -> tuple[date, date]:
    return date(fy - 1, 7, 1), date(fy, 6, 30)


def _current_fy(today: date) -> int:
    return today.year + 1 if today.month >= 7 else today.year


def _rand_date(start: date, end: date, rnd: random.Random) -> date:
    if end <= start:
        return start
    return start + timedelta(days=rnd.randint(0, (end - start).days))


def build_tables(scale: float = 1.0, today: date | None = None) -> list[tuple[str, list[dict]]]:
    """Generate the full dataset in dependency order (no DB needed).

    Returns a list of ``(table_name, rows)`` tuples. FK integrity is wired in
    Python with explicit ids. Deterministic given SEED and ``today``.
    """
    rnd = random.Random(SEED)
    fake = Faker()
    Faker.seed(SEED)

    today = today or date.today()
    cur_fy = _current_fy(today)
    fiscal_years = [cur_fy - 3, cur_fy - 2, cur_fy - 1, cur_fy]

    n_emp = int(500 * scale)
    n_clients = int(250 * scale)
    n_eng = int(900 * scale)

    # -------- reference tables --------
    offices = [{"office_id": i + 1, "name": n, "city": c, "country": co, "region": r}
               for i, (n, c, co, r) in enumerate(OFFICES)]
    service_lines = [{"service_line_id": i + 1, "name": n} for i, n in enumerate(SERVICE_LINES)]
    grades = [{"grade_id": i + 1, "name": g[0], "rank_order": g[1]} for i, g in enumerate(GRADES)]

    departments = []
    dept_lookup = {}  # (office_id, service_line_id) -> department_id
    did = 0
    for o in offices:
        for sl in service_lines:
            did += 1
            departments.append({"department_id": did, "name": f"{sl['name']} - {o['city']}",
                                "office_id": o["office_id"]})
            dept_lookup[(o["office_id"], sl["service_line_id"])] = did

    # -------- employees --------
    employees = []
    for eid in range(1, n_emp + 1):
        office = rnd.choice(offices)
        sl = rnd.choice(service_lines)
        grade = rnd.choices(grades, weights=GRADE_WEIGHTS, k=1)[0]
        hire = _rand_date(date(cur_fy - 12, 7, 1), today - timedelta(days=30), rnd)
        terminated = rnd.random() < 0.14 and hire < today - timedelta(days=365)
        term_date = _rand_date(hire + timedelta(days=365), today, rnd) if terminated else None
        status = "terminated" if terminated else ("on_leave" if rnd.random() < 0.03 else "active")
        first, last = fake.first_name(), fake.last_name()
        employees.append({
            "employee_id": eid, "first_name": first, "last_name": last,
            "email": f"{first.lower()}.{last.lower()}{eid}@firm.example",
            "office_id": office["office_id"],
            "department_id": dept_lookup[(office["office_id"], sl["service_line_id"])],
            "grade_id": grade["grade_id"], "service_line_id": sl["service_line_id"],
            "manager_id": None,  # filled below
            "hire_date": hire, "termination_date": term_date,
            "employment_status": status,
            "birth_date": _rand_date(date(cur_fy - 60, 1, 1), date(cur_fy - 23, 1, 1), rnd),
        })

    # manager assignment: someone more senior in the same office & service line
    by_group: dict[tuple[int, int], list[dict]] = {}
    for e in employees:
        by_group.setdefault((e["office_id"], e["service_line_id"]), []).append(e)
    for e in employees:
        peers = by_group[(e["office_id"], e["service_line_id"])]
        seniors = [p for p in peers if p["grade_id"] > e["grade_id"]]
        if seniors:
            e["manager_id"] = rnd.choice(seniors)["employee_id"]

    partners = [e for e in employees if e["grade_id"] == 6]
    managers_plus = [e for e in employees if e["grade_id"] >= 3]

    # -------- compensation history --------
    compensation = []
    cid = 0
    grade_by_id = {g["grade_id"]: g for g in grades}
    for e in employees:
        g = GRADES[e["grade_id"] - 1]
        mult = OFFICE_COST[offices[e["office_id"] - 1]["city"]]
        base = rnd.uniform(g[2], g[3]) * mult
        n_hist = rnd.randint(1, 4)
        eff = e["hire_date"]
        for k in range(n_hist):
            cid += 1
            salary = round(base * (0.9 + 0.05 * k), -2)
            compensation.append({"comp_id": cid, "employee_id": e["employee_id"],
                                 "effective_date": eff, "base_salary": salary,
                                 "bonus_target_pct": round(5 + g[1] * 3 + rnd.uniform(0, 5), 1),
                                 "currency": "USD"})
            eff = _rand_date(eff + timedelta(days=200), eff + timedelta(days=500), rnd)
            if eff > today:
                break

    # -------- performance reviews --------
    reviews = []
    rid = 0
    for e in employees:
        for fy in fiscal_years[:-1]:  # completed years
            _, fy_end = _fy_bounds(fy)
            if e["hire_date"] > fy_end:
                continue
            rid += 1
            reviews.append({"review_id": rid, "employee_id": e["employee_id"],
                            "review_period": f"FY{fy}", "rating": round(rnd.uniform(2.5, 5.0), 1),
                            "reviewer_id": e["manager_id"],
                            "review_date": _fy_bounds(fy)[1] + timedelta(days=rnd.randint(10, 40))})

    # -------- certifications --------
    certifications = []
    cert_id = 0
    for e in employees:
        p = 0.2 + 0.12 * (e["grade_id"] - 1)  # seniors more likely certified
        if rnd.random() < min(p, 0.9):
            cert_id += 1
            obtained = _rand_date(e["hire_date"], today, rnd)
            certifications.append({"cert_id": cert_id, "employee_id": e["employee_id"],
                                   "name": rnd.choice(CERTS), "obtained_date": obtained,
                                   "expiry_date": obtained + timedelta(days=365 * 3)})

    # -------- leave --------
    leave_rows = []
    lid = 0
    for e in employees:
        for _ in range(rnd.randint(0, 4)):
            lid += 1
            start = _rand_date(max(e["hire_date"], today - timedelta(days=730)), today, rnd)
            days = rnd.randint(1, 10)
            leave_rows.append({"leave_id": lid, "employee_id": e["employee_id"],
                               "leave_type": rnd.choice(LEAVE_TYPES), "start_date": start,
                               "end_date": start + timedelta(days=days), "days": days})

    # -------- clients --------
    clients = []
    for cl in range(1, n_clients + 1):
        clients.append({"client_id": cl, "name": fake.company(),
                        "industry": rnd.choice(INDUSTRIES), "country": rnd.choice([o["country"] for o in offices]),
                        "size_segment": rnd.choices(SIZE_SEGMENTS, weights=[0.5, 0.35, 0.15])[0],
                        "onboarded_date": _rand_date(date(cur_fy - 8, 1, 1), today, rnd),
                        "status": rnd.choices(["active", "churned", "prospect"], weights=[0.8, 0.12, 0.08])[0]})

    # -------- engagements --------
    engagements = []
    for eng_id in range(1, n_eng + 1):
        client = rnd.choice(clients)
        sl = rnd.choice(service_lines)
        fy = rnd.choices(fiscal_years, weights=[0.2, 0.25, 0.3, 0.25])[0]
        fy_start, fy_end = _fy_bounds(fy)
        start = _rand_date(fy_start, fy_start + timedelta(days=120), rnd)
        # every engagement carries a planned/expected end_date (populated even
        # while in progress), so date-range filters on end_date behave sensibly.
        end = start + timedelta(days=rnd.randint(30, 180))
        if fy == cur_fy:
            status = rnd.choices(["planned", "in_progress"], weights=[0.2, 0.8])[0]
        else:
            status = rnd.choices(["completed", "on_hold"], weights=[0.92, 0.08])[0]
        budget_hours = rnd.randint(150, 2500)
        engagements.append({
            "engagement_id": eng_id, "client_id": client["client_id"],
            "service_line_id": sl["service_line_id"], "engagement_type": ENG_TYPE[sl["name"]],
            "name": f"{sl['name']} FY{fy} - {client['name']}", "fiscal_year": f"FY{fy}",
            "start_date": start, "end_date": end, "status": status,
            "partner_id": rnd.choice(partners)["employee_id"] if partners else None,
            "manager_id": rnd.choice(managers_plus)["employee_id"] if managers_plus else None,
            "budget_amount": round(budget_hours * rnd.uniform(180, 320), -2),
            "budgeted_hours": budget_hours, "currency": "USD"})

    # -------- staffing --------
    staffing = []
    eng_staff: dict[int, list[int]] = {}
    sid = 0
    active_emps = [e for e in employees if e["employment_status"] != "terminated"]
    for eng in engagements:
        team_size = rnd.randint(3, 8)
        team = rnd.sample(active_emps, min(team_size, len(active_emps)))
        eng_staff[eng["engagement_id"]] = [e["employee_id"] for e in team]
        for e in team:
            sid += 1
            role = grade_by_id[e["grade_id"]]["name"]
            staffing.append({"staffing_id": sid, "engagement_id": eng["engagement_id"],
                             "employee_id": e["employee_id"], "role": role,
                             "allocation_pct": rnd.choice([25, 50, 75, 100])})

    # -------- time entries --------
    emp_by_id = {e["employee_id"]: e for e in employees}
    time_entries = []
    tid = 0
    for eng in engagements:
        w_start = eng["start_date"]
        w_end = min(eng["end_date"] or today, today)
        if w_end <= w_start:
            continue
        for emp_id in eng_staff[eng["engagement_id"]]:
            g = GRADES[emp_by_id[emp_id]["grade_id"] - 1]
            for _ in range(rnd.randint(6, 22)):
                tid += 1
                billable = rnd.random() < 0.85
                time_entries.append({
                    "time_entry_id": tid, "engagement_id": eng["engagement_id"],
                    "employee_id": emp_id, "entry_date": _rand_date(w_start, w_end, rnd),
                    "hours": round(rnd.uniform(1, 9), 1), "billable": billable,
                    "billing_rate": g[4] + rnd.randint(-20, 40) if billable else None,
                    "task_description": fake.sentence(nb_words=6)})

    # -------- invoices / line items / payments --------
    invoices, line_items, payments = [], [], []
    inv_id = line_id = pay_id = 0
    for eng in engagements:
        if eng["status"] == "planned":
            continue
        for _ in range(rnd.randint(1, 3)):
            inv_id += 1
            inv_date = _rand_date(eng["start_date"], min(eng["end_date"] or today, today), rnd)
            due = inv_date + timedelta(days=30)
            amount = round(rnd.uniform(0.15, 0.5) * float(eng["budget_amount"]), 2)
            country = clients[eng["client_id"] - 1]["country"]
            tax_rate = 0.20 if country in ("United Kingdom", "Germany") else 0.0
            if due < today:
                status = rnd.choices(["paid", "overdue"], weights=[0.85, 0.15])[0]
            else:
                status = "sent"
            invoices.append({"invoice_id": inv_id, "client_id": eng["client_id"],
                             "engagement_id": eng["engagement_id"], "invoice_date": inv_date,
                             "due_date": due, "amount": amount,
                             "tax_amount": round(amount * tax_rate, 2), "currency": "USD",
                             "status": status})
            # line items summing to amount
            n_lines = rnd.randint(1, 4)
            remaining = amount
            for li in range(n_lines):
                line_id += 1
                line_amt = round(remaining if li == n_lines - 1 else remaining * rnd.uniform(0.2, 0.6), 2)
                remaining = round(remaining - line_amt, 2)
                line_items.append({"line_id": line_id, "invoice_id": inv_id,
                                   "description": rnd.choice(["Professional fees", "Advisory hours",
                                                              "Audit fieldwork", "Tax preparation"]),
                                   "quantity": 1, "unit_price": line_amt, "amount": line_amt})
            if status == "paid":
                pay_id += 1
                payments.append({"payment_id": pay_id, "invoice_id": inv_id,
                                 "payment_date": _rand_date(inv_date, due + timedelta(days=25), rnd),
                                 "amount": round(amount * (1 + tax_rate), 2),
                                 "method": rnd.choice(PAY_METHODS)})

    # -------- expenses --------
    expenses = []
    exp_id = 0
    for eng in engagements:
        for _ in range(rnd.randint(0, 6)):
            exp_id += 1
            expenses.append({"expense_id": exp_id, "engagement_id": eng["engagement_id"],
                             "employee_id": rnd.choice(eng_staff[eng["engagement_id"]]),
                             "expense_date": _rand_date(eng["start_date"], min(eng["end_date"] or today, today), rnd),
                             "category": rnd.choice(EXPENSE_CATS), "amount": round(rnd.uniform(20, 2000), 2),
                             "billable": rnd.random() < 0.4, "reimbursed": rnd.random() < 0.7})

    # -------- tax returns (Tax engagements) --------
    tax_returns = []
    tr_id = 0
    for eng in engagements:
        if eng["engagement_type"] != "Tax":
            continue
        tr_id += 1
        tax_year = int(eng["fiscal_year"][2:]) - 1
        due = date(tax_year + 1, 4, 15)
        if due < today:
            filing = rnd.choices(["filed", "amended", "in_prep"], weights=[0.85, 0.05, 0.10])[0]
        else:
            filing = rnd.choices(["not_started", "in_prep", "filed"], weights=[0.4, 0.45, 0.15])[0]
        filed_date = _rand_date(due - timedelta(days=60), due, rnd) if filing in ("filed", "amended") else None
        tax_returns.append({"return_id": tr_id, "client_id": eng["client_id"],
                            "engagement_id": eng["engagement_id"], "tax_year": tax_year,
                            "jurisdiction": rnd.choice(JURISDICTIONS), "return_type": rnd.choice(RETURN_TYPES),
                            "filing_status": filing, "filed_date": filed_date, "due_date": due,
                            "balance_amount": round(rnd.uniform(-50_000, 200_000), 2)})

    # -------- audit findings (Audit engagements) --------
    audit_findings = []
    af_id = 0
    for eng in engagements:
        if eng["engagement_type"] != "Audit":
            continue
        for _ in range(rnd.randint(0, 5)):
            af_id += 1
            identified = _rand_date(eng["start_date"], min(eng["end_date"] or today, today), rnd)
            severity = rnd.choices(["low", "medium", "high"], weights=[0.5, 0.35, 0.15])[0]
            resolved = rnd.random() < (0.75 if severity != "high" else 0.5)
            audit_findings.append({"finding_id": af_id, "engagement_id": eng["engagement_id"],
                                   "severity": severity, "category": rnd.choice(FINDING_CATS),
                                   "description": fake.sentence(nb_words=10),
                                   "status": "resolved" if resolved else "open",
                                   "identified_date": identified,
                                   "resolved_date": identified + timedelta(days=rnd.randint(5, 90)) if resolved else None})

    # -------- bulk insert (dependency order) --------
    table_data = [
        ("offices", offices), ("service_lines", service_lines), ("departments", departments),
        ("grades", grades), ("employees", employees), ("compensation", compensation),
        ("performance_reviews", reviews), ("certifications", certifications), ("leave", leave_rows),
        ("clients", clients), ("engagements", engagements), ("engagement_staffing", staffing),
        ("time_entries", time_entries), ("invoices", invoices), ("invoice_line_items", line_items),
        ("payments", payments), ("expenses", expenses), ("tax_returns", tax_returns),
        ("audit_findings", audit_findings),
    ]

    return table_data


def seed(engine: Engine, scale: float = 1.0) -> dict[str, int]:
    """Generate and bulk-insert the full dataset. Returns per-table row counts."""
    table_data = build_tables(scale=scale)
    meta = MetaData()
    meta.reflect(bind=engine)
    counts: dict[str, int] = {}
    with engine.begin() as conn:
        for name, rows in table_data:
            if rows:
                conn.execute(meta.tables[name].insert(), rows)
            counts[name] = len(rows)
    return counts
