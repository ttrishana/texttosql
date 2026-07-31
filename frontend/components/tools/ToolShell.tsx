import { StageIndicator } from './StageIndicator'

interface ToolShellProps {
  title: string
  description?: string
  stages: string[]
  currentStage: number
  leftLabel: string
  rightLabel: string
  leftPanel: React.ReactNode
  rightPanel: React.ReactNode
  statsBar?: React.ReactNode
}

export function ToolShell({
  title,
  description,
  stages,
  currentStage,
  leftLabel,
  rightLabel,
  leftPanel,
  rightPanel,
  statsBar,
}: ToolShellProps) {
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Tool header */}
      <div className="shrink-0 px-6 py-4 bg-white border-b border-gray-200 flex items-center justify-between gap-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
          {description && <p className="text-xs text-gray-400 mt-0.5">{description}</p>}
        </div>
        <StageIndicator stages={stages} currentStage={currentStage} />
      </div>

      {/* Optional full-width stats bar (e.g. results summary) */}
      {statsBar && <div className="shrink-0 border-b border-gray-200 bg-white">{statsBar}</div>}

      {/* Split pane */}
      <div className="flex flex-1 min-h-0 divide-x divide-gray-200">
        {/* Left panel */}
        <div className="flex flex-col w-1/2 min-w-0">
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 shrink-0">
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              {leftLabel}
            </span>
          </div>
          <div className="flex-1 overflow-auto panel-scroll">{leftPanel}</div>
        </div>

        {/* Right panel */}
        <div className="flex flex-col w-1/2 min-w-0">
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 shrink-0">
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              {rightLabel}
            </span>
          </div>
          <div className="flex-1 overflow-auto panel-scroll">{rightPanel}</div>
        </div>
      </div>
    </div>
  )
}
