'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { ToolShell } from '@/components/tools/ToolShell'
import { Button } from '@/components/ui/Button'
import { QueryComposer } from '@/components/ask/QueryComposer'
import { HowItWorks } from '@/components/ask/HowItWorks'
import { SchemaBrowser } from '@/components/ask/SchemaBrowser'
import { PipelineView } from '@/components/ask/PipelineView'
import { SystemLog } from '@/components/ask/SystemLog'
import { AnswerPanel } from '@/components/ask/AnswerPanel'
import { ResultsTable } from '@/components/ask/ResultsTable'
import { QueryStatsBar } from '@/components/ask/QueryStatsBar'
import { getSources, runQuery, ApiError } from '@/lib/api/texttosql'
import { FALLBACK_SOURCES, PIPELINE_STEPS, QUERY_STAGES } from '@/lib/constants'
import type { QueryResponse, SourceInfo } from '@/lib/types'

type Stage = 0 | 1 | 2
const STEP_INTERVAL_MS = 750

export default function AskPage() {
  const [stage, setStage] = useState<Stage>(0)
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [offline, setOffline] = useState(false)

  const [question, setQuestion] = useState('')
  const [initialQuestion, setInitialQuestion] = useState('')
  const [threadId, setThreadId] = useState<string | null>(null)
  const [threadActive, setThreadActive] = useState(false)

  const [activeStep, setActiveStep] = useState(0)
  const [correcting, setCorrecting] = useState(false)
  const [logLines, setLogLines] = useState<string[]>([])

  const [result, setResult] = useState<QueryResponse | null>(null)
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const [requestError, setRequestError] = useState<string | null>(null)

  const timer = useRef<ReturnType<typeof setInterval> | null>(null)
  const clearTimer = () => {
    if (timer.current) {
      clearInterval(timer.current)
      timer.current = null
    }
  }

  // Load the data sources once; fall back to the documented set if offline.
  useEffect(() => {
    getSources()
      .then((s) => setSources(s.length ? s : FALLBACK_SOURCES))
      .catch(() => {
        setSources(FALLBACK_SOURCES)
        setOffline(true)
      })
  }, [])

  useEffect(() => clearTimer, [])

  const handleSubmit = useCallback(
    async (q: string, source: string | undefined) => {
      clearTimer()
      setQuestion(q)
      setStage(1)
      setActiveStep(0)
      setCorrecting(false)
      setResult(null)
      setRequestError(null)
      setLatencyMs(null)
      setLogLines([`→ ${PIPELINE_STEPS[0].label}: ${PIPELINE_STEPS[0].detail}`])

      const start = performance.now()
      let idx = 0
      let capped = false
      timer.current = setInterval(() => {
        if (idx < PIPELINE_STEPS.length - 1) {
          idx += 1
          setActiveStep(idx)
          setLogLines((prev) => [...prev, `→ ${PIPELINE_STEPS[idx].label}: ${PIPELINE_STEPS[idx].detail}`])
        } else if (!capped) {
          capped = true
          setLogLines((prev) => [...prev, '· waiting for the database and model…'])
        }
      }, STEP_INTERVAL_MS)

      try {
        const res = await runQuery(q, { threadId: threadId ?? undefined, source })
        clearTimer()

        const finalLog: string[] = []
        if (res.data_source) finalLog.push(`✓ source: ${res.data_source}`)
        if (res.sql) finalLog.push('✓ SQL generated and validated')
        if (res.route === 'data_query') finalLog.push(`✓ ${res.row_count ?? res.rows?.length ?? 0} row(s) returned`)
        if (res.attempts > 0) finalLog.push(`! self-corrected after ${res.attempts} retr${res.attempts === 1 ? 'y' : 'ies'}`)
        finalLog.push('✓ done')

        setActiveStep(PIPELINE_STEPS.length)
        setCorrecting(res.attempts > 0)
        setLogLines((prev) => [...prev, ...finalLog])
        setResult(res)
        setThreadId(res.thread_id)
        setLatencyMs(performance.now() - start)

        // brief beat so the completed pipeline is visible before the reveal
        setTimeout(() => setStage(2), 450)
      } catch (e) {
        clearTimer()
        let msg = 'Unexpected error running the query.'
        if (e instanceof ApiError) {
          msg =
            e.status === 500
              ? `${e.message}. The backend errored while processing the query — check its logs. A common cause on the Gemini free tier is a rate limit or exhausted quota.`
              : e.message
        }
        setRequestError(msg)
        setStage(2)
      }
    },
    [threadId],
  )

  const startFollowUp = () => {
    setInitialQuestion('')
    setThreadActive(true)
    setResult(null)
    setRequestError(null)
    setStage(0)
  }

  const startNewQuestion = () => {
    setInitialQuestion('')
    setThreadActive(false)
    setThreadId(null)
    setResult(null)
    setRequestError(null)
    setStage(0)
  }

  // ── Panels per stage ──────────────────────────────────────────────────────
  let leftLabel = 'Ask a question'
  let rightLabel = 'How it works & schema'
  let leftPanel: React.ReactNode = null
  let rightPanel: React.ReactNode = null
  let statsBar: React.ReactNode = undefined

  if (stage === 0) {
    leftPanel = (
      <QueryComposer
        sources={sources}
        onSubmit={handleSubmit}
        threadActive={threadActive}
        initialQuestion={initialQuestion}
      />
    )
    rightPanel = (
      <div>
        <HowItWorks />
        <SchemaBrowser sources={sources} offline={offline} />
      </div>
    )
  } else if (stage === 1) {
    leftLabel = 'Agent pipeline'
    rightLabel = 'System log'
    leftPanel = <PipelineView question={question} activeStep={activeStep} correcting={correcting} />
    rightPanel = <SystemLog lines={logLines} />
  } else if (requestError) {
    leftLabel = 'Something went wrong'
    rightLabel = 'Troubleshooting'
    leftPanel = <RequestErrorPanel message={requestError} onRetry={() => handleSubmit(question, undefined)} onReset={startNewQuestion} />
    rightPanel = <TroubleshootingPanel />
  } else if (result) {
    leftLabel = 'Answer & SQL'
    rightLabel = 'Results'
    leftPanel = <AnswerPanel result={result} />
    rightPanel = <ResultsTable result={result} />
    statsBar = (
      <QueryStatsBar
        result={result}
        latencyMs={latencyMs}
        onFollowUp={startFollowUp}
        onNewQuestion={startNewQuestion}
      />
    )
  }

  return (
    <ToolShell
      title="Firm Data Q&A"
      description="Ask questions about firm data in plain English — the agent writes, validates, and runs the SQL"
      stages={QUERY_STAGES}
      currentStage={stage}
      leftLabel={leftLabel}
      rightLabel={rightLabel}
      leftPanel={leftPanel}
      rightPanel={rightPanel}
      statsBar={statsBar}
    />
  )
}

function RequestErrorPanel({
  message,
  onRetry,
  onReset,
}: {
  message: string
  onRetry: () => void
  onReset: () => void
}) {
  return (
    <div className="p-6">
      <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3.5">
        <AlertTriangle size={18} className="shrink-0 mt-0.5 text-red-500" />
        <div>
          <p className="text-sm font-semibold text-red-800">Could not run the query</p>
          <p className="mt-1 text-sm text-red-600">{message}</p>
        </div>
      </div>
      <div className="mt-4 flex gap-2">
        <Button onClick={onRetry}>Try again</Button>
        <Button variant="secondary" onClick={onReset}>Start over</Button>
      </div>
    </div>
  )
}

function TroubleshootingPanel() {
  return (
    <div className="p-6 space-y-3 text-sm text-gray-500">
      <h3 className="font-semibold text-gray-700">Is the backend running?</h3>
      <p>The frontend proxies to the text-to-SQL FastAPI service. Start it from the repo root:</p>
      <pre className="rounded-lg bg-sidebar text-gray-100 text-xs font-mono p-3 overflow-x-auto panel-scroll">
        <code>uvicorn texttosql.api.main:app --reload</code>
      </pre>
      <p className="text-xs text-gray-400">
        Override the target with <code className="font-mono">TEXTTOSQL_BACKEND_URL</code> (defaults to
        <code className="font-mono"> http://localhost:8000</code>). If the API was started with
        <code className="font-mono"> API_KEY</code> set, provide the same value as
        <code className="font-mono"> TEXTTOSQL_API_KEY</code>.
      </p>
    </div>
  )
}
