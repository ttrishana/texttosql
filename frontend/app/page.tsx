'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Activity, ArrowRight, Database, MessagesSquare, Table2 } from 'lucide-react'
import { StatCard } from '@/components/dashboard/StatCard'
import { SourceCard } from '@/components/dashboard/SourceCard'
import { Card } from '@/components/ui/Card'
import { getHealth, getSources } from '@/lib/api/texttosql'
import { FALLBACK_SOURCES } from '@/lib/constants'
import type { HealthResponse, SourceInfo } from '@/lib/types'

export default function OverviewPage() {
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [offline, setOffline] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getSources().catch(() => null),
      getHealth().catch(() => null),
    ]).then(([s, h]) => {
      if (s && s.length) {
        setSources(s)
      } else {
        setSources(FALLBACK_SOURCES)
        setOffline(true)
      }
      setHealth(h)
      setLoading(false)
    })
  }, [])

  const uniqueTables = new Set(sources.flatMap((s) => s.tables)).size
  const statusValue = loading
    ? '—'
    : offline
      ? 'Offline'
      : health?.status === 'ok'
        ? 'Healthy'
        : health?.status === 'degraded'
          ? 'Degraded'
          : 'Unknown'

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Firm Data Intelligence</h1>
        <p className="mt-1 text-sm text-gray-500">
          Natural-language analytics across the firm&rsquo;s HR, audit, tax, and billing data — an AI agent
          writes and runs read-only SQL for you.
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <StatCard label="Backend" value={statusValue} subtext="text-to-SQL API" icon={Activity} />
        <StatCard label="Data sources" value={loading ? '—' : String(sources.length)} subtext="Routable domains" icon={Database} />
        <StatCard label="Tables covered" value={loading ? '—' : String(uniqueTables)} subtext="Across all sources" icon={Table2} />
      </div>

      {/* CTA */}
      <Link href="/ask" className="block group">
        <Card className="p-6 flex items-center justify-between gap-6 transition-colors group-hover:border-accent">
          <div className="flex items-start gap-4">
            <div className="shrink-0 w-11 h-11 rounded-xl bg-accent flex items-center justify-center">
              <MessagesSquare size={20} className="text-sidebar" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Ask a question</h2>
              <p className="mt-0.5 text-sm text-gray-500">
                Try &ldquo;Total revenue by service line for FY2025&rdquo; or &ldquo;Headcount by office and grade&rdquo;.
              </p>
            </div>
          </div>
          <span className="shrink-0 inline-flex items-center gap-1.5 text-sm font-medium text-gray-700 group-hover:text-gray-900">
            Open Firm Data Q&A
            <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
          </span>
        </Card>
      </Link>

      {/* Sources */}
      <div>
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Data sources</h2>
          {offline && <span className="text-xs text-amber-600">Backend offline — showing documented coverage</span>}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {sources.map((s) => (
            <SourceCard key={s.name} source={s} health={health} />
          ))}
        </div>
      </div>
    </div>
  )
}
