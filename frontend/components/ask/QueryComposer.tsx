'use client'

import { useEffect, useRef, useState } from 'react'
import { CornerDownLeft, Database, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { cn, sourceLabel } from '@/lib/utils'
import { EXAMPLE_QUESTIONS } from '@/lib/constants'
import type { SourceInfo } from '@/lib/types'

interface QueryComposerProps {
  sources: SourceInfo[]
  onSubmit: (question: string, source: string | undefined) => void
  loading?: boolean
  threadActive?: boolean
  initialQuestion?: string
}

const AUTO = '__auto__'

export function QueryComposer({
  sources,
  onSubmit,
  loading = false,
  threadActive = false,
  initialQuestion = '',
}: QueryComposerProps) {
  const [question, setQuestion] = useState(initialQuestion)
  const [source, setSource] = useState<string>(AUTO)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    // preventScroll so focusing doesn't scroll the source picker out of view
    textareaRef.current?.focus({ preventScroll: true })
  }, [])

  // Single-DB backends expose one source — preselect it so the picker isn't empty.
  useEffect(() => {
    if (sources.length === 1) setSource(sources[0].name)
  }, [sources])

  const submit = () => {
    const q = question.trim()
    if (!q || loading) return
    onSubmit(q, source === AUTO ? undefined : source)
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      submit()
    }
  }

  // Single-DB backends report one source ("firm"); hide the picker's noise then.
  const showAuto = sources.length !== 1

  return (
    <div className="p-6 space-y-5">
      {threadActive && (
        <div className="flex items-center gap-2 text-xs text-gray-500 bg-accent-dim border border-accent/30 rounded-lg px-3 py-2">
          <Sparkles size={13} className="text-gray-600" />
          Follow-up — this question continues the current conversation, so you can say things like &ldquo;…and just for London?&rdquo;
        </div>
      )}

      {/* Data source */}
      <div>
        <label className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
          <Database size={13} /> Data source
        </label>
        <div className="flex flex-wrap gap-2">
          {showAuto && (
            <SourcePill label="Auto-route" active={source === AUTO} onClick={() => setSource(AUTO)} />
          )}
          {sources.map((s) => (
            <SourcePill
              key={s.name}
              label={sourceLabel(s.name)}
              active={source === s.name}
              onClick={() => setSource(s.name)}
            />
          ))}
        </div>
        {showAuto && source === AUTO && (
          <p className="mt-2 text-xs text-gray-400">
            The orchestrator picks the right database for each question.
          </p>
        )}
      </div>

      {/* Question */}
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
          Your question
        </label>
        <textarea
          ref={textareaRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
          rows={4}
          disabled={loading}
          placeholder="e.g. Total revenue by service line for FY2025"
          className="w-full resize-none rounded-lg border border-gray-200 px-3.5 py-3 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-accent/60 focus:border-accent disabled:bg-gray-50"
        />
        <div className="mt-3 flex items-center justify-between">
          <span className="text-xs text-gray-400 flex items-center gap-1">
            <CornerDownLeft size={12} /> ⌘ + Enter to run
          </span>
          <Button onClick={submit} disabled={!question.trim() || loading}>
            {loading ? 'Running…' : 'Run query'}
          </Button>
        </div>
      </div>

      {/* Example questions */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
          Try an example
        </p>
        <div className="space-y-2">
          {EXAMPLE_QUESTIONS.map((ex) => (
            <button
              key={ex.question}
              type="button"
              disabled={loading}
              onClick={() => setQuestion(ex.question)}
              className="w-full text-left group flex items-start gap-3 rounded-lg border border-gray-200 px-3 py-2.5 hover:border-accent hover:bg-accent-dim/40 transition-colors disabled:opacity-50"
            >
              <span className="shrink-0 mt-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400 w-14">
                {ex.domain}
              </span>
              <span className="text-sm text-gray-700 group-hover:text-gray-900">{ex.question}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function SourcePill({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'px-3 py-1.5 rounded-full text-sm font-medium border transition-colors capitalize',
        active
          ? 'bg-sidebar text-accent border-sidebar'
          : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300',
      )}
    >
      {label}
    </button>
  )
}
