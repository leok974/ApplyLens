type Status = 'applied' | 'hr_screen' | 'interview' | 'offer' | 'rejected' | 'on_hold' | 'ghosted'

export type AppRow = {
  id: number
  company: string
  role: string
  source?: string | null
  source_confidence?: number
  status: Status
  last_email_snippet?: string | null
  thread_id?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

const now = () => new Date().toISOString()

export function appRow(overrides: Partial<AppRow> = {}): AppRow {
  const id = overrides.id ?? Math.floor(100 + Math.random() * 900)
  return {
    id,
    company: `Company ${id}`,
    role: 'Engineer',
    source: 'Lever',
    source_confidence: 0.5,
    status: 'applied',
    last_email_snippet: null,
    thread_id: null,
    notes: '',
    created_at: now(),
    updated_at: now(),
    ...overrides,
  }
}

export const listResponse = (rows: AppRow[]) => rows

export function patchResponse(prev: AppRow, patch: Partial<AppRow>): AppRow {
  return { ...prev, ...patch, updated_at: now() }
}
