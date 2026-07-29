# Text-to-SQL Agent (LangGraph + Gemini + PostgreSQL + FastAPI)

A natural-language-to-SQL agent for a professional-services firm (audit / tax /
accounting + HR analytics). Ask a business question in English; the agent
analyzes intent, generates PostgreSQL, validates and runs it read-only,
**self-corrects on errors**, and returns a plain-language answer plus the SQL
and rows — exposed over a FastAPI endpoint.

The design implements a layered ReAct loop in LangGraph:

```
Interaction Layer (FastAPI)
        │
Primary Orchestrator ──(data_query)──► Intent Analysis ─► Prompt Design ─► SQL Execution
        ▲   │(else)                          ▲                                 │
        │   └──────────────► Respond ◄───────┼──────────────(success)─────────┘
        │                                    │
        └────────── answer          Self-Correction ◄──(error, attempts<max)───┘
                                             │ (loops back to Intent Analysis)
Knowledge Layer:  Semantic Metadata (semantic_model.yaml + few_shots.yaml)  +  Data Warehouse (Postgres)
```

## Architecture

| Layer | Component | Where |
|---|---|---|
| Interaction | FastAPI REST API | [api/main.py](src/texttosql/api/main.py) |
| Orchestration | LangGraph `StateGraph` + conditional edges | [agent/graph.py](src/texttosql/agent/graph.py) |
| — Primary Orchestrator | route: data_query / clarify / smalltalk / out_of_scope | [nodes/orchestrator.py](src/texttosql/agent/nodes/orchestrator.py) |
| — Intent Analysis | structured intent extraction | [nodes/intent.py](src/texttosql/agent/nodes/intent.py) |
| — Prompt Design | assemble context + generate SQL | [nodes/prompt_design.py](src/texttosql/agent/nodes/prompt_design.py) |
| — SQL Execution | guardrails + read-only run | [nodes/execution.py](src/texttosql/agent/nodes/execution.py) |
| — Self-Correction | diagnose error, loop back | [nodes/self_correction.py](src/texttosql/agent/nodes/self_correction.py) |
| Knowledge | SemanticCatalog (introspection + YAML overlay) | [knowledge/catalog.py](src/texttosql/knowledge/catalog.py) |
| Safety | sqlglot SQL validation | [agent/guardrails.py](src/texttosql/agent/guardrails.py) |

## Prerequisites

- Python 3.11+
- Docker (for PostgreSQL + pgvector), or your own Postgres
- A Google **Gemini** API key ([AI Studio](https://aistudio.google.com/app/apikey))

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .            # add [dev] for tests, [retrieval] for pgvector mode
cp .env.example .env        # then edit .env: set GOOGLE_API_KEY (+ model ids if needed)
```

Start Postgres (creates the `texttosql_admin` / `texttosql_readonly` roles and the
pgvector extension automatically on first run):

```bash
docker compose up -d
```

Create the schema and load ~76k rows of synthetic data:

```bash
python scripts/init_db.py            # use --scale 0.2 for a quick, smaller dataset
```

### No Docker? Three options

The code only reads connection URLs — Postgres can live anywhere.

**A. Embedded Postgres (zero install, recommended for local testing).** A real
Postgres (with pgvector) shipped as a pip wheel — no Docker, no system install, no
sudo. The data lives in `./.pgdata`.

```bash
pip install -e ".[embedded]"
echo "EMBEDDED_DB=true" >> .env       # ignores the *_DATABASE_URL values
python scripts/init_db.py             # boots it, creates roles, loads data
```

**B. Local install** (Postgres.app or `brew install postgresql@16`) **or C. cloud
Postgres** (Neon / Supabase free tier). Point `.env`'s `*_DATABASE_URL` at it, then
create the roles once with a superuser URL and seed:

```bash
python scripts/bootstrap_db.py "postgresql://<superuser>:<pw>@<host>:5432/postgres"
python scripts/init_db.py
```

> **Gemini free tier:** `gemini-2.5-pro` is not available (quota 0). The defaults
> use `gemini-2.5-flash`, which works on the free tier. Use `pro` for
> `GEMINI_MODEL_MAIN` only on a paid key.

## Run

**API:**

```bash
uvicorn texttosql.api.main:app --reload
```

```bash
curl -s -X POST localhost:8000/query -H 'content-type: application/json' \
  -d '{"question":"Total revenue by service line for FY2025"}' | jq
```

Multi-turn (reuse `thread_id` for follow-ups like "…and just for London?"):

```bash
curl -s -X POST localhost:8000/query -H 'content-type: application/json' \
  -d '{"question":"How many active employees per office?","thread_id":"demo-1"}' | jq
```

Other endpoints: `GET /health`, `GET /schema` (catalog summary).

**CLI (quick graph test):**

```bash
python -m texttosql.agent.graph "Who are the top 5 highest-paid active employees without a CPA?"
```

## The database

One coherent schema for a professional-services firm — see
[db/schema.sql](src/texttosql/db/schema.sql). ~19 tables:

- **Org/reference:** offices, service_lines, departments, grades
- **People/HR:** employees, compensation (salary history), performance_reviews, certifications, leave
- **Delivery:** clients, engagements, engagement_staffing, time_entries
- **Billing:** invoices, invoice_line_items, payments, expenses
- **Service-specific:** tax_returns, audit_findings

**Two roles, least privilege:** `texttosql_admin` owns the schema and does DDL +
seeding; **`texttosql_readonly` is the only role the agent uses** — `SELECT`-only,
`default_transaction_read_only = on`, and a 15s `statement_timeout`.

**Knowledge Layer:** the live schema is merged with a curated business overlay
([semantic_model.yaml](src/texttosql/knowledge/semantic_model.yaml): descriptions,
synonyms, enum values, join hints, metric definitions, glossary) and curated
NL→SQL examples ([few_shots.yaml](src/texttosql/knowledge/few_shots.yaml)).

## Multiple databases (routing)

Set `MULTI_DB=true` to run against several domain databases instead of one. The
**Primary Orchestrator** becomes a *data-source router*: a [router node](src/texttosql/agent/nodes/router.py)
picks exactly one database per question (single-domain routing), and the rest of
the loop — intent, prompt design, execution, self-correction, guardrails — operates
against that source's own engine + `SemanticCatalog`.

Sources are declared in [sources.yaml](src/texttosql/knowledge/sources.yaml) — one
entry per domain with a description (used by the router), a database, and its tables:

| Source | Database | Covers |
|---|---|---|
| `hr` | hrdb | employees, compensation, reviews, certifications, leave, org structure |
| `audit` | auditdb | clients, engagements, staffing, timesheets, audit findings |
| `tax` | taxdb | clients, tax engagements, tax returns/filings |
| `billing` | billingdb | invoices, line items, payments, expenses |

`python scripts/init_db.py` (with `MULTI_DB=true` + `EMBEDDED_DB=true`) splits the
demo data across the four databases, generating each domain's schema from the single
[schema.sql](src/texttosql/db/schema.sql) with cross-domain foreign keys dropped
(shared ids like `employee_id` stay as plain columns — realistic for separate
systems). Single-DB mode is just the special case of one source named `firm`, so
there's one code path either way.

- **Point at real databases:** replace each source's `database:` in sources.yaml
  with a read-only `url:` (or `url_env:` naming an env var). No code changes.
- **Pin a source per request:** `POST /query {"question": "...", "source": "hr"}`
  skips the router. `GET /sources` lists them; `GET /schema?source=hr` shows one.
- **Cross-domain joins** (e.g. audit hours + HR salaries) aren't supported by
  single-domain routing — that needs `postgres_fdw` federation or a warehouse view.

## Safety

Defense in depth on every generated query
([guardrails.py](src/texttosql/agent/guardrails.py)): single-statement only,
SELECT-only (blocks all DML/DDL), every table must be in the known schema,
dangerous functions blocked, and an automatic `LIMIT`. Backed by the read-only DB
role and statement timeout.

## Tests

```bash
pip install -e ".[dev]"
pytest                                   # guardrails + metadata + seed run without a DB
pytest tests/test_eval.py -v             # needs a seeded DB (+ GOOGLE_API_KEY for agent tests)
```

- `test_guardrails.py` — validator accepts/rejects the right queries
- `test_metadata.py` — all 20 golden SQL statements are valid SELECTs over known tables
- `test_seed.py` — synthetic data referential integrity + determinism
- `test_eval.py` — golden SQL executes against the DB; full agent answers end-to-end

## Optional

- **Retrieval mode** (`RETRIEVAL_MODE=true`, `pip install -e ".[retrieval]"`,
  `python scripts/build_index.py`): embed schema + few-shots into pgvector for
  large schemas. Default mode passes the full schema (fits comfortably here).
- **Durable memory:** swap `MemorySaver` for `PostgresSaver`
  (`pip install -e ".[memory]"`) in [agent/graph.py](src/texttosql/agent/graph.py).
- **Tracing:** set `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY`.

## Configuration

All via `.env` (see [.env.example](.env.example)): `GOOGLE_API_KEY`,
`GEMINI_MODEL_MAIN`/`GEMINI_MODEL_FAST`, DB URLs, `MAX_CORRECTION_ATTEMPTS`,
`RESULT_ROW_CAP`, `STATEMENT_TIMEOUT_MS`, `RETRIEVAL_MODE`, `API_KEY`.
