import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.TEXTTOSQL_BACKEND_URL ?? 'http://localhost:8000'

export async function GET(req: NextRequest) {
  const source = req.nextUrl.searchParams.get('source')
  const qs = source ? `?source=${encodeURIComponent(source)}` : ''
  try {
    const res = await fetch(`${BACKEND}/schema${qs}`, { cache: 'no-store' })
    const data = await res.json().catch(() => ([]))
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json(
      { error: `Cannot reach the text-to-SQL backend at ${BACKEND}. Is it running?` },
      { status: 502 },
    )
  }
}
