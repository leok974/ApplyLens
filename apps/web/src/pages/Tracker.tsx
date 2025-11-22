import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listApplications, updateApplication, createApplication, AppOut, AppStatus, fetchTrackerApplications, TrackerRow } from '../lib/api'
import { needsFollowup } from '../lib/trackerFilters'
import StatusChip from '../components/StatusChip'
import InlineNote from '../components/InlineNote'
import CreateFromEmailButton from '../components/CreateFromEmailButton'
import { NOTE_SNIPPETS } from '../config/tracker'
import { Mail } from 'lucide-react'

// Toast variants for different status transitions
type ToastVariant = 'default' | 'success' | 'warning' | 'error' | 'info'

const STATUS_TO_TOAST_VARIANT: Record<AppStatus, ToastVariant> = {
  applied: 'default',
  hr_screen: 'info',
  interview: 'success',
  offer: 'success',
  rejected: 'error',
  on_hold: 'warning',
  ghosted: 'warning',
}

const STATUS_LABELS: Record<AppStatus, string> = {
  applied: 'Applied',
  hr_screen: 'HR Screen',
  interview: 'Interview',
  offer: 'Offer',
  rejected: 'Rejected',
  on_hold: 'On Hold',
  ghosted: 'Ghosted',
}

const STATUS_OPTIONS: AppStatus[] = ['applied', 'hr_screen', 'interview', 'offer', 'rejected', 'on_hold', 'ghosted']

// Helper to generate Gmail thread link
function gmailLink(threadId?: string): string {
  if (!threadId) return '#'
  return `https://mail.google.com/mail/u/0/#inbox/${threadId}`
}

export default function Tracker() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [applications, setApplications] = useState<AppOut[]>([])
  const [trackerRows, setTrackerRows] = useState<TrackerRow[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState(searchParams.get('q') || '')
  const [statusFilter, setStatusFilter] = useState<AppStatus | ''>(searchParams.get('status') as AppStatus || '')
  const [fromMailboxFilter, setFromMailboxFilter] = useState(false)
  const [needsFollowupFilter, setNeedsFollowupFilter] = useState(false)
  const [toast, setToast] = useState<{ message: string; variant: ToastVariant } | null>(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ company: '', role: '', source: '' })
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null)
  const selectedRowRef = useRef<HTMLDivElement | null>(null)
  // Show toast helper
  const showToast = (message: string, variant: ToastVariant = 'default') => {
    setToast({ message, variant })
    setTimeout(() => setToast(null), 3000)
  }

  // Show toast notification if application was just created
  useEffect(() => {
    if (searchParams.get('created') === '1') {
      const label = decodeURIComponent(searchParams.get('label') || 'Application')
      showToast(`${label} added to tracker`, 'success')

      // Remove query params from URL
      const newParams = new URLSearchParams(searchParams)
      newParams.delete('created')
      newParams.delete('label')
      setSearchParams(newParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  // Handle deep-link from Thread Viewer via ?appId=<id>
  useEffect(() => {
    const appIdParam = searchParams.get('appId')
    if (appIdParam) {
      const appId = parseInt(appIdParam, 10)
      if (!isNaN(appId)) {
        setSelectedAppId(appId)
        // Clear the param after reading it
        const newParams = new URLSearchParams(searchParams)
        newParams.delete('appId')
        setSearchParams(newParams, { replace: true })
      }
    }
  }, [searchParams, setSearchParams])

  // Scroll to selected row when data loads
  useEffect(() => {
    if (selectedAppId && !loading && selectedRowRef.current) {
      // scrollIntoView may not be available in test environment
      if (typeof selectedRowRef.current.scrollIntoView === 'function') {
        selectedRowRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }, [selectedAppId, loading])

  const fetchRows = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (statusFilter) params.status = statusFilter
      if (search) params.company = search
      const data = await listApplications(params)
      // Ensure we always have an array, even if API returns null/undefined
      setApplications(Array.isArray(data) ? data : [])

      // Also fetch tracker rows from Gmail if we have no applications
      if (!data || data.length === 0) {
        const tracker = await fetchTrackerApplications()
        setTrackerRows(tracker)
      } else {
        setTrackerRows([])
      }
    } catch (error) {
      console.error('Failed to load applications:', error)
      showToast('Failed to load applications', 'error')
      // Don't crash the page - set empty array
      setApplications([])
      // Try to fetch tracker data as fallback
      try {
        const tracker = await fetchTrackerApplications()
        setTrackerRows(tracker)
      } catch (trackerError) {
        console.error('Failed to load tracker data:', trackerError)
        setTrackerRows([])
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRows()
  }, [statusFilter])

  const createRow = async () => {
    if (!form.company || !form.role) {
      showToast('Company and role are required', 'error')
      return
    }
    setCreating(true)
    try {
      const created = await createApplication({
        company: form.company,
        role: form.role,
        source: form.source || undefined,
        status: 'applied',
      })
      setForm({ company: '', role: '', source: '' })
      fetchRows()
      showToast(`${created.company} — ${created.role} created`, 'success')
      // Close dialog
      ;(document.getElementById('create-dialog') as any)?.close?.()
    } catch (error) {
      console.error('Failed to create:', error)
      showToast('Failed to create application', 'error')
    } finally {
      setCreating(false)
    }
  }

  const openCreateWithPrefill = (prefill?: Partial<typeof form>) => {
    if (prefill) {
      setForm((f) => ({ ...f, ...prefill }))
    }
    ;(document.getElementById('create-dialog') as any)?.showModal?.()
  }

  const updateRow = async (id: number, patch: Partial<AppOut>, rowForToast?: AppOut) => {
    try {
      await updateApplication(id, patch)
      fetchRows()

      // Show contextual toast
      if (patch.status && rowForToast) {
        const variant = STATUS_TO_TOAST_VARIANT[patch.status as AppStatus]
        const statusLabel = STATUS_LABELS[patch.status as AppStatus]
        showToast(`Status: ${statusLabel} — ${rowForToast.company}`, variant)
      } else {
        showToast('Saved', 'success')
      }
    } catch (error) {
      console.error('Failed to update:', error)
      showToast('Update failed', 'error')
    }
  }

  const gmailLink = (thread?: string | null) => {
    if (!thread) return undefined
    return `https://mail.google.com/mail/u/0/#inbox/${thread}`
  }

  // Calculate metrics from current filtered data
  const metrics = {
    total: applications.length,
    fromMailbox: applications.filter(a => a.thread_id).length,
    needsFollowup: applications.filter(a => needsFollowup(a)).length,
  }

  return (
    <div className="space-y-5">
      {/* Toast notification with variants */}
        {toast && (
          <div
            data-testid="toast"
            data-variant={toast.variant}
            role="status"
            aria-live="polite"
            className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg ${
              toast.variant === 'success' ? 'bg-green-600 text-white' :
              toast.variant === 'error' ? 'bg-red-600 text-white' :
              toast.variant === 'warning' ? 'bg-yellow-500 text-white' :
              toast.variant === 'info' ? 'bg-blue-600 text-white' :
              'bg-gray-800 text-white'
            }`}>
            <div className="flex items-center">
              <span className="mr-2">
                {toast.variant === 'success' ? '✓' :
                 toast.variant === 'error' ? '✗' :
                 toast.variant === 'warning' ? '⚠' :
                 toast.variant === 'info' ? 'ℹ' : '•'}
              </span>
              {(() => {
                // Split on " — " to separate title and desc
                const parts = toast.message.split(/\s*—\s*/)
                if (parts.length > 1) {
                  return (
                    <div>
                      <span data-testid="toast-title">{parts[0]}</span>
                      <span data-testid="toast-desc" className="ml-1">— {parts.slice(1).join(' — ')}</span>
                    </div>
                  )
                }
                // No separator, use full message as title
                return <span data-testid="toast-title">{toast.message}</span>
              })()}
            </div>
          </div>
        )}

      {/* Summary Metrics Tile */}
      {!loading && applications.length > 0 && (
        <div
          data-testid="tracker-summary-tile"
          className="surface-card p-4 border border-zinc-300 dark:border-zinc-700 rounded-lg"
        >
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100" data-testid="metric-total">
                {metrics.total}
              </div>
              <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">Total Applications</div>
            </div>
            <div className="text-center border-l border-zinc-300 dark:border-zinc-700">
              <div className="text-2xl font-bold text-yellow-400" data-testid="metric-from-mailbox">
                {metrics.fromMailbox}
              </div>
              <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">From Mailbox</div>
            </div>
            <div className="text-center border-l border-zinc-300 dark:border-zinc-700">
              <div className="text-2xl font-bold text-cyan-400" data-testid="metric-needs-followup">
                {metrics.needsFollowup}
              </div>
              <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">Needs Follow-up</div>
            </div>
          </div>
        </div>
      )}

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          className="border rounded px-3 py-2 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-sky-500"
          placeholder="Search company or role"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchRows()}
          data-testid="tracker-search-input"
        />
        <button
          className="px-3 py-2 text-sm border rounded hover:bg-gray-50 transition"
          onClick={() => fetchRows()}
          data-testid="tracker-search-btn"
        >
          Search
        </button>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as AppStatus | '')}
          data-testid="tracker-status-filter"
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
        <button
          onClick={() => setFromMailboxFilter(!fromMailboxFilter)}
          data-testid="filter-from-mailbox"
          className={`px-3 py-2 text-sm rounded transition flex items-center gap-2 ${
            fromMailboxFilter
              ? 'bg-yellow-400/20 text-yellow-400 border border-yellow-400/50 hover:bg-yellow-400/30'
              : 'border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800'
          }`}
          title={fromMailboxFilter ? 'Showing only mail-linked applications' : 'Show only applications from mailbox'}
        >
          <Mail className="h-4 w-4" />
          From Mailbox
          {fromMailboxFilter && <span className="font-semibold">✓</span>}
        </button>
        <button
          onClick={() => setNeedsFollowupFilter(!needsFollowupFilter)}
          data-testid="filter-needs-followup"
          className={`px-3 py-2 text-sm rounded transition flex items-center gap-2 ${
            needsFollowupFilter
              ? 'bg-cyan-400/20 text-cyan-400 border border-cyan-400/50 hover:bg-cyan-400/30'
              : 'border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800'
          }`}
          title={needsFollowupFilter ? 'Showing applications that may need follow-up' : 'Show applications that may need follow-up'}
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          Needs follow-up
          {needsFollowupFilter && <span className="font-semibold">✓</span>}
        </button>
        <button
          className="ml-auto px-3 py-2 text-sm border rounded hover:bg-gray-50 transition"
          onClick={() => (document.getElementById('create-dialog') as any)?.showModal?.()}
          data-testid="tracker-new-btn"
        >
          New
        </button>
      </div>

      {/* Applications Table */}
      <div className="surface-card overflow-hidden">
        {(fromMailboxFilter || needsFollowupFilter) && (
          <div className="px-3 py-2 text-xs text-zinc-600 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-800/50 border-b border-zinc-300 dark:border-zinc-700">
            {fromMailboxFilter && needsFollowupFilter && (
              <span>Showing applications from mailbox that may need follow-up</span>
            )}
            {fromMailboxFilter && !needsFollowupFilter && (
              <span>Showing only applications linked to email threads</span>
            )}
            {!fromMailboxFilter && needsFollowupFilter && (
              <span>Showing applications in early stages (applied, HR screen, interview) with email threads</span>
            )}
          </div>
        )}
        <div className="sticky top-0 z-10 grid grid-cols-12 gap-2 surface-panel px-3 py-2 text-xs font-medium border-b border-zinc-300 dark:border-zinc-700">
          <div className="col-span-3">Company</div>
          <div className="col-span-3">Role</div>
          <div className="col-span-2">Source</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-2 text-right">Actions</div>
        </div>
        {loading ? (
          <div className="p-8 text-center text-sm text-zinc-500 dark:text-zinc-400">Loading…</div>
        ) : (
          <div className="divide-y divide-zinc-300 dark:divide-zinc-700">
            {applications
              .filter(a => !fromMailboxFilter || a.thread_id)
              .filter(a => !needsFollowupFilter || needsFollowup(a))
              .map((r) => {
                const isSelected = selectedAppId === r.id
                return (
              <div
                key={`app-${r.id}`}
                ref={isSelected ? selectedRowRef : null}
                className={`grid grid-cols-12 gap-2 items-center px-3 py-2 text-sm transition ${
                  isSelected
                    ? 'bg-yellow-400/10 border-l-4 border-yellow-400 dark:bg-yellow-400/5'
                    : 'hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
                }`}
                data-testid="tracker-row"
                data-id={r.id}
                data-selected={isSelected ? 'true' : undefined}
              >
                <div className="col-span-3 font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                  {r.company}
                  {r.thread_id && (
                    <button
                      onClick={() => window.open(gmailLink(r.thread_id), '_blank')}
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded-full bg-yellow-400/10 text-yellow-400/90 hover:bg-yellow-400/20 border border-yellow-400/20 transition-colors"
                      data-testid="mail-linked-badge"
                      title="Linked to Mailbox Assistant thread - Click to open in Gmail"
                      aria-label={`Open ${r.company} email thread in Gmail`}
                    >
                      <Mail className="h-3 w-3" />
                      <span className="font-medium">Mail</span>
                    </button>
                  )}
                </div>
                <div className="col-span-3 text-zinc-900 dark:text-zinc-100">{r.role}</div>
                <div className="col-span-2 text-zinc-500 dark:text-zinc-400">{r.source || '—'}</div>
                <div className="col-span-2">
                  <div className="flex items-center gap-2">
                    <StatusChip status={r.status} />
                    <select
                      aria-label={`Change status for ${r.company}`}
                      value={r.status}
                      data-testid={`status-select-${r.id}`}
                      onChange={(e) => updateRow(r.id, { status: e.target.value as AppStatus }, r)}
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>
                          {STATUS_LABELS[s]}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="col-span-2 flex flex-col items-end gap-2">
                  {r.thread_id && (
                    <CreateFromEmailButton
                      threadId={r.thread_id}
                      company={r.company}
                      role={r.role}
                      source={r.source || undefined}
                      onPrefill={(prefill) => openCreateWithPrefill(prefill)}
                      onCreated={() => fetchRows()}
                      showToast={showToast}
                    />
                  )}
                  <a
                    className="px-2 py-1 text-sm border rounded hover:bg-white transition self-end"
                    href={gmailLink(r.thread_id)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Thread
                  </a>
                  <div className="w-full">
                    <InlineNote
                      value={r.notes || ''}
                      updatedAt={r.updated_at}
                      testId={`note-${r.id}`}
                      snippets={NOTE_SNIPPETS}
                      onSave={async (next) => {
                        try {
                          await updateApplication(r.id, { notes: next })
                          showToast(`Note saved — ${r.company}`, 'success')
                          await fetchRows()
                        } catch (error) {
                          console.error('Failed to save note:', error)
                          showToast('Save failed', 'error')
                        }
                      }}
                    />
                  </div>
                </div>
              </div>
                )
              })}
            {applications.length === 0 && trackerRows.length > 0 && (
              <>
                {trackerRows.map((row, idx) => (
                  <div
                    key={`tracker-${idx}`}
                    className="grid grid-cols-12 gap-2 items-center px-3 py-2 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition"
                    data-testid="tracker-row-readonly"
                  >
                    <div className="col-span-3 font-semibold text-zinc-900 dark:text-zinc-100">{row.company}</div>
                    <div className="col-span-3 text-zinc-900 dark:text-zinc-100">{row.role}</div>
                    <div className="col-span-2 text-zinc-500 dark:text-zinc-400">{row.source}</div>
                    <div className="col-span-2">
                      <span className="inline-flex items-center rounded-full border border-zinc-300 dark:border-zinc-700 bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 text-xs">
                        {row.status}
                      </span>
                    </div>
                    <div className="col-span-2 text-right text-xs text-zinc-500 dark:text-zinc-400">
                      {new Date(row.last_update).toLocaleString()}
                    </div>
                  </div>
                ))}
                <div className="p-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
                  <p>
                    📧 Showing {trackerRows.length} application{trackerRows.length !== 1 ? 's' : ''} from your Gmail inbox.
                  </p>
                  <p className="mt-2">
                    These are read-only. Click "New" above to create editable applications.
                  </p>
                </div>
              </>
            )}
            {applications.length === 0 && trackerRows.length === 0 && (
              <div className="p-12 text-center">
                <div className="text-6xl mb-4">📭</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No Applications Yet</h3>
                <p className="text-gray-600 mb-4">
                  {statusFilter || search ? 'Try adjusting your filters' : 'Create your first application or sync your Gmail inbox'}
                </p>
                <a
                  href="/inbox"
                  className="inline-block px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  Go to Inbox
                </a>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Create Dialog */}
      <dialog id="create-dialog" className="rounded-xl p-0 border-0">
        <div className="w-[420px]">
          <div className="px-4 py-3 border-b">
            <h3 className="font-semibold">New Application</h3>
          </div>
          <div className="p-4 space-y-3">
            <input
              placeholder="Company"
              className="border rounded px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-sky-500"
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
              data-testid="create-company"
              autoFocus
            />
            <input
              placeholder="Role"
              className="border rounded px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-sky-500"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              data-testid="create-role"
              onKeyDown={(e) => e.key === 'Enter' && createRow()}
            />
            <input
              placeholder="Source (e.g., Lever)"
              className="border rounded px-2 py-2 w-full focus:outline-none focus:ring-2 focus:ring-sky-500"
              value={form.source}
              onChange={(e) => setForm({ ...form, source: e.target.value })}
              data-testid="create-source"
            />
          </div>
          <div className="border-t px-4 py-3 flex justify-end gap-2 bg-gray-50">
            <button
              className="px-3 py-2 text-sm border rounded hover:bg-white transition"
              onClick={() => (document.getElementById('create-dialog') as any)?.close?.()}
            >
              Cancel
            </button>
            <button
              className="px-3 py-2 text-sm border rounded bg-black text-white hover:opacity-90 transition disabled:opacity-50"
              onClick={createRow}
              disabled={creating}
              data-testid="create-save"
            >
              {creating ? 'Creating…' : 'Save'}
            </button>
          </div>
        </div>
      </dialog>
    </div>
  )
}
