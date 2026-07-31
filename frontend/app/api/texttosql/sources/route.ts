import { NextResponse } from 'next/server'

const BACKEND = process.env.TEXTTOSQL_BACKEND_URL ?? 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/sources`, { cache: 'no-store' })
    const data = await res.json().catch(() => ([]))
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json(
      { error: `Cannot reach the text-to-SQL backend at ${BACKEND}. Is it running?` },
      { status: 502 },
    )
  }
}
