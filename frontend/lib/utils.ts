import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const SOURCE_ACRONYMS: Record<string, string> = { hr: 'HR' }

/** Human-friendly label for a data-source name (e.g. "hr" → "HR", "audit" → "Audit"). */
export function sourceLabel(name: string): string {
  if (!name) return ''
  return SOURCE_ACRONYMS[name.toLowerCase()] ?? name.charAt(0).toUpperCase() + name.slice(1)
}

/** Format a cell value from a SQL result row for display. */
export function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') {
    // Keep integers clean; give floats a sensible, non-lossy default.
    return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 4 })
  }
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

/** Build a CSV blob from column headers + row objects (order follows `columns`). */
export function rowsToCsv(columns: string[], rows: Array<Record<string, unknown>>): Blob {
  const escape = (v: unknown): string => {
    if (v === null || v === undefined) return ''
    const s = typeof v === 'object' ? JSON.stringify(v) : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const lines = [columns.join(',')]
  for (const row of rows) {
    lines.push(columns.map((c) => escape(row[c])).join(','))
  }
  return new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
}

/** Trigger a browser download for a blob. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
