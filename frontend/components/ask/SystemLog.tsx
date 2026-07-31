'use client'

import { useEffect, useRef } from 'react'

interface SystemLogProps {
  lines: string[]
}

export function SystemLog({ lines }: SystemLogProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  return (
    <div className="p-6">
      <div className="rounded-lg bg-sidebar text-gray-300 font-mono text-xs p-4 min-h-full">
        {lines.length === 0 ? (
          <p className="text-gray-500">Waiting for the agent…</p>
        ) : (
          <div className="space-y-1">
            {lines.map((line, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-gray-600 select-none">{String(i + 1).padStart(2, '0')}</span>
                <span className={line.startsWith('!') ? 'text-amber-300' : 'text-gray-300'}>
                  {line.replace(/^!/, '')}
                </span>
              </div>
            ))}
            <div ref={endRef} />
          </div>
        )}
      </div>
    </div>
  )
}
