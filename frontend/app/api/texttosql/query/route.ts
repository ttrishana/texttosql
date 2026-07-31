import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.TEXTTOSQL_BACKEND_URL ?? 'http://localhost:8000'
const API_KEY = process.env.TEXTTOSQL_API_KEY

export async function POST(req: NextRequest) {
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body.' }, { status: 400 })
  }

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (API_KEY) headers['X-API-Key'] = API_KEY

  try {
    const res = await fetch(`${BACKEND}/query`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })
    // The backend returns JSON on success and on handled errors, but an
    // unhandled 500 is plain text — capture it so the UI shows something useful.
    const raw = await res.text()
    let data: unknown
    try {
      data = raw ? JSON.parse(raw) : {}
    } catch {
      data = { error: raw.slice(0, 500) || `Backend error (${res.status})` }
    }
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json(
      { error: `Cannot reach the text-to-SQL backend at ${BACKEND}. Is it running?` },
      { status: 502 },
    )
  }
}
