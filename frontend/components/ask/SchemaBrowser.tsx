'use client'

import { useEffect, useState } from 'react'
import { ChevronDown, ChevronRight, Table2 } from 'lucide-react'
import { cn, sourceLabel } from '@/lib/utils'
import { getSchema } from '@/lib/api/texttosql'
import type { SourceInfo, TableInfo } from '@/lib/types'

interface SchemaBrowserProps {
  sources: SourceInfo[]
  offline?: boolean
}

export function SchemaBrowser({ sources, offline = false }: SchemaBrowserProps) {
  const [activeSource, setActiveSource] = useState<string>(sources[0]?.name ?? '')
  const [tables, setTables] = useState<TableInfo[] | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!sources.length) return
    if (!sources.some((s) => s.name === activeSource)) {
      setActiveSource(sources[0].name)
    }
  }, [sources, activeSource])

  useEffect(() => {
    if (offline || !activeSource) {
      setTables(null)
      return
    }
    let cancelled = false
    setLoading(true)
    getSchema(activeSource === 'firm' ? undefined : activeSource)
      .then((t) => !cancelled && setTables(t))
      .catch(() => !cancelled && setTables(null))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [activeSource, offline])

  const active = sources.find((s) => s.name === activeSource)
  const multi = sources.length > 1

  return (
    <div className="p-6 space-y-4">
      <h3 className="font-semibold text-gray-700 text-sm">Data coverage</h3>

      {multi && (
        <div className="flex flex-wrap gap-1.5">
          {sources.map((s) => (
            <button
              key={s.name}
              onClick={() => setActiveSource(s.name)}
              className={cn(
                'px-2.5 py-1 rounded-md text-xs font-medium border transition-colors',
                s.name === activeSource
                  ? 'bg-sidebar text-accent border-sidebar'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300',
              )}
            >
              {sourceLabel(s.name)}
            </button>
          ))}
        </div>
      )}

      {active?.description && (
        <p className="text-xs leading-relaxed text-gray-500">{active.description.trim()}</p>
      )}

      <div className="space-y-1">
        {loading && <p className="text-xs text-gray-400">Loading schema…</p>}

        {/* Live catalog when available; otherwise the source's table list. */}
        {!loading && tables && tables.length > 0
          ? tables.map((t) => <TableRow key={t.table} table={t.table} description={t.description} columns={t.columns} />)
          : (active?.tables ?? []).map((name) => <TableRow key={name} table={name} />)}
      </div>

      {offline && (
        <p className="text-xs text-amber-600">
          Backend offline — showing the documented schema. Start the API to browse live column details.
        </p>
      )}
    </div>
  )
}

function TableRow({
  table,
  description,
  columns,
}: {
  table: string
  description?: string
  columns?: string[]
}) {
  const [open, setOpen] = useState(false)
  const expandable = Boolean(columns && columns.length)

  return (
    <div className="rounded-lg border border-gray-100">
      <button
        onClick={() => expandable && setOpen((o) => !o)}
        className={cn(
          'w-full flex items-center gap-2 px-3 py-2 text-left',
          expandable && 'hover:bg-gray-50',
        )}
      >
        <Table2 size={13} className="shrink-0 text-gray-400" />
        <code className="text-xs font-mono text-gray-700">{table}</code>
        {description && <span className="text-xs text-gray-400 truncate">— {description}</span>}
        {expandable && (
          <span className="ml-auto shrink-0 text-gray-400">
            {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
        )}
      </button>
      {open && columns && (
        <div className="px-3 pb-2.5 pt-0.5 flex flex-wrap gap-1.5">
          {columns.map((c) => (
            <span key={c} className="text-[11px] font-mono text-gray-500 bg-gray-50 border border-gray-100 rounded px-1.5 py-0.5">
              {c}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
