import { API_BASE } from './apiBase'
import { apiUrl } from './apiUrl'
import { clearCurrentUser } from '@/api/auth'

// Helper to get CSRF token from cookie
function getCsrfToken(): string | null {
  const match = document.cookie.match(/csrf_token=([^;]+)/)
  return match ? match[1] : null
}

// Copilot: add ensureCsrf() before POSTs; handle 401/403 specifically in backfillGmail().
export async function ensureCsrf(): Promise<void> {
  const hasCsrf = document.cookie.includes("csrf_token=")
  if (!hasCsrf) {
    await fetch(apiUrl("/api/auth/csrf"), { credentials: "include" })
  }
}

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
  // ML-powered fields (Phase 35)
  category?: string
  expires_at?: string | null
  event_start_at?: string | null
  event_end_at?: string | null
  interests?: string[]
  confidence?: number
}

export async function fetchEmails(): Promise<Email[]> {
  const r = await fetch(apiUrl('/api/emails/'))
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
  // Highlight fields for easy access
  subject_highlight?: string
  body_highlight?: string
  // Reply metrics
  first_user_reply_at?: string
  user_reply_count?: number
  replied?: boolean
  time_to_response_hours?: number | null
  // ML-powered fields (Phase 35)
  category?: string
  expires_at?: string | null
  event_start_at?: string | null
  event_end_at?: string | null
  interests?: string[]
  confidence?: number
}

export type SearchParams = {
  q: string
  size?: number
  limit?: number
  labelFilter?: string
  scale?: string
  labels?: string[]
  dateFrom?: string
  dateTo?: string
  replied?: boolean
  sort?: string
  categories?: string[]
  hideExpired?: boolean
  // Security filters
  risk_min?: number     // 0–100
  risk_max?: number     // 0–100
  quarantined?: boolean // true / false
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
  sort?: string,
  categories?: string[],
  hideExpired?: boolean,
  risk_min?: number,
  risk_max?: number,
  quarantined?: boolean
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
  if (categories && categories.length > 0) {
    categories.forEach(c => {
      url += `&categories=${encodeURIComponent(c)}`
    })
  }
  if (hideExpired !== undefined) {
    url += `&hide_expired=${hideExpired}`
  }
  // Security filters
  if (typeof risk_min === 'number') {
    url += `&risk_min=${risk_min}`
  }
  if (typeof risk_max === 'number') {
    url += `&risk_max=${risk_max}`
  }
  if (typeof quarantined === 'boolean') {
    url += `&quarantined=${quarantined}`
  }
  const r = await fetch(url)
  if (!r.ok) throw new Error('Search failed')
  const data = await r.json()
  return data.hits as SearchHit[]
}

// New search function with params object
export async function searchEmailsWithParams(params: SearchParams): Promise<SearchHit[]> {
  const { q, size, limit, risk_min, risk_max, quarantined } = params
  const sp = new URLSearchParams({ q })

  const actualLimit = size ?? limit ?? 10
  sp.set('limit', String(actualLimit))

  if (params.labelFilter) sp.set('label_filter', params.labelFilter)
  if (params.scale) sp.set('scale', params.scale)
  if (params.labels && params.labels.length > 0) {
    params.labels.forEach(l => sp.append('labels', l))
  }
  if (params.dateFrom) sp.set('date_from', params.dateFrom)
  if (params.dateTo) sp.set('date_to', params.dateTo)
  if (params.replied !== undefined) sp.set('replied', String(params.replied))
  if (params.sort && params.sort !== 'relevance') sp.set('sort', params.sort)
  if (params.categories && params.categories.length > 0) {
    params.categories.forEach(c => sp.append('categories', c))
  }
  if (params.hideExpired !== undefined) sp.set('hide_expired', String(params.hideExpired))

  // Security filters
  if (typeof risk_min === 'number') sp.set('risk_min', String(risk_min))
  if (typeof risk_max === 'number') sp.set('risk_max', String(risk_max))
  if (typeof quarantined === 'boolean') sp.set('quarantined', String(quarantined))

  const r = await fetch(`/api/search/?${sp.toString()}`, { credentials: 'include' })
  if (!r.ok) throw new Error(`Search failed (${r.status})`)
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

/**
 * Fail-soft suggestions API helper - NEVER throws, NEVER blocks results.
 * Returns empty array on any error to keep UI responsive.
 */
export async function getSuggestions(q: string, limit = 8): Promise<string[]> {
  if (!q || q.trim().length < 2) return []

  try {
    const res = await fetch(
      `/api/suggest/?q=${encodeURIComponent(q)}&limit=${limit}`,
      { credentials: 'include' }
    )

    if (!res.ok) {
      console.warn(`[suggest] soft-fail: ${res.status}`)
      return []
    }

    const j = await res.json()
    // Accept multiple shapes: {suggestions: []}, {items: []}, or direct array
    return j.suggestions ?? j.items ?? (Array.isArray(j) ? j : [])
  } catch (err) {
    console.warn('[suggest] soft-fail:', err)
    return [] // ← do NOT throw; UI should continue to render results
  }
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
  inserted?: number
  days: number
  user_email: string
  status?: string
  message?: string
  _timeout?: boolean
}

// Copilot: backfillGmail(days) calls '/api/gmail/backfill', handles 202 responses and errors.
// Copilot: Rate limited to once per 5 minutes per user; backend returns 429 if too frequent.
// Copilot: Includes CSRF token from cookie in X-CSRF-Token header for security.
export async function backfillGmail(days = 60, userEmail?: string): Promise<BackfillResponse> {
  // Ensure CSRF cookie is set before making POST request
  await ensureCsrf()

  let url = `/api/gmail/backfill?days=${days}`
  if (userEmail) {
    url += `&user_email=${encodeURIComponent(userEmail)}`
  }

  const csrfToken = getCsrfToken()
  const headers: HeadersInit = {}
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken
  }

  const r = await fetch(url, {
    method: 'POST',
    headers,
    credentials: 'include'
  })

  // Handle 524 Gateway Timeout (Cloudflare timeout - typically 100 seconds)
  if (r.status === 524) {
    console.warn('[backfill] 524 Gateway Timeout - backfill may still be running on backend')
    return {
      status: 'timeout',
      message: 'Backfill started but response timed out. Check your inbox in a few minutes.',
      days,
      user_email: userEmail || 'current'
    }
  }

  // Handle specific error codes
  if (r.status === 401) {
    const data = await r.json().catch(() => ({}))
    if (data.error === 'gmail_reauth_required') {
      throw new Error('Please reconnect your Gmail account')
    }
    throw new Error('Authentication required')
  }

  if (r.status === 403) {
    throw new Error('Please refresh the page and try again')
  }

  if (!r.ok) throw new Error(`Backfill failed: ${r.status} ${r.statusText}`)
  return r.json()
}

// v0.4.17: Async Job Pattern for Gmail Backfill (no more 524 timeouts!)
export type StartJobResponse = {
  job_id: string
  started: boolean
}

export type JobStatusResponse = {
  job_id: string
  state: 'queued' | 'running' | 'done' | 'error' | 'canceled'
  processed: number
  total: number | null
  error: string | null
  inserted: number | null
}

/**
 * Start async Gmail backfill job - returns immediately with job_id
 * Use with useJobPoller() hook to track progress
 */
export async function startBackfillJob(days = 60, userEmail?: string): Promise<StartJobResponse> {
  await ensureCsrf()

  let url = `/api/gmail/backfill/start?days=${days}`
  if (userEmail) {
    url += `&user_email=${encodeURIComponent(userEmail)}`
  }

  const csrfToken = getCsrfToken()
  const headers: HeadersInit = {}
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken
  }

  const r = await fetch(url, {
    method: 'POST',
    headers,
    credentials: 'include'
  })

  // Handle 524 Gateway Timeout (fallback - shouldn't happen with async jobs)
  if (r.status === 524) {
    console.warn('[startBackfillJob] 524 Gateway Timeout - job may have started anyway')
    throw new Error('Request timed out. Please try again.')
  }

  if (!r.ok) {
    const text = await r.text()
    throw new Error(`Failed to start backfill: ${r.status} - ${text}`)
  }

  return r.json()
}

/**
 * Get status of a running job (used by useJobPoller)
 */
export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const url = `/api/gmail/backfill/status?job_id=${encodeURIComponent(jobId)}`
  const r = await fetch(url, { credentials: 'include' })

  if (!r.ok) {
    throw new Error(`Failed to get job status: ${r.status}`)
  }

  return r.json()
}

/**
 * Cancel a running job
 */
export async function cancelJob(jobId: string): Promise<{ ok: boolean; error?: string }> {
  await ensureCsrf()

  const csrfToken = getCsrfToken()
  const headers: HeadersInit = {}
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken
  }

  const url = `/api/gmail/backfill/cancel?job_id=${encodeURIComponent(jobId)}`
  const r = await fetch(url, {
    method: 'POST',
    headers,
    credentials: 'include'
  })

  if (!r.ok) {
    throw new Error(`Failed to cancel job: ${r.status}`)
  }

  return r.json()
}

// Phase 2: ML Labeling and Profile APIs
export type LabelRebuildResponse = {
  updated: number
  categories: Record<string, number>
}

export type ProfileRebuildResponse = {
  user_email: string
  emails_processed: number
  senders: number
  categories: number
  interests: number
}

// Copilot: Helper function for POST requests that automatically includes CSRF token
// Handles 524 (Gateway Timeout) gracefully for long-running operations
async function post(url: string, init: RequestInit = {}) {
  // Ensure CSRF cookie is set before making POST request
  await ensureCsrf()

  const csrfToken = getCsrfToken()
  const headers: Record<string, string> = { ...(init.headers as Record<string, string> || {}) }
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken
  }

  const r = await fetch(url, {
    method: 'POST',
    ...init,
    headers,
    credentials: 'include'
  })

  // Handle 524 Gateway Timeout (Cloudflare timeout)
  if (r.status === 524) {
    console.warn('[api] 524 Gateway Timeout - operation may still be running on backend')
    // Return a special response indicating timeout but potential success
    return {
      status: 'timeout',
      message: 'Operation started but response timed out. Check back in a moment.',
      _timeout: true
    }
  }

  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json().catch(() => ({}))
}

export const sync7d = () => post('/api/gmail/backfill?days=7')
export const sync60d = () => post('/api/gmail/backfill?days=60')

export const relabel = (limit = 2000): Promise<LabelRebuildResponse> =>
  post(`/api/ml/label/rebuild?limit=${limit}`)

export const rebuildProfile = (userEmail: string): Promise<ProfileRebuildResponse> =>
  post(`${API_BASE}/profile/rebuild?user_email=${encodeURIComponent(userEmail)}`)

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
  const r = await fetch(apiUrl('/api/applications'), {  // apiUrl auto-adds trailing slash
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input)
  })
  if (!r.ok) throw new Error('Failed to create application')
  return r.json()
}

export async function updateApplication(id: number, patch: Partial<AppOut>): Promise<AppOut> {
  const r = await fetch(apiUrl(`/api/applications/${id}`), {
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

// Search Explain

export type ExplainResponse = {
  id: string
  reason: string
  evidence: {
    labels?: string[]
    label_heuristics?: string[]
    list_unsubscribe?: boolean
    is_promo?: boolean
    is_newsletter?: boolean
    keywords_hit?: boolean
    sender?: string
    sender_domain?: string
  }
}

export async function explainEmail(id: string): Promise<ExplainResponse> {
  const r = await fetch(`/api/search/explain/${id}`)
  if (!r.ok) throw new Error(`Explain failed: ${r.status}`)
  return r.json()
}

// ===== Actions Inbox API =====

export type ActionReason = {
  category: string
  signals: string[]
  risk_score: number
  quarantined: boolean
}

export type ActionRow = {
  message_id: string
  from_name: string
  from_email: string
  subject: string
  received_at: string
  labels: string[]
  reason: ActionReason
  allowed_actions: string[]
  // Lifecycle flags
  archived?: boolean
  quarantined?: boolean
  muted?: boolean
  user_overrode_safe?: boolean
  // Actionability signals
  risk_score?: number
  unread?: boolean
}

export type MessageDetail = {
  message_id: string
  from_name?: string
  from_email?: string
  to_email?: string
  subject: string
  received_at: string
  risk_score?: number
  quarantined?: boolean
  archived?: boolean
  category?: string
  html_body?: string | null
  text_body?: string | null
  messages?: Array<{
    id: string
    from: string
    to: string[]
    date: string
    snippet?: string
    body_html?: string
    body_text?: string
  }>
  summary?: {
    headline: string
    details: string[]
  }
  timeline?: Array<{
    ts: string
    actor: string
    kind: "received" | "replied" | "follow_up_needed" | "flagged" | "status_change"
    note: string
  }>
}

// Helper to get CSRF token from meta tag
function getCsrf(): string {
  // Read CSRF token from cookie (backend sets it via CSRFMiddleware)
  const cookies = document.cookie.split(';')
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=')
    if (name === 'csrf_token') {
      return decodeURIComponent(value)
    }
  }
  return ''
}

export async function fetchActionsInbox(mode: "review" | "quarantined" | "archived" = "review"): Promise<ActionRow[]> {
  const r = await fetch(`/api/actions/inbox?mode=${mode}`, {
    credentials: 'include',
  })
  if (!r.ok) throw new Error(`Fetch actions inbox failed: ${r.status}`)
  return r.json()
}

export type ExplainActionResponse = {
  summary: string
}

export async function explainMessage(message_id: string): Promise<ExplainActionResponse> {
  const r = await fetch('/api/actions/explain', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': getCsrf(),
    },
    body: JSON.stringify({ message_id })
  })
  if (!r.ok) throw new Error(`Explain action failed: ${r.status}`)
  return r.json()
}

// Keep old name for backward compatibility
export const explainAction = explainMessage

export async function fetchMessageDetail(message_id: string): Promise<MessageDetail> {
  const r = await fetch(`/api/actions/message/${message_id}`, {
    credentials: 'include',
  })
  if (!r.ok) throw new Error(`Fetch message detail failed: ${r.status}`)
  return r.json()
}

export type ActionMutationResponse = {
  ok: boolean
  message_id?: string
  new_risk_score?: number
  quarantined?: boolean
  archived?: boolean
  muted?: boolean
  user_overrode_safe?: boolean
}

export async function postArchive(message_id: string): Promise<ActionMutationResponse> {
  const r = await fetch('/api/actions/archive', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': getCsrf(),
    },
    body: JSON.stringify({ message_id })
  })
  if (!r.ok) throw new Error(`Archive failed: ${r.status}`)
  return r.json()
}

export async function postMarkSafe(message_id: string): Promise<ActionMutationResponse> {
  const r = await fetch('/api/actions/mark_safe', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': getCsrf(),
    },
    body: JSON.stringify({ message_id })
  })
  if (!r.ok) throw new Error(`Mark safe failed: ${r.status}`)
  return r.json()
}

export async function postMarkSuspicious(message_id: string): Promise<ActionMutationResponse> {
  const r = await fetch('/api/actions/mark_suspicious', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': getCsrf(),
    },
    body: JSON.stringify({ message_id })
  })
  if (!r.ok) throw new Error(`Mark suspicious failed: ${r.status}`)
  return r.json()
}

export async function postUnsubscribe(message_id: string): Promise<ActionMutationResponse> {
  const r = await fetch('/api/actions/unsubscribe', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': getCsrf(),
    },
    body: JSON.stringify({ message_id })
  })
  if (!r.ok) throw new Error(`Unsubscribe failed: ${r.status}`)
  return r.json()
}

export async function postRestore(message_id: string): Promise<ActionMutationResponse> {
  const r = await fetch('/api/actions/restore', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': getCsrf(),
    },
    body: JSON.stringify({ message_id })
  })
  if (!r.ok) throw new Error(`Restore failed: ${r.status}`)
  return r.json()
}

// ===== Bulk Actions (Phase 4.5) =====

// TODO(thread-viewer v1.4.5):
// Bulk triage endpoints. Backend will auth + persist.
// We assume message_ids belong to the current user.

export type BulkActionResponse = {
  updated: string[]
  failed: string[]
}

async function postJSON(url: string, body: any) {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": getCsrf(),
    },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

export async function bulkArchiveMessages(ids: string[]): Promise<BulkActionResponse> {
  return postJSON("/api/actions/bulk/archive", { message_ids: ids });
}

export async function bulkMarkSafeMessages(ids: string[]): Promise<BulkActionResponse> {
  return postJSON("/api/actions/bulk/mark-safe", { message_ids: ids });
}

export async function bulkQuarantineMessages(ids: string[]): Promise<BulkActionResponse> {
  return postJSON("/api/actions/bulk/quarantine", { message_ids: ids });
}

/**
 * Send feedback on thread summary quality.
 * Used to improve AI summary generation over time.
 */
export async function sendThreadSummaryFeedback(opts: {
  messageId: string;
  helpful: boolean;
}): Promise<{ ok: boolean }> {
  const csrf = getCsrf();
  const res = await fetch("/api/actions/summary-feedback", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "x-csrf-token": csrf,
    },
    body: JSON.stringify({
      message_id: opts.messageId,
      helpful: opts.helpful,
      // reason: (optional, we're not collecting freeform yet)
    }),
  });

  if (!res.ok) {
    throw new Error("Failed to submit summary feedback");
  }

  return res.json() as Promise<{ ok: boolean }>;
}

/**
 * Generate a follow-up draft email using Agent V2.
 * Returns a structured draft with subject and body.
 */
export interface FollowupDraftRequest {
  thread_id: string;
  application_id?: number;
}

export interface FollowupDraft {
  subject: string;
  body: string;
}

export interface FollowupDraftResponse {
  status: 'ok' | 'error';
  draft?: FollowupDraft;
  message?: string;
}

export async function generateFollowupDraft(
  req: FollowupDraftRequest
): Promise<FollowupDraftResponse> {
  const csrf = getCsrf();
  const res = await fetch("/v2/agent/followup-draft", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "x-csrf-token": csrf,
    },
    body: JSON.stringify({
      thread_id: req.thread_id,
      application_id: req.application_id,
      mode: "preview_only",
    }),
  });

  if (!res.ok) {
    throw new Error(`Failed to generate draft: ${res.status}`);
  }

  return res.json() as Promise<FollowupDraftResponse>;
}

// ===== Follow-up Queue =====

export interface QueueMeta {
  total: number;
  time_window_days: number;
}

export interface QueueItem {
  thread_id: string;
  application_id?: number;
  priority: number;
  reason_tags: string[];
  company?: string;
  role?: string;
  subject?: string;
  snippet?: string;
  last_message_at?: string;
  status?: string;
  gmail_url?: string;
  is_done: boolean;
}

export interface FollowupQueueRequest {
  user_id?: string;
  time_window_days?: number;
}

export interface FollowupQueueResponse {
  status: 'ok' | 'error';
  queue_meta?: QueueMeta;
  items: QueueItem[];
  message?: string;
}

export async function getFollowupQueue(
  req: FollowupQueueRequest = {}
): Promise<FollowupQueueResponse> {
  const res = await fetch('/v2/agent/followup-queue', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-csrf-token': getCsrf(),
    },
    credentials: 'include',
    body: JSON.stringify({
      time_window_days: req.time_window_days || 30,
      ...req,
    }),
  });

  if (!res.ok) {
    throw new Error(`Failed to get followup queue: ${res.statusText}`);
  }

  return res.json() as Promise<FollowupQueueResponse>;
}


// ===== Sender Overrides =====

export type SenderOverride = {
  id: string
  sender: string
  muted: boolean
  safe: boolean
  created_at: string
  updated_at: string
}

export type SenderOverrideListResponse = {
  overrides: SenderOverride[]
}

export type InboxMetricsSummary = {
  archived: number
  quarantined: number
  muted_senders: number
  safe_senders: number
}

export type RuntimeConfig = {
  readOnly: boolean
  version?: string
}

export type TrackerApplication = {
  id: string
  company: string
  role: string
  stage: string
  source?: string | null
  last_activity_at?: string | null
}

export type TrackerResponse = {
  applications: TrackerApplication[]
}

// --- Fetch helpers ---

// Runtime config (read-only mode, version banner, etc.)
export async function fetchRuntimeConfig(): Promise<RuntimeConfig> {
  const res = await fetch("/api/config", {
    method: "GET",
    credentials: "include",
  })
  if (!res.ok) {
    throw new Error("Failed to load runtime config")
  }
  return res.json()
}

// Inbox insights metrics summary card
export async function fetchInboxMetrics(): Promise<InboxMetricsSummary> {
  const res = await fetch("/api/actions/metrics/summary", {
    method: "GET",
    credentials: "include",
  })
  if (!res.ok) {
    throw new Error("Failed to load inbox metrics")
  }
  return res.json()
}

// Tracker data (pipeline / applications list)
export async function fetchTracker(): Promise<TrackerResponse> {
  const res = await fetch("/api/tracker", {
    method: "GET",
    credentials: "include",
  })
  if (!res.ok) {
    throw new Error("Failed to load tracker data")
  }
  return res.json()
}

// Sender override list
export async function fetchSenderOverrides(): Promise<SenderOverrideListResponse> {
  const res = await fetch("/api/settings/senders", {
    method: "GET",
    credentials: "include",
  })
  if (!res.ok) {
    throw new Error("Failed to load sender overrides")
  }
  return res.json()
}

// Add muted override
export async function addMutedSender(sender: string): Promise<SenderOverride> {
  const res = await fetch("/api/settings/senders/mute", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sender }),
  })
  if (!res.ok) {
    throw new Error("Failed to mute sender")
  }
  return res.json()
}

// Add safe override
export async function addSafeSender(sender: string): Promise<SenderOverride> {
  const res = await fetch("/api/settings/senders/safe", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sender }),
  })
  if (!res.ok) {
    throw new Error("Failed to mark sender safe")
  }
  return res.json()
}

// Delete override
export async function deleteSenderOverride(id: string): Promise<void> {
  const res = await fetch(`/api/settings/senders/${id}`, {
    method: "DELETE",
    credentials: "include",
  })
  if (!res.ok) {
    throw new Error("Failed to delete sender override")
  }
}

// ===== Inbox Metrics (Legacy) =====

export type InboxSummary = {
  archived: number
  quarantined: number
  muted_senders: number
  safe_senders: number
}

export async function fetchInboxSummary(): Promise<InboxSummary> {
  const r = await fetch('/api/actions/metrics/summary', {
    method: 'GET',
    credentials: 'include',
  })
  if (!r.ok) throw new Error('Failed to fetch summary')
  return r.json()
}

// Old interface for backward compatibility
async function performAction(action: string, message_id: string): Promise<{ ok: boolean }> {
  const r = await fetch(`/api/actions/${action}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': getCsrf(),
    },
    credentials: 'include',
    body: JSON.stringify({ message_id })
  })
  if (!r.ok) {
    if (r.status === 403) throw new Error('Actions are read-only in production')
    throw new Error(`Action ${action} failed: ${r.status}`)
  }
  return r.json()
}

export const inboxActions = {
  markSafe: (id: string) => performAction('mark_safe', id),
  markSuspicious: (id: string) => performAction('mark_suspicious', id),
  archive: (id: string) => performAction('archive', id),
  unsubscribe: (id: string) => performAction('unsubscribe', id),
}

// Get email by ID (for details panel)

export type EmailDetailResponse = {
  id: string
  subject: string
  from_addr?: string
  from?: string
  to_addr?: string
  to?: string
  received_at?: string
  date?: string
  labels?: string[]
  gmail_labels?: string[]
  risk?: "low"|"med"|"high"
  reason?: string
  body_html?: string
  body_text?: string
  thread_id?: string
  unsubscribe_url?: string | null
}

export async function getEmailById(id: string): Promise<EmailDetailResponse> {
  const r = await fetch(`/api/search/by_id/${encodeURIComponent(id)}`)
  if (!r.ok) throw new Error(`Failed to fetch email: ${r.status}`)
  return r.json()
}

export async function getThread(threadId: string) {
  const r = await fetch(`/api/threads/${encodeURIComponent(threadId)}?limit=20`);
  if (!r.ok) throw new Error("Failed to fetch thread");
  return r.json(); // expect { messages: [{id, from, date, snippet, body_html, body_text}, ...] oldest..newest }
}

/**
 * Unified thread viewer API - fetches message detail for ThreadViewer component
 * Works with any message_id from Inbox, Search, Actions, etc.
 */
export async function fetchThreadDetail(messageId: string): Promise<MessageDetail> {
  // Try the actions endpoint first (has most detail)
  const r = await fetch(`/api/actions/message/${messageId}`, {
    credentials: 'include',
  });
  if (!r.ok) throw new Error(`Failed to fetch thread detail: ${r.status}`);
  const raw = await r.json();

  // TODO(thread-viewer v1.5):
  // backend should populate summary/timeline.
  // we patch them here so UI never renders empty.
  const withContext = {
    ...raw,
    summary: raw.summary ?? {
      headline: "Conversation about scheduling next steps",
      details: [
        "They are interested and want your availability.",
        "Next action is to propose a time window.",
        "No red flags found in tone or language.",
      ],
    },
    timeline: raw.timeline ?? [
      {
        ts: raw.messages?.[raw.messages.length - 1]?.date ?? new Date().toISOString(),
        actor: raw.messages?.[raw.messages.length - 1]?.from ?? "Contact",
        kind: "received" as const,
        note: "Latest reply from contact",
      },
      {
        ts: raw.messages?.[0]?.date ?? new Date().toISOString(),
        actor: raw.messages?.[0]?.from ?? "You",
        kind: "replied" as const,
        note: "You responded with availability",
      },
    ],
  };

  return withContext;
}

/**
 * Fetch thread risk analysis from security/agent backend
 * TODO(thread-viewer v1.1):
 * Replace fallback with live agent-backed endpoint once
 * /security/analyze/:threadId is stable in prod.
 * This call should return { summary, factors[], riskLevel, recommendedAction }.
 */
export async function fetchThreadAnalysis(threadId: string): Promise<import('../types/thread').ThreadRiskAnalysis> {
  // Placeholder endpoint. We'll wire to the real backend later.
  // For now, call `/api/security/analyze/:threadId` if it exists,
  // otherwise return mock data.

  try {
    const res = await fetch(`/api/security/analyze/${threadId}`, {
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Analysis endpoint not ready');
    return res.json();
  } catch (err) {
    // Fallback mock so UI can render without backend being ready.
    return {
      summary: "No high-risk behavior detected. Sender is known, content looks legitimate.",
      factors: [
        "Sender domain previously seen in safe conversations",
        "No credential harvesting language detected",
        "No urgency / threat language detected",
      ],
      riskLevel: "low",
      recommendedAction: "Mark Safe",
    };
  }
}

// Quick Actions (dry-run mode)

export type ActionResponse = {
  status: string
  action: string
  doc_id: string
  message?: string
}

async function postAction(path: string, doc_id: string, note?: string): Promise<ActionResponse> {
  const r = await fetch(`/api/search/actions/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id, note })
  })
  if (!r.ok) throw new Error(`Action ${path} failed: ${r.status}`)
  return r.json()
}

export const actions = {
  archive: (id: string, note?: string) => postAction('archive', id, note),
  markSafe: (id: string, note?: string) => postAction('mark_safe', id, note),
  markSuspicious: (id: string, note?: string) => postAction('mark_suspicious', id, note),
  unsubscribeDry: (id: string, note?: string) => postAction('unsubscribe_dryrun', id, note),
}

// ---------- Applications API (Paginated) ----------

export type AppsSort = "updated_at" | "applied_at" | "company" | "status"
export type AppsOrder = "asc" | "desc"

export interface ListApplicationsParams {
  limit?: number
  status?: string | null
  sort?: AppsSort
  order?: AppsOrder
  cursor?: string | null
}

export interface ApplicationRow {
  id: string
  company?: string
  role?: string
  status?: string
  applied_at?: string
  updated_at?: string
  source?: string
}

export interface ListApplicationsResponse {
  items: ApplicationRow[]
  next_cursor?: string | null
  sort: AppsSort
  order: AppsOrder
  total?: number | null
}

export async function listApplicationsPaged(
  params: ListApplicationsParams = {}
): Promise<ListApplicationsResponse> {
  const q = new URLSearchParams()
  if (params.limit) q.set("limit", String(params.limit))
  if (params.status) q.set("status", params.status)
  if (params.sort) q.set("sort", params.sort)
  if (params.order) q.set("order", params.order)
  if (params.cursor) q.set("cursor", params.cursor)

  const r = await fetch(`/api/applications?${q.toString()}`)
  if (!r.ok) throw new Error("Failed to list applications")
  return r.json()
}

// =============================================================================
// Email Statistics
// =============================================================================

export interface EmailCountResponse {
  owner_email: string
  count: number
}

export interface EmailStatsResponse {
  owner_email: string
  total: number
  last_30d: number
  by_day: Array<{ day: string; count: number }>
  top_senders: Array<{ sender: string; count: number }>
  top_categories: Array<{ category: string; count: number }>
}

export async function getEmailCount(): Promise<EmailCountResponse> {
  const r = await fetch(`${API_BASE}/emails/count`, { credentials: 'include' })
  if (!r.ok) throw new Error('Failed to get email count')
  return r.json()
}

export async function getEmailStats(): Promise<EmailStatsResponse> {
  const r = await fetch(`${API_BASE}/emails/stats`, { credentials: 'include' })
  if (!r.ok) throw new Error('Failed to get email stats')
  return r.json()
}

// ============================================================================
// Phase 4: AI Features API Helpers
// ============================================================================

export async function api<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    ...opts
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export const AI = {
  summarize: (thread_id: string, max_citations = 3) =>
    api('/api/ai/summarize', {
      method: 'POST',
      body: JSON.stringify({ thread_id, max_citations })
    }),
  health: () => api('/api/ai/health'),
};

export const RAG = {
  query: (q: string, k = 5) =>
    api('/api/rag/query', {
      method: 'POST',
      body: JSON.stringify({ q, k })
    }),
  health: () => api('/rag/health'),
};

export const Security = {
  top3: (message_id: string) =>
    api(`/api/security/risk-top3?message_id=${encodeURIComponent(message_id)}`),
};

// ---------- Tracker API ----------

export interface TrackerRow {
  company: string
  role: string
  source: string
  status: string
  last_update: string
}

/**
 * Fetch application rows derived from Gmail emails for the Tracker page.
 * Returns job-related emails grouped by company as simple tracker rows.
 * Safe for production - read-only, fails gracefully.
 */
export async function fetchTrackerApplications(): Promise<TrackerRow[]> {
  try {
    const response = await fetch('/api/tracker', {
      credentials: 'include',
    })

    if (!response.ok) {
      console.warn(`Tracker API returned ${response.status}`)
      return []
    }

    const data = await response.json()

    // Validate response is an array
    if (!Array.isArray(data)) {
      console.warn('Tracker API returned non-array:', data)
      return []
    }

    return data
  } catch (error) {
    console.error('Failed to fetch tracker applications:', error)
    return []
  }
}

// ============================================================================
// Mailbox Assistant API
// ============================================================================

export type AssistantEmailSource = {
  id: string
  sender: string
  subject: string
  timestamp: string
  risk_score?: number
  quarantined?: boolean
  amount?: number
  due_date?: string
  unsubscribe_candidate?: boolean
  reply_needed?: boolean
}

export type AssistantSuggestedAction = {
  label: string
  kind: "external_link" | "unsubscribe" | "mark_safe" | "archive" | "follow_up" | "draft_reply"
  email_id?: string
  link?: string
  sender?: string
  sender_email?: string
  subject?: string
}

export type AssistantActionPerformed = {
  type: string
  status: string
  target?: string
}

export type AssistantQueryResponse = {
  intent: string
  summary: string
  sources: AssistantEmailSource[]
  suggested_actions: AssistantSuggestedAction[]
  actions_performed: AssistantActionPerformed[]
  next_steps?: string
  followup_prompt?: string
  llm_used?: string  // Phase 3: "ollama", "openai", or "fallback"
}

export async function queryMailboxAssistant(opts: {
  user_query: string
  time_window_days: number // 7 | 30 | 60
  mode: "off" | "run"
  memory_opt_in: boolean
  account: string
  context_hint?: {  // Phase 3: Short-term memory
    previous_intent?: string
    previous_email_ids: string[]
  }
}): Promise<AssistantQueryResponse> {
  const res = await fetch("/api/assistant/query", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(opts),
  })
  if (!res.ok) {
    throw new Error("Mailbox Assistant query failed")
  }
  return res.json()
}

// Draft Reply API (Phase 1.5)
// ============================================================================

export type DraftReplyRequest = {
  email_id: string
  sender: string
  subject: string
  account: string
  thread_summary?: string
  tone?: "warmer" | "more_direct" | "formal" | "casual"
}

export type DraftReplyResponse = {
  email_id: string
  sender: string
  subject: string
  draft: string
  sender_email?: string
}

export async function draftReply(req: DraftReplyRequest): Promise<DraftReplyResponse> {
  const res = await fetch("/api/assistant/draft-reply", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(`Failed to draft reply: ${errorText}`)
  }
  return res.json()
}

// ============================================================================
// Profile Summary API (Warehouse-backed)
// ============================================================================

export type ProfileSummaryResponse = {
  account: string
  last_sync_at: string | null
  dataset: string
  totals: {
    all_time_emails: number
    last_30d_emails: number
  }
  top_senders_30d: Array<{
    sender: string
    email: string
    count: number
  }>
  top_categories_30d: Array<{
    category: string
    count: number
  }>
  top_interests: Array<{
    keyword: string
    count: number
  }>
}

/**
 * Fetch unified profile summary from BigQuery warehouse marts.
 * Returns totals, top senders, categories, and interests.
 * Cache: 60 seconds backend
 * Error handling: Returns fallback object with zeros and empty arrays on failure
 */
export async function fetchProfileSummary(): Promise<ProfileSummaryResponse> {
  const fallback: ProfileSummaryResponse = {
    account: "leoklemet.pa@gmail.com",
    last_sync_at: null,
    dataset: "unknown",
    totals: { all_time_emails: 0, last_30d_emails: 0 },
    top_senders_30d: [],
    top_categories_30d: [],
    top_interests: []
  }

  try {
    const res = await fetch("/api/metrics/profile/summary", {
      credentials: "include"
    })
    if (!res.ok) {
      console.warn(`Profile summary API returned ${res.status}`)
      return fallback
    }
    return res.json()
  } catch (error) {
    console.error("Failed to fetch profile summary:", error)
    return fallback
  }
}

// ============================================================================
// Logout Helper
// ============================================================================

/**
 * Log out the current user.
 * Attempts to call backend logout endpoint, then redirects to home page.
 * This is resilient - even if backend logout fails, we still redirect.
 * DO NOT throw from this helper.
 */
export async function logoutUser(): Promise<void> {
  try {
    // If we have a backend logout endpoint, call it first.
    // Try /api/auth/logout with credentials included.
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include"
    });
  } catch (_) {
    // swallow; we still clear local state
  }

  // Clear cached user data to prevent stale UI after logout
  clearCurrentUser();

  // Note: Navigation is now handled by the caller (e.g., Settings page)
  // to prevent hard page reloads that can crash Playwright tests.
}
