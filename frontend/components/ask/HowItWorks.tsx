import { ShieldCheck } from 'lucide-react'

export function HowItWorks() {
  return (
    <div className="p-6 space-y-4 text-sm text-gray-500 border-b border-gray-100">
      <h3 className="font-semibold text-gray-700">How it works</h3>
      <ol className="space-y-3 list-decimal list-inside">
        <li>Ask a business question in plain English (or pin a data source).</li>
        <li>The agent classifies intent, then assembles the relevant schema and curated examples.</li>
        <li>It generates PostgreSQL, validates it, and runs it under a read-only role.</li>
        <li>On an error it self-corrects and retries — then answers in plain language with the SQL and rows.</li>
      </ol>
      <div className="mt-2 p-3 bg-accent-dim border border-accent/30 rounded-lg text-xs text-gray-700 flex gap-2">
        <ShieldCheck size={15} className="shrink-0 mt-0.5 text-gray-600" />
        <span>
          <strong>Read-only by design:</strong> every query is single-statement, SELECT-only, schema-checked, and
          auto-limited — backed by a read-only database role and a statement timeout.
        </span>
      </div>
    </div>
  )
}
