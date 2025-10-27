import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listApplications, updateApplication, createApplication, AppOut, AppStatus, fetchTrackerApplications, TrackerRow } from '../lib/api'
import StatusChip from '../components/StatusChip'
import InlineNote from '../components/InlineNote'
import CreateFromEmailButton from '../components/CreateFromEmailButton'
import { NOTE_SNIPPETS } from '../config/tracker'

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

export default function Tracker() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [applications, setApplications] = useState<AppOut[]>([])
  const [trackerRows, setTrackerRows] = useState<TrackerRow[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState(searchParams.get('q') || '')
  const [statusFilter, setStatusFilter] = useState<AppStatus | ''>(searchParams.get('status') as AppStatus || '')
  const [toast, setToast] = useState<{ message: string; variant: ToastVariant } | null>(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ company: '', role: '', source: '' })

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

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 dark:bg-[#0f172a] dark:text-zinc-100">
      <div className="p-6 space-y-5">
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
          className="border rounded px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
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
          className="ml-auto px-3 py-2 text-sm border rounded hover:bg-gray-50 transition"
          onClick={() => (document.getElementById('create-dialog') as any)?.showModal?.()}
          data-testid="tracker-new-btn"
        >
          New
        </button>
      </div>

      {/* Applications Table */}
      <div className="surface-card overflow-hidden">
        <div className="sticky top-0 z-10 grid grid-cols-12 gap-2 border-b border-[color:hsl(var(--border))] bg-[color:hsl(var(--muted))] px-3 py-2 text-xs font-medium">
          <div className="col-span-3">Company</div>
          <div className="col-span-3">Role</div>
          <div className="col-span-2">Source</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-2 text-right">Actions</div>
        </div>
        {loading ? (
          <div className="p-8 text-center text-sm text-[color:hsl(var(--muted-foreground))]">Loading…</div>
        ) : (
          <div className="divide-y divide-[color:hsl(var(--border))]">
            {applications.map((r) => (
              <div
                key={`app-${r.id}`}
                className="grid grid-cols-12 gap-2 items-center px-3 py-2 text-sm bg-white dark:bg-zinc-900 border-b border-zinc-300 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition"
                data-testid="tracker-row"
                data-id={r.id}
              >
                <div className="col-span-3 font-semibold text-[color:hsl(var(--foreground))]">{r.company}</div>
                <div className="col-span-3 text-[color:hsl(var(--foreground))]">{r.role}</div>
                <div className="col-span-2 text-[color:hsl(var(--muted-foreground))]">{r.source || '—'}</div>
                <div className="col-span-2">
                  <div className="flex items-center gap-2">
                    <StatusChip status={r.status} />
                    <select
                      aria-label={`Change status for ${r.company}`}
                      className="rounded border border-[color:hsl(var(--border))] bg-[color:hsl(var(--card))] px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-[color:hsl(var(--ring))]"
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
            ))}
            {applications.length === 0 && trackerRows.length > 0 && (
              <>
                {trackerRows.map((row, idx) => (
                  <div
                    key={`tracker-${idx}`}
                    className="grid grid-cols-12 gap-2 items-center px-3 py-2 text-sm hover:bg-[color:hsl(var(--muted))]/30 transition"
                    data-testid="tracker-row-readonly"
                  >
                    <div className="col-span-3 font-semibold text-[color:hsl(var(--foreground))]">{row.company}</div>
                    <div className="col-span-3 text-[color:hsl(var(--foreground))]">{row.role}</div>
                    <div className="col-span-2 text-[color:hsl(var(--muted-foreground))]">{row.source}</div>
                    <div className="col-span-2">
                      <span className="inline-flex items-center rounded-full border px-2 py-0.5 text-xs">
                        {row.status}
                      </span>
                    </div>
                    <div className="col-span-2 text-right text-xs text-[color:hsl(var(--muted-foreground))]">
                      {new Date(row.last_update).toLocaleString()}
                    </div>
                  </div>
                ))}
                <div className="p-6 text-center text-sm text-[color:hsl(var(--muted-foreground))]">
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
    </div>
  )
}
