import type { PipelineStep, SourceInfo, ToolDefinition } from './types'

export const TOOLS: ToolDefinition[] = [
  {
    id: 'ask',
    name: 'Firm Data Q&A',
    description: 'Ask questions about firm data in plain English — the agent writes, validates, and runs the SQL',
    department: 'Data & Analytics',
    status: 'active',
    path: '/ask',
  },
  {
    id: 'saved-queries',
    name: 'Saved Queries',
    description: 'Reuse and schedule vetted natural-language queries',
    department: 'Data & Analytics',
    status: 'coming-soon',
    path: '/saved-queries',
  },
  {
    id: 'data-catalog',
    name: 'Data Catalog',
    description: 'Browse the semantic model, metrics, and table lineage',
    department: 'Data & Analytics',
    status: 'coming-soon',
    path: '/data-catalog',
  },
]

export const NAV_DEPARTMENTS: Array<{ label: string; department: ToolDefinition['department'] }> = [
  { label: 'Data & Analytics', department: 'Data & Analytics' },
]

/** The three tool stages, mirroring the Baker Tilly staged split-pane flow. */
export const QUERY_STAGES = ['Ask', 'Analyzing', 'Answer']

/** The agent's ReAct loop, surfaced to the user during the Analyzing stage. */
export const PIPELINE_STEPS: PipelineStep[] = [
  { id: 'orchestrator', label: 'Orchestrator', detail: 'Classifying the request' },
  { id: 'router', label: 'Router', detail: 'Selecting the data source' },
  { id: 'intent', label: 'Intent Analysis', detail: 'Understanding what you asked' },
  { id: 'prompt_design', label: 'Prompt Design', detail: 'Assembling schema + examples' },
  { id: 'sql_execution', label: 'SQL Execution', detail: 'Validating and running read-only' },
  { id: 'respond', label: 'Respond', detail: 'Composing the answer' },
]

/** Seed questions drawn from the curated few-shots — grouped by domain. */
export const EXAMPLE_QUESTIONS: Array<{ label: string; question: string; domain: string }> = [
  { domain: 'HR', label: 'Headcount by service line', question: 'How many active employees are in each service line?' },
  { domain: 'HR', label: 'Top earners without a CPA', question: 'Who are the top 5 highest-paid active employees without a CPA?' },
  { domain: 'Billing', label: 'Revenue by service line', question: 'Total revenue by service line for FY2025.' },
  { domain: 'Billing', label: 'Overdue invoices', question: 'Which clients have overdue invoices, and what is the total overdue amount?' },
  { domain: 'Audit', label: 'Engagements over budget', question: 'Which audit engagements are over budget by billed value?' },
  { domain: 'Tax', label: 'Returns due soon', question: 'Which tax returns are unfiled and due within the next 30 days?' },
]

/**
 * Fallback source metadata (from knowledge/sources.yaml) used only when the
 * backend is unreachable, so the schema browser still communicates coverage.
 */
export const FALLBACK_SOURCES: SourceInfo[] = [
  {
    name: 'hr',
    description:
      'People & HR analytics: employees, compensation, performance reviews, certifications, leave, and org structure. Headcount, attrition, pay, tenure, and certification questions.',
    tables: ['offices', 'grades', 'departments', 'employees', 'compensation', 'performance_reviews', 'certifications', 'leave'],
  },
  {
    name: 'audit',
    description:
      'Audit & client delivery: clients, engagements, staffing, timesheets/billable hours, and audit findings. Utilization, budgets, staffing, and findings questions.',
    tables: ['offices', 'grades', 'service_lines', 'clients', 'employees', 'engagements', 'engagement_staffing', 'time_entries', 'audit_findings'],
  },
  {
    name: 'tax',
    description:
      'Tax practice: clients, tax engagements, and tax returns/filings across jurisdictions. Filing deadlines, refunds/balances, and jurisdiction questions.',
    tables: ['clients', 'service_lines', 'engagements', 'tax_returns'],
  },
  {
    name: 'billing',
    description:
      'Billing & finance: invoices, invoice line items, payments, and expenses. Revenue, receivables, overdue invoices, and expense questions.',
    tables: ['clients', 'invoices', 'invoice_line_items', 'payments', 'expenses'],
  },
]
