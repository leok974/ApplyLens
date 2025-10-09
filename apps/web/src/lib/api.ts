export type Email = {
  id: number
  thread_id: string
  from_addr: string
  subject: string
  label: string
  received_at: string
  gmail_id?: string
  sender?: string
  recipient?: string
  labels?: string[]
  label_heuristics?: string[]
  body_text?: string
  body_preview?: string
  company?: string
  role?: string
  source?: string
  application_id?: number | null
}

export async function fetchEmails(): Promise<Email[]> {
  const r = await fetch('/api/emails/')
  if (!r.ok) throw new Error('Failed to fetch emails')
  return r.json()
}

export type SearchHit = {
  id: number
  subject: string
  from_addr?: string
  sender?: string
  recipient?: string
  label?: string
  labels?: string[]
  label_heuristics?: string[]
  received_at: string
  score: number
  highlight?: { subject?: string[]; body_text?: string[] }
  // Reply metrics
  first_user_reply_at?: string
  user_reply_count?: number
  replied?: boolean
  time_to_response_hours?: number | null
}

export async function searchEmails(
  query: string,
  limit = 10,
  labelFilter?: string,
  scale?: string,
  labels?: string[],
  dateFrom?: string,
  dateTo?: string,
  replied?: boolean,
  sort?: string
): Promise<SearchHit[]> {
  let url = `/api/search/?q=${encodeURIComponent(query)}&limit=${limit}`
  if (labelFilter) {
    url += `&label_filter=${encodeURIComponent(labelFilter)}`
  }
  if (scale) {
    url += `&scale=${encodeURIComponent(scale)}`
  }
  if (labels && labels.length > 0) {
    labels.forEach(l => {
      url += `&labels=${encodeURIComponent(l)}`
    })
  }
  if (dateFrom) {
    url += `&date_from=${encodeURIComponent(dateFrom)}`
  }
  if (dateTo) {
    url += `&date_to=${encodeURIComponent(dateTo)}`
  }
  if (replied !== undefined) {
    url += `&replied=${replied}`
  }
  if (sort && sort !== 'relevance') {
    url += `&sort=${encodeURIComponent(sort)}`
  }
  const r = await fetch(url)
  if (!r.ok) throw new Error('Search failed')
  const data = await r.json()
  return data.hits as SearchHit[]
}

export type UnifiedSuggest = {
  suggestions: string[]
  did_you_mean: string[]
  body_prefix: string[]
}

export async function unifiedSuggest(prefix: string, limit = 8): Promise<UnifiedSuggest> {
  const r = await fetch(`/api/suggest/?q=${encodeURIComponent(prefix)}&limit=${limit}`)
  if (!r.ok) throw new Error('Suggest failed')
  return r.json()
}

// Gmail Integration

export type GmailConnectionStatus = {
  connected: boolean
  user_email?: string
  provider: string
  has_refresh_token: boolean
  total?: number
}

export async function getGmailStatus(userEmail?: string): Promise<GmailConnectionStatus> {
  let url = '/api/gmail/status'
  if (userEmail) {
    url += `?user_email=${encodeURIComponent(userEmail)}`
  }
  const r = await fetch(url)
  if (!r.ok) throw new Error('Failed to fetch Gmail status')
  return r.json()
}

export type GmailInboxResponse = {
  emails: Email[]
  total: number
  page: number
  limit: number
}

export async function getGmailInbox(
  page = 1, 
  limit = 50, 
  labelFilter?: string,
  userEmail?: string
): Promise<GmailInboxResponse> {
  let url = `/api/gmail/inbox?page=${page}&limit=${limit}`
  if (labelFilter) {
    url += `&label_filter=${encodeURIComponent(labelFilter)}`
  }
  if (userEmail) {
    url += `&user_email=${encodeURIComponent(userEmail)}`
  }
  const r = await fetch(url)
  if (!r.ok) throw new Error('Failed to fetch Gmail inbox')
  return r.json()
}

export type BackfillResponse = {
  inserted: number
  days: number
  user_email: string
}

export async function backfillGmail(days = 60, userEmail?: string): Promise<BackfillResponse> {
  let url = `/api/gmail/backfill?days=${days}`
  if (userEmail) {
    url += `&user_email=${encodeURIComponent(userEmail)}`
  }
  const r = await fetch(url, { method: 'POST' })
  if (!r.ok) throw new Error('Backfill failed')
  return r.json()
}

export function initiateGmailAuth() {
  window.location.href = '/api/auth/google/login'
}

// Applications

export type AppStatus = "applied" | "hr_screen" | "interview" | "offer" | "rejected" | "on_hold" | "ghosted"

export type AppOut = {
  id: number
  company: string
  role?: string
  source?: string
  source_confidence?: number
  status: AppStatus
  notes?: string
  thread_id?: string
  created_at?: string
  updated_at?: string
}

export async function listApplications(params?: {
  status?: AppStatus
  company?: string
  q?: string
  limit?: number
}): Promise<AppOut[]> {
  const qs = new URLSearchParams(params as any).toString()
  const url = `/api/applications${qs ? `?${qs}` : ''}`
  const r = await fetch(url)
  if (!r.ok) throw new Error('Failed to list applications')
  return r.json()
}

export async function getApplication(id: number): Promise<AppOut> {
  const r = await fetch(`/api/applications/${id}`)
  if (!r.ok) throw new Error('Failed to get application')
  return r.json()
}

export async function createApplication(input: Partial<AppOut>): Promise<AppOut> {
  const r = await fetch('/api/applications', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input)
  })
  if (!r.ok) throw new Error('Failed to create application')
  return r.json()
}

export async function updateApplication(id: number, patch: Partial<AppOut>): Promise<AppOut> {
  const r = await fetch(`/api/applications/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch)
  })
  if (!r.ok) throw new Error('Failed to update application')
  return r.json()
}

export async function deleteApplication(id: number): Promise<{ ok: boolean }> {
  const r = await fetch(`/api/applications/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error('Failed to delete application')
  return r.json()
}

export type CreateFromEmailResponse = {
  application_id: number
  linked_email_id: number
}

export async function createApplicationFromEmail(emailId: number): Promise<CreateFromEmailResponse> {
  const r = await fetch(`/api/applications/from-email/${emailId}`, { method: 'POST' })
  if (!r.ok) throw new Error('Failed to create application from email')
  return r.json()
}
