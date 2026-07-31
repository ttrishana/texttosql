'use client'

import { Download, TableProperties } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { cn, downloadBlob, formatCell, rowsToCsv } from '@/lib/utils'
import type { QueryResponse } from '@/lib/types'

export function ResultsTable({ result }: { result: QueryResponse }) {
  const columns = result.columns ?? []
  const rows = result.rows ?? []

  // No result set at all — a non-data question (smalltalk / clarify / out of scope).
  if (result.route !== 'data_query' && rows.length === 0 && columns.length === 0) {
    return (
      <EmptyState
        title="No result set"
        detail="This request didn't require a database query, so there are no rows to show."
      />
    )
  }

  // A data query that returned zero rows.
  if (rows.length === 0) {
    return (
      <EmptyState
        title="Query ran — 0 rows"
        detail="The SQL executed successfully but matched no records."
      />
    )
  }

  const download = () => {
    downloadBlob(rowsToCsv(columns, rows), 'query-results.csv')
  }

  return (
    <div className="flex flex-col h-full">
      <div className="shrink-0 flex items-center justify-between px-4 py-2.5 border-b border-gray-100">
        <span className="text-xs text-gray-500">
          {result.row_count ?? rows.length} row{(result.row_count ?? rows.length) === 1 ? '' : 's'}
          {result.row_count != null && rows.length < result.row_count && ` · showing first ${rows.length}`}
        </span>
        <Button variant="secondary" size="sm" onClick={download} className="text-xs">
          <Download size={13} /> CSV
        </Button>
      </div>

      <div className="flex-1 overflow-auto panel-scroll">
        <table className="w-full text-sm border-collapse">
          <thead className="sticky top-0 z-10">
            <tr className="bg-gray-50">
              {columns.map((col) => (
                <th
                  key={col}
                  className="text-left font-semibold text-gray-600 text-xs uppercase tracking-wide px-4 py-2.5 border-b border-gray-200 whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className={cn(i % 2 === 1 && 'bg-gray-50/60', 'hover:bg-accent-dim/40')}>
                {columns.map((col) => {
                  const value = row[col]
                  const numeric = typeof value === 'number'
                  return (
                    <td
                      key={col}
                      className={cn(
                        'px-4 py-2 border-b border-gray-100 text-gray-700 align-top',
                        numeric ? 'text-right font-mono tabular-nums whitespace-nowrap' : 'max-w-md',
                      )}
                    >
                      {formatCell(value)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center p-10 text-gray-400">
      <TableProperties size={28} className="mb-3" />
      <p className="text-sm font-medium text-gray-600">{title}</p>
      <p className="text-xs mt-1 max-w-xs">{detail}</p>
    </div>
  )
}
