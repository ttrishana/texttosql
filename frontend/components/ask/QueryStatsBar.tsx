'use client'

import { Plus, RotateCcw } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { sourceLabel } from '@/lib/utils'
import type { QueryResponse } from '@/lib/types'

interface QueryStatsBarProps {
  result: QueryResponse
  latencyMs: number | null
  onFollowUp: () => void
  onNewQuestion: () => void
}

const ROUTE_LABEL: Record<string, string> = {
  data_query: 'Data query',
  clarify: 'Clarify',
  smalltalk: 'Small talk',
  out_of_scope: 'Out of scope',
}

export function QueryStatsBar({ result, latencyMs, onFollowUp, onNewQuestion }: QueryStatsBarProps) {
  const selfCorrected = result.attempts > 0

  return (
    <div className="px-6 py-3 flex items-center justify-between gap-6 flex-wrap">
      <div className="flex items-center gap-6 flex-wrap">
        <Stat label="Route">
          <Badge variant={result.route === 'data_query' ? 'accent' : 'info'}>
            {result.route ? ROUTE_LABEL[result.route] ?? result.route : '—'}
          </Badge>
        </Stat>
        {result.data_source && (
          <Stat label="Source">
            <span className="text-sm font-medium text-gray-800">{sourceLabel(result.data_source)}</span>
          </Stat>
        )}
        {result.route === 'data_query' && (
          <Stat label="Rows">
            <span className="text-sm font-medium text-gray-800 tabular-nums">
              {result.row_count ?? result.rows?.length ?? 0}
            </span>
          </Stat>
        )}
        <Stat label="Attempts">
          <span className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-800 tabular-nums">{result.attempts + 1}</span>
            {selfCorrected && <Badge variant="warning">self-corrected</Badge>}
          </span>
        </Stat>
        {latencyMs != null && (
          <Stat label="Latency">
            <span className="text-sm font-medium text-gray-800 tabular-nums">
              {(latencyMs / 1000).toFixed(1)}s
            </span>
          </Stat>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" onClick={onFollowUp}>
          <Plus size={14} /> Follow-up
        </Button>
        <Button variant="ghost" size="sm" onClick={onNewQuestion}>
          <RotateCcw size={14} /> New question
        </Button>
      </div>
    </div>
  )
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">{label}</span>
      {children}
    </div>
  )
}
