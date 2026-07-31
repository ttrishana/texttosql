# Firm Data Q&A — Text-to-SQL Frontend

A Next.js frontend for the [text-to-SQL agent](../README.md), styled and structured to
match the **Baker Tilly Intelligence Suite** tools: the dark sidebar shell, the lime
accent, and the staged **Ask → Analyzing → Answer** split-pane flow.

Ask a business question in plain English; the agent classifies intent, generates
PostgreSQL, validates and runs it read-only, self-corrects on errors, and returns a
plain-language answer plus the SQL and rows.

## Stack

- Next.js 16 (App Router) · React 19 · TypeScript
- Tailwind CSS v4 · lucide-react icons
- Same design system as `baker-tilly-isuite` (`AppShell`, `Sidebar`, `ToolShell`, `Card`/`Button`/`Badge`, brand tokens)

## Run

The frontend talks to the FastAPI backend through same-origin Next.js API routes
(`app/api/texttosql/*`), so the backend URL and API key stay server-side.

1. **Start the backend** (from the repo root — see the [main README](../README.md)):

   ```bash
   uvicorn texttosql.api.main:app --reload
   ```

2. **Start the frontend:**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Open http://localhost:3000.

## Configuration

Copy `.env.example` to `.env.local`:

| Variable | Default | Purpose |
|---|---|---|
| `TEXTTOSQL_BACKEND_URL` | `http://localhost:8000` | Base URL of the FastAPI service |
| `TEXTTOSQL_API_KEY` | *(empty)* | Sent as `X-API-Key` on `/query`, only if the backend sets `API_KEY` |

If the backend is offline the UI degrades gracefully — the overview and schema browser
fall back to the documented source/table coverage, and running a query surfaces a clear
"backend unreachable" state instead of failing silently.

## Structure

```
app/
  page.tsx                     Overview: backend health, sources, schema coverage
  (tool)/ask/page.tsx          Firm Data Q&A tool (staged split-pane flow)
  api/texttosql/*/route.ts     Proxy routes → FastAPI (/query, /sources, /schema, /health)
components/
  layout/  AppShell, Sidebar
  tools/   ToolShell, StageIndicator
  ui/      Card, Button, Badge
  ask/     QueryComposer, HowItWorks, SchemaBrowser, PipelineView,
           SystemLog, AnswerPanel, ResultsTable, QueryStatsBar
  dashboard/ StatCard, SourceCard
lib/
  api/texttosql.ts             Typed client for the proxy routes
  types.ts, constants.ts, utils.ts
```
