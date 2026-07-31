'use client'

import { useState } from 'react'
import { AlertTriangle, Check, Copy, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import type { QueryResponse } from '@/lib/types'

export function AnswerPanel({ result }: { result: QueryResponse }) {
  const [copied, setCopied] = useState(false)
  const isDataQuery = result.route === 'data_query'

  const copySql = async () => {
    if (!result.sql) return
    try {
      await navigator.clipboard.writeText(result.sql)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <div className="p-6 space-y-5">
      {/* Answer */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-2">Answer</p>
        <div className="text-[15px] leading-relaxed text-gray-800 whitespace-pre-wrap">
          {result.answer || '—'}
        </div>
      </div>

      {/* Non-data-query note */}
      {!isDataQuery && result.route && (
        <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
          <MessageSquare size={13} />
          This request was handled as <span className="font-medium capitalize">{result.route.replace('_', ' ')}</span> — no SQL was run.
        </div>
      )}

      {/* Error (surfaced after self-correction is exhausted) */}
      {result.error && (
        <div className="flex items-start gap-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">The query could not be completed</p>
            <p className="mt-0.5 font-mono text-red-600 break-words">{result.error}</p>
          </div>
        </div>
      )}

      {/* Generated SQL */}
      {result.sql && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Generated SQL</p>
            <Button variant="ghost" size="sm" onClick={copySql} className="text-xs">
              {copied ? <Check size={13} /> : <Copy size={13} />}
              {copied ? 'Copied' : 'Copy'}
            </Button>
          </div>
          <pre className="rounded-lg bg-sidebar text-gray-100 text-xs font-mono p-4 overflow-x-auto panel-scroll">
            <code>{result.sql}</code>
          </pre>
        </div>
      )}
    </div>
  )
}
