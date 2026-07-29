-- =====================================================================
-- Professional-services firm: audit / tax / accounting delivery + HR.
-- Dialect: PostgreSQL. Fiscal year runs Jul 1 - Jun 30.
-- Run as texttosql_admin (owns these tables). Idempotent: drops first.
-- =====================================================================

DROP TABLE IF EXISTS audit_findings CASCADE;
DROP TABLE IF EXISTS tax_returns CASCADE;
DROP TABLE IF EXISTS expenses CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS invoice_line_items CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS time_entries CASCADE;
DROP TABLE IF EXISTS engagement_staffing CASCADE;
DROP TABLE IF EXISTS engagements CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS leave CASCADE;
DROP TABLE IF EXISTS certifications CASCADE;
DROP TABLE IF EXISTS performance_reviews CASCADE;
DROP TABLE IF EXISTS compensation CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS grades CASCADE;
DROP TABLE IF EXISTS departments CASCADE;
DROP TABLE IF EXISTS service_lines CASCADE;
DROP TABLE IF EXISTS offices CASCADE;

-- ---------------------------------------------------------------------
-- Organization / reference
-- ---------------------------------------------------------------------
CREATE TABLE offices (
    office_id   SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL,
    country     TEXT NOT NULL,
    region      TEXT NOT NULL              -- e.g. EMEA, Americas, APAC
);

CREATE TABLE service_lines (
    service_line_id SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE    -- Audit, Tax, Accounting, Advisory
);

CREATE TABLE departments (
    department_id SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    office_id     INT REFERENCES offices(office_id)
);

CREATE TABLE grades (
    grade_id   SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,        -- Analyst .. Partner
    rank_order INT NOT NULL                 -- 1 = most junior
);

-- ---------------------------------------------------------------------
-- People / HR
-- ---------------------------------------------------------------------
CREATE TABLE employees (
    employee_id       SERIAL PRIMARY KEY,
    first_name        TEXT NOT NULL,
    last_name         TEXT NOT NULL,
    email             TEXT UNIQUE NOT NULL,
    office_id         INT REFERENCES offices(office_id),
    department_id     INT REFERENCES departments(department_id),
    grade_id          INT REFERENCES grades(grade_id),
    service_line_id   INT REFERENCES service_lines(service_line_id),
    -- self-reference: DEFERRABLE so bulk loads (a report inserted before its
    -- manager) validate at COMMIT rather than per-row.
    manager_id        INT REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED,
    hire_date         DATE NOT NULL,
    termination_date  DATE,                 -- NULL while still employed
    employment_status TEXT NOT NULL DEFAULT 'active',  -- active | terminated | on_leave
    birth_date        DATE
);

-- Salary history: "current" salary = row with the latest effective_date.
CREATE TABLE compensation (
    comp_id          SERIAL PRIMARY KEY,
    employee_id      INT NOT NULL REFERENCES employees(employee_id),
    effective_date   DATE NOT NULL,
    base_salary      NUMERIC(12,2) NOT NULL,
    bonus_target_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
    currency         TEXT NOT NULL DEFAULT 'USD'
);

CREATE TABLE performance_reviews (
    review_id     SERIAL PRIMARY KEY,
    employee_id   INT NOT NULL REFERENCES employees(employee_id),
    review_period TEXT NOT NULL,            -- e.g. 'FY2025'
    rating        NUMERIC(2,1) NOT NULL,    -- 1.0 .. 5.0
    reviewer_id   INT REFERENCES employees(employee_id),
    review_date   DATE NOT NULL
);

CREATE TABLE certifications (
    cert_id       SERIAL PRIMARY KEY,
    employee_id   INT NOT NULL REFERENCES employees(employee_id),
    name          TEXT NOT NULL,            -- CPA, ACCA, CA, CFA, EA
    obtained_date DATE NOT NULL,
    expiry_date   DATE
);

CREATE TABLE leave (
    leave_id    SERIAL PRIMARY KEY,
    employee_id INT NOT NULL REFERENCES employees(employee_id),
    leave_type  TEXT NOT NULL,              -- annual | sick | parental | unpaid
    start_date  DATE NOT NULL,
    end_date    DATE NOT NULL,
    days        NUMERIC(4,1) NOT NULL
);

-- ---------------------------------------------------------------------
-- Clients & engagements (service delivery)
-- ---------------------------------------------------------------------
CREATE TABLE clients (
    client_id      SERIAL PRIMARY KEY,
    name           TEXT NOT NULL,
    industry       TEXT NOT NULL,
    country        TEXT NOT NULL,
    size_segment   TEXT NOT NULL,           -- SMB | Mid-Market | Enterprise
    onboarded_date DATE NOT NULL,
    status         TEXT NOT NULL DEFAULT 'active'  -- active | churned | prospect
);

CREATE TABLE engagements (
    engagement_id   SERIAL PRIMARY KEY,
    client_id       INT NOT NULL REFERENCES clients(client_id),
    service_line_id INT NOT NULL REFERENCES service_lines(service_line_id),
    engagement_type TEXT NOT NULL,          -- Audit | Tax | Bookkeeping | Advisory
    name            TEXT NOT NULL,
    fiscal_year     TEXT NOT NULL,          -- e.g. 'FY2025'
    start_date      DATE NOT NULL,
    end_date        DATE,
    status          TEXT NOT NULL DEFAULT 'in_progress',  -- planned|in_progress|completed|on_hold
    partner_id      INT REFERENCES employees(employee_id),
    manager_id      INT REFERENCES employees(employee_id),
    budget_amount   NUMERIC(14,2),
    budgeted_hours  NUMERIC(10,2),
    currency        TEXT NOT NULL DEFAULT 'USD'
);

CREATE TABLE engagement_staffing (
    staffing_id    SERIAL PRIMARY KEY,
    engagement_id  INT NOT NULL REFERENCES engagements(engagement_id),
    employee_id    INT NOT NULL REFERENCES employees(employee_id),
    role           TEXT NOT NULL,           -- e.g. Partner, Manager, Senior, Staff
    allocation_pct NUMERIC(5,2) NOT NULL DEFAULT 100
);

CREATE TABLE time_entries (
    time_entry_id    SERIAL PRIMARY KEY,
    engagement_id    INT NOT NULL REFERENCES engagements(engagement_id),
    employee_id      INT NOT NULL REFERENCES employees(employee_id),
    entry_date       DATE NOT NULL,
    hours            NUMERIC(5,2) NOT NULL,
    billable         BOOLEAN NOT NULL DEFAULT true,
    billing_rate     NUMERIC(10,2),
    task_description TEXT
);

-- ---------------------------------------------------------------------
-- Billing / finance
-- ---------------------------------------------------------------------
CREATE TABLE invoices (
    invoice_id   SERIAL PRIMARY KEY,
    client_id    INT NOT NULL REFERENCES clients(client_id),
    engagement_id INT REFERENCES engagements(engagement_id),
    invoice_date DATE NOT NULL,
    due_date     DATE NOT NULL,
    amount       NUMERIC(14,2) NOT NULL,    -- net amount before tax
    tax_amount   NUMERIC(14,2) NOT NULL DEFAULT 0,
    currency     TEXT NOT NULL DEFAULT 'USD',
    status       TEXT NOT NULL DEFAULT 'sent'  -- draft | sent | paid | overdue
);

CREATE TABLE invoice_line_items (
    line_id     SERIAL PRIMARY KEY,
    invoice_id  INT NOT NULL REFERENCES invoices(invoice_id),
    description TEXT NOT NULL,
    quantity    NUMERIC(10,2) NOT NULL DEFAULT 1,
    unit_price  NUMERIC(12,2) NOT NULL,
    amount      NUMERIC(14,2) NOT NULL
);

CREATE TABLE payments (
    payment_id   SERIAL PRIMARY KEY,
    invoice_id   INT NOT NULL REFERENCES invoices(invoice_id),
    payment_date DATE NOT NULL,
    amount       NUMERIC(14,2) NOT NULL,
    method       TEXT NOT NULL             -- bank_transfer | card | check
);

CREATE TABLE expenses (
    expense_id   SERIAL PRIMARY KEY,
    engagement_id INT REFERENCES engagements(engagement_id),
    employee_id  INT NOT NULL REFERENCES employees(employee_id),
    expense_date DATE NOT NULL,
    category     TEXT NOT NULL,            -- travel | meals | software | other
    amount       NUMERIC(12,2) NOT NULL,
    billable     BOOLEAN NOT NULL DEFAULT false,
    reimbursed   BOOLEAN NOT NULL DEFAULT false
);

-- ---------------------------------------------------------------------
-- Service-specific (tax & audit flavor)
-- ---------------------------------------------------------------------
CREATE TABLE tax_returns (
    return_id      SERIAL PRIMARY KEY,
    client_id      INT NOT NULL REFERENCES clients(client_id),
    engagement_id  INT REFERENCES engagements(engagement_id),
    tax_year       INT NOT NULL,
    jurisdiction   TEXT NOT NULL,          -- e.g. US-Federal, UK, CA-Ontario
    return_type    TEXT NOT NULL,          -- corporate | individual | vat | payroll
    filing_status  TEXT NOT NULL DEFAULT 'not_started',  -- not_started|in_prep|filed|amended
    filed_date     DATE,
    due_date       DATE NOT NULL,
    balance_amount NUMERIC(14,2)           -- +owed to authority / -refund
);

CREATE TABLE audit_findings (
    finding_id      SERIAL PRIMARY KEY,
    engagement_id   INT NOT NULL REFERENCES engagements(engagement_id),
    severity        TEXT NOT NULL,          -- low | medium | high
    category        TEXT NOT NULL,          -- e.g. revenue_recognition, controls
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'open',  -- open | resolved
    identified_date DATE NOT NULL,
    resolved_date   DATE
);

-- ---------------------------------------------------------------------
-- Indexes for realistic aggregation performance
-- ---------------------------------------------------------------------
CREATE INDEX idx_employees_office      ON employees(office_id);
CREATE INDEX idx_employees_grade       ON employees(grade_id);
CREATE INDEX idx_employees_service     ON employees(service_line_id);
CREATE INDEX idx_employees_status      ON employees(employment_status);
CREATE INDEX idx_comp_emp_eff          ON compensation(employee_id, effective_date DESC);
CREATE INDEX idx_time_engagement       ON time_entries(engagement_id);
CREATE INDEX idx_time_employee         ON time_entries(employee_id);
CREATE INDEX idx_time_date             ON time_entries(entry_date);
CREATE INDEX idx_eng_client            ON engagements(client_id);
CREATE INDEX idx_eng_fy                ON engagements(fiscal_year);
CREATE INDEX idx_eng_service           ON engagements(service_line_id);
CREATE INDEX idx_invoices_client       ON invoices(client_id);
CREATE INDEX idx_invoices_status       ON invoices(status);
CREATE INDEX idx_invoices_engagement   ON invoices(engagement_id);
CREATE INDEX idx_payments_invoice      ON payments(invoice_id);
CREATE INDEX idx_taxreturns_client     ON tax_returns(client_id);
CREATE INDEX idx_findings_engagement   ON audit_findings(engagement_id);
