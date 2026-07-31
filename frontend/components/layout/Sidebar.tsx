'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { TOOLS, NAV_DEPARTMENTS } from '@/lib/constants'
import type { Department } from '@/lib/types'

function DepartmentSection({ department }: { department: Department }) {
  const pathname = usePathname()
  const tools = TOOLS.filter((t) => t.department === department)

  return (
    <div>
      <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-widest text-gray-500">
        {department}
      </p>
      <ul className="space-y-0.5">
        {tools.map((tool) => {
          const isActive = pathname === tool.path
          const isComingSoon = tool.status === 'coming-soon'

          return (
            <li key={tool.id}>
              {isComingSoon ? (
                <div className="flex items-center justify-between px-3 py-2 rounded-lg text-sm text-gray-500 cursor-not-allowed select-none">
                  <span className="truncate">{tool.name}</span>
                  <span className="shrink-0 ml-2 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-gray-700 text-gray-400 uppercase tracking-wide">
                    Soon
                  </span>
                </div>
              ) : (
                <Link
                  href={tool.path}
                  className={cn(
                    'flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors',
                    isActive
                      ? 'bg-accent-dim text-accent font-medium'
                      : 'text-gray-300 hover:bg-sidebar-hover hover:text-white',
                  )}
                >
                  <span className="truncate">{tool.name}</span>
                  {isActive && <ChevronRight size={14} className="shrink-0 text-accent" />}
                </Link>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed top-0 left-0 h-screen w-60 bg-sidebar flex flex-col z-40">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded bg-accent flex items-center justify-center shrink-0">
            <span className="text-sidebar font-black text-xs">BT</span>
          </div>
          <div>
            <p className="text-white font-semibold text-sm leading-tight">Baker Tilly</p>
            <p className="text-gray-400 text-[10px] leading-tight tracking-wide">Intelligence Suite</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-5">
        {/* Dashboard link */}
        <Link
          href="/"
          className={cn(
            'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
            pathname === '/'
              ? 'bg-accent-dim text-accent font-medium'
              : 'text-gray-300 hover:bg-sidebar-hover hover:text-white',
          )}
        >
          <LayoutDashboard size={15} />
          Overview
        </Link>

        <div className="border-t border-white/10 pt-4 space-y-5">
          {NAV_DEPARTMENTS.map(({ department }) => (
            <DepartmentSection key={department} department={department} />
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-white/10">
        <p className="text-[10px] text-gray-500">© 2026 Baker Tilly US, LLP</p>
      </div>
    </aside>
  )
}
