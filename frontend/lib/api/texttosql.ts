import type { HealthResponse, QueryResponse, SourceInfo, TableInfo } from '../types'

/**
 * Thrown when a request to the backend fails. `status` is 0 when the backend
 * could not be reached at all (so the UI can show an "offline" state).
 */
export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function parseError(res: Response): Promise<never> {
  const body = await res.json().catch(() => ({}))
  const detail: string = body.detail ?? body.error ?? `Request failed (${res.status})`
  throw new ApiError(detail, res.status)
}

// POST /api/texttosql/query
export async function runQuery(
  question: string,
  opts: { threadId?: string; source?: string } = {},
): Promise<QueryResponse> {
  const res = await fetch('/api/texttosql/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      thread_id: opts.threadId,
      source: opts.source,
    }),
  })
  if (!res.ok) await parseError(res)
  return res.json()
}

// GET /api/texttosql/sources
export async function getSources(): Promise<SourceInfo[]> {
  const res = await fetch('/api/texttosql/sources')
  if (!res.ok) await parseError(res)
  return res.json()
}

// GET /api/texttosql/schema?source=<name>
export async function getSchema(source?: string): Promise<TableInfo[]> {
  const qs = source ? `?source=${encodeURIComponent(source)}` : ''
  const res = await fetch(`/api/texttosql/schema${qs}`)
  if (!res.ok) await parseError(res)
  return res.json()
}

// GET /api/texttosql/health
export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch('/api/texttosql/health')
  if (!res.ok) await parseError(res)
  return res.json()
}
