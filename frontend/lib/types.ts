// ── Suite / navigation ────────────────────────────────────────────────────────

export type Department = 'Data & Analytics' | 'Audit' | 'Tax' | 'Advisory'
export type ToolStatus = 'active' | 'coming-soon'

export interface ToolDefinition {
  id: string
  name: string
  description: string
  department: Department
  status: ToolStatus
  path: string
}

// ── Text-to-SQL API contract (mirrors src/texttosql/api/schemas.py) ────────────

/** POST /query response. `route` is data_query | clarify | smalltalk | out_of_scope. */
export interface QueryResponse {
  thread_id: string
  route: QueryRoute | null
  data_source: string | null
  answer: string
  sql: string | null
  columns: string[] | null
  rows: Array<Record<string, unknown>> | null
  row_count: number | null
  attempts: number
  error: string | null
}

export type QueryRoute = 'data_query' | 'clarify' | 'smalltalk' | 'out_of_scope'

/** GET /sources — one domain database the router can choose from. */
export interface SourceInfo {
  name: string
  description: string
  tables: string[]
}

/** GET /schema — one table in the selected source's catalog. */
export interface TableInfo {
  table: string
  description: string
  columns: string[]
}

/** GET /health */
export interface HealthResponse {
  status: 'ok' | 'degraded'
  sources: Record<string, boolean>
}

// ── Tool UI state ───────────────────────────────────────────────────────────--

/** A single node in the agent's ReAct loop, shown during the Analyzing stage. */
export interface PipelineStep {
  id: string
  label: string
  detail: string
}

export type PipelineStepState = 'pending' | 'active' | 'done'
