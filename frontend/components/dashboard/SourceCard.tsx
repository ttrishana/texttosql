import { Database } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { sourceLabel } from '@/lib/utils'
import type { HealthResponse, SourceInfo } from '@/lib/types'

interface SourceCardProps {
  source: SourceInfo
  health?: HealthResponse | null
}

export function SourceCard({ source, health }: SourceCardProps) {
  const status = health?.sources?.[source.name]
  const known = health != null && source.name in (health.sources ?? {})

  return (
    <Card className="p-5 flex flex-col h-full">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="shrink-0 w-8 h-8 rounded-lg bg-sidebar flex items-center justify-center">
            <Database size={15} className="text-accent" />
          </div>
          <h3 className="font-semibold text-gray-900 truncate">{sourceLabel(source.name)}</h3>
        </div>
        {known && (
          <span className="flex items-center gap-1.5 text-xs text-gray-500 shrink-0">
            <span className={`w-2 h-2 rounded-full ${status ? 'bg-green-500' : 'bg-red-500'}`} />
            {status ? 'Connected' : 'Down'}
          </span>
        )}
      </div>

      <p className="mt-3 text-sm text-gray-500 leading-relaxed line-clamp-4 flex-1">
        {source.description.trim()}
      </p>

      <div className="mt-4">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-1.5">
          {source.tables.length} tables
        </p>
        <div className="flex flex-wrap gap-1">
          {source.tables.map((t) => (
            <span key={t} className="text-[11px] font-mono text-gray-500 bg-gray-50 border border-gray-100 rounded px-1.5 py-0.5">
              {t}
            </span>
          ))}
        </div>
      </div>
    </Card>
  )
}
