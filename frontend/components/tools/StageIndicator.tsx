import { cn } from '@/lib/utils'
import { Check } from 'lucide-react'

interface StageIndicatorProps {
  stages: string[]
  currentStage: number // 0-indexed
}

export function StageIndicator({ stages, currentStage }: StageIndicatorProps) {
  return (
    <div className="flex items-center gap-0">
      {stages.map((stage, i) => {
        const isDone = i < currentStage
        const isActive = i === currentStage

        return (
          <div key={stage} className="flex items-center">
            {/* Step circle */}
            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors',
                  isDone && 'bg-accent text-sidebar',
                  isActive && 'bg-sidebar text-accent border-2 border-accent',
                  !isDone && !isActive && 'bg-gray-100 text-gray-400',
                )}
              >
                {isDone ? <Check size={14} strokeWidth={3} /> : i + 1}
              </div>
              <span
                className={cn(
                  'text-xs font-medium whitespace-nowrap',
                  isActive && 'text-sidebar',
                  isDone && 'text-gray-500',
                  !isDone && !isActive && 'text-gray-400',
                )}
              >
                {stage}
              </span>
            </div>

            {/* Connector line */}
            {i < stages.length - 1 && (
              <div
                className={cn(
                  'h-0.5 w-12 mb-5 mx-1 transition-colors',
                  i < currentStage ? 'bg-accent' : 'bg-gray-200',
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
