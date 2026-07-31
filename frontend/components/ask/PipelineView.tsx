import { Check, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PIPELINE_STEPS } from '@/lib/constants'

interface PipelineViewProps {
  question: string
  activeStep: number // index into PIPELINE_STEPS; steps before it are done
  correcting?: boolean
}

export function PipelineView({ question, activeStep, correcting = false }: PipelineViewProps) {
  return (
    <div className="p-6 space-y-5">
      <div className="rounded-lg bg-gray-50 border border-gray-200 px-4 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-1">Question</p>
        <p className="text-sm text-gray-800">{question}</p>
      </div>

      {correcting && (
        <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          The first attempt hit an error — the agent is self-correcting and retrying.
        </div>
      )}

      <ol className="space-y-1">
        {PIPELINE_STEPS.map((step, i) => {
          const isDone = i < activeStep
          const isActive = i === activeStep

          return (
            <li key={step.id} className="flex items-start gap-3 py-2">
              <div
                className={cn(
                  'mt-0.5 w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-colors',
                  isDone && 'bg-accent text-sidebar',
                  isActive && 'bg-sidebar text-accent',
                  !isDone && !isActive && 'bg-gray-100 text-gray-400',
                )}
              >
                {isDone ? (
                  <Check size={13} strokeWidth={3} />
                ) : isActive ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <span className="text-[11px] font-semibold">{i + 1}</span>
                )}
              </div>
              <div className="min-w-0">
                <p
                  className={cn(
                    'text-sm font-medium',
                    isActive ? 'text-gray-900' : isDone ? 'text-gray-600' : 'text-gray-400',
                  )}
                >
                  {step.label}
                </p>
                <p className={cn('text-xs', isActive ? 'text-gray-500' : 'text-gray-400')}>
                  {step.detail}
                </p>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
