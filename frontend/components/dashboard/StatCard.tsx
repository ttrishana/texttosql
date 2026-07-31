import type { LucideIcon } from 'lucide-react'
import { Card } from '@/components/ui/Card'

interface StatCardProps {
  label: string
  value: string
  subtext?: string
  icon: LucideIcon
}

export function StatCard({ label, value, subtext, icon: Icon }: StatCardProps) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">{label}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900 truncate">{value}</p>
          {subtext && <p className="mt-1 text-xs text-gray-400">{subtext}</p>}
        </div>
        <div className="shrink-0 w-9 h-9 rounded-lg bg-accent-dim flex items-center justify-center">
          <Icon size={18} className="text-gray-600" />
        </div>
      </div>
    </Card>
  )
}
