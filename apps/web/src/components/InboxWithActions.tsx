import { useEffect, useState } from 'react'
import {
  fetchActionsInbox,
  explainMessage,
  postArchive,
  postMarkSafe,
  postMarkSuspicious,
  postUnsubscribe,
  postRestore,
  fetchInboxSummary,
  ActionRow,
  InboxSummary,
} from '../lib/api'
import { safeFormatDate } from '../lib/date'
import { Alert, AlertDescription } from './ui/alert'
import { Badge } from './ui/badge'
import { Info } from 'lucide-react'
import { cn } from '../lib/utils'
import { HeaderSettingsDropdown } from './HeaderSettingsDropdown'
import { NavTabs } from './NavTabs'
import { ThreadViewer } from './ThreadViewer'
import { useThreadViewer } from '../hooks/useThreadViewer'

// Helper: ActionButton component
function ActionButton({
  label,
  onClick,
  disabled,
  tone = 'default',
}: {
  label: string
  onClick: (e: React.MouseEvent) => void
  disabled?: boolean
  tone?: 'default' | 'success' | 'warn' | 'danger' | 'ghost'
}) {
  const base =
    'px-2 py-1 rounded text-[11px] border flex items-center gap-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  const toneClass = {
    default: 'bg-muted/20 hover:bg-muted/30 border-border',
    success:
      'bg-emerald-600/20 text-emerald-200 border-emerald-700 hover:bg-emerald-600/30',
    warn: 'bg-amber-600/20 text-amber-200 border-amber-700 hover:bg-amber-600/30',
    danger:
      'bg-red-700/20 text-red-200 border-red-800 hover:bg-red-700/30',
    ghost:
      'bg-transparent border-border hover:bg-muted/20 text-foreground',
  }[tone]

  return (
    <button
      type="button"
      className={`${base} ${toneClass}`}
      disabled={disabled}
      onClick={onClick}
    >
      {label}
    </button>
  )
}

export default function InboxWithActions() {
  const [rows, setRows] = useState<ActionRow[]>([])
  const [loading, setLoading] = useState(false)
  const [rowLoading, setRowLoading] = useState<Record<string, boolean>>({})
  const [explanations, setExplanations] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'review' | 'quarantined' | 'archived'>('review')
  const [summary, setSummary] = useState<InboxSummary | null>(null)
  const [summaryError, setSummaryError] = useState<string | null>(null)

  // Thread viewer state (replaces old drawer state)
  const thread = useThreadViewer(rows.map(r => ({ id: r.message_id })))

  // Phase 4: derived values for ThreadViewer
  const totalCount = thread.items.length;
  // TODO(thread-viewer v1.4.5):
  // handledCount is now driven by local optimistic state.
  // Eventually this should come from the canonical row model (server-sourced),
  // but this is good enough for operator UX.
  const handledCount = thread.items.filter(
    (it: any) => it.archived || it.quarantined
  ).length;

  const bulkCount = thread.selectedBulkIds.size;

  const loadInbox = async (mode: 'review' | 'quarantined' | 'archived' = viewMode) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchActionsInbox(mode)
      setRows(data)
    } catch (err) {
      setError('Failed to load inbox: ' + String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInbox()
    // Load summary metrics with error handling
    let ignore = false
    async function loadSummary() {
      try {
        const data = await fetchInboxSummary()
        if (!ignore) {
          setSummary(data)
          setSummaryError(null)
        }
      } catch (err) {
        if (!ignore) {
          setSummaryError('Failed to load insights')
          console.error('Inbox summary error:', err)
        }
      }
    }
    loadSummary()
    return () => {
      ignore = true
    }
  }, [])

  // Handle tab change
  const handleChangeMode = async (mode: 'review' | 'quarantined' | 'archived') => {
    setViewMode(mode)
    await loadInbox(mode)
    // If currently open message is no longer in this mode, close the detail panel
    if (thread.selectedId) {
      const stillThere = rows.find(r => r.message_id === thread.selectedId)
      if (!stillThere) {
        thread.closeThread()
      }
    }
  }

  // Helper: set row busy state
  function setRowBusy(id: string, busy: boolean) {
    setRowLoading(prev => ({ ...prev, [id]: busy }))
  }

  // Handle opening message drawer - now uses shared ThreadViewer
  const handleOpenMessage = (message_id: string) => {
    thread.showThread(message_id)
  }

  // Handle explain action (toggle)
  const handleExplain = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()

    // If already showing, collapse it
    if (explanations[row.message_id]) {
      setExplanations(prev => {
        const copy = { ...prev }
        delete copy[row.message_id]
        return copy
      })
      return
    }

    try {
      const result = await explainMessage(row.message_id)
      setExplanations(prev => ({
        ...prev,
        [row.message_id]: result.summary,
      }))
    } catch (err) {
      setError('Explain failed: ' + String(err))
    }
  }

  // Handle archive action
  const handleArchive = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()
    setRowBusy(row.message_id, true)
    try {
      const res = await postArchive(row.message_id)
      if (res.ok) {
        setRows(prev => prev.filter(r => r.message_id !== row.message_id))
        if (thread.selectedId === row.message_id) thread.closeThread()
      }
    } catch (err) {
      setError('Archive failed: ' + String(err))
    } finally {
      setRowBusy(row.message_id, false)
    }
  }

  // Handle mark safe action
  const handleMarkSafe = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()
    setRowBusy(row.message_id, true)
    try {
      const res = await postMarkSafe(row.message_id)
      if (res.ok) {
        // Mark Safe moves item to Archived - remove from current view
        setRows(prev => prev.filter(r => r.message_id !== row.message_id))
        if (thread.selectedId === row.message_id) thread.closeThread()
      }
    } catch (err) {
      setError('Mark safe failed: ' + String(err))
    } finally {
      setRowBusy(row.message_id, false)
    }
  }

  // Handle mark suspicious action
  const handleMarkSuspicious = async (
    e: React.MouseEvent,
    row: ActionRow
  ) => {
    e.stopPropagation()
    setRowBusy(row.message_id, true)
    try {
      const res = await postMarkSuspicious(row.message_id)
      if (res.ok) {
        // Mark Suspicious moves item to Quarantined - remove from current view
        setRows(prev => prev.filter(r => r.message_id !== row.message_id))
        if (thread.selectedId === row.message_id) thread.closeThread()
      }
    } catch (err) {
      setError('Mark suspicious failed: ' + String(err))
    } finally {
      setRowBusy(row.message_id, false)
    }
  }

  // Handle unsubscribe action
  const handleUnsub = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()
    setRowBusy(row.message_id, true)
    try {
      const res = await postUnsubscribe(row.message_id)
      if (res.ok) {
        // treat unsubscribe same as archive: remove from actionable list
        setRows(prev => prev.filter(r => r.message_id !== row.message_id))
        if (thread.selectedId === row.message_id) thread.closeThread()
      }
    } catch (err) {
      setError('Unsubscribe failed: ' + String(err))
    } finally {
      setRowBusy(row.message_id, false)
    }
  }

  // Handle restore to review action
  const handleRestore = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()
    setRowBusy(row.message_id, true)
    try {
      const res = await postRestore(row.message_id)
      if (res.ok) {
        // Remove from current view (Quarantined or Archived)
        setRows(prev => prev.filter(r => r.message_id !== row.message_id))
        if (thread.selectedId === row.message_id) thread.closeThread()
      }
    } catch (err) {
      setError('Restore failed: ' + String(err))
    } finally {
      setRowBusy(row.message_id, false)
    }
  }

  // Render action buttons for a given message
  function renderActionButtonsFor(message_id: string | null) {
    if (!message_id) return null
    const row = rows.find(r => r.message_id === message_id)
    if (!row) return null

    const disabled = !!rowLoading[message_id]
    const allow = (action: string) => row.allowed_actions.includes(action)

    return (
      <>
        {allow('archive') && (
          <ActionButton
            label="Archive"
            onClick={e => handleArchive(e, row)}
            disabled={disabled}
            tone="default"
          />
        )}
        {allow('mark_safe') && (
          <ActionButton
            label="Safe"
            onClick={e => handleMarkSafe(e, row)}
            disabled={disabled}
            tone="success"
          />
        )}
        {allow('mark_suspicious') && (
          <ActionButton
            label="Suspicious"
            onClick={e => handleMarkSuspicious(e, row)}
            disabled={disabled}
            tone="warn"
          />
        )}
        {allow('unsubscribe') && (
          <ActionButton
            label="Unsub"
            onClick={e => handleUnsub(e, row)}
            disabled={disabled}
            tone="danger"
          />
        )}
        {allow('explain') && (
          <ActionButton
            label={
              explanations[message_id] ? 'Hide why' : 'Explain why'
            }
            onClick={e => handleExplain(e, row)}
            disabled={false}
            tone="ghost"
          />
        )}
        {/* Show Restore button only in Quarantined and Archived views */}
        {(viewMode === 'quarantined' || viewMode === 'archived') && allow('archive') && (
          <ActionButton
            label="Restore to Review"
            onClick={e => handleRestore(e, row)}
            disabled={disabled}
            tone="default"
          />
        )}
      </>
    )
  }

  // Render detail pane
  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto">
      <header className="mb-6 flex items-start justify-between px-4 pt-4 pb-2 border-b border-border/50 bg-background/60 backdrop-blur-xl rounded-t-lg">
        <div className="flex flex-col gap-2">
          <NavTabs />
          <p className="text-[11px] text-muted-foreground">
            Review offers, track pipeline, mute junk.
          </p>
        </div>
        <HeaderSettingsDropdown />
      </header>

      {/* View Mode Tabs */}
      <div className="flex items-center gap-2 text-xs mb-4">
        <button
          className={
            viewMode === 'review'
              ? 'px-2 py-1 rounded bg-primary text-primary-foreground border border-primary text-[11px]'
              : 'px-2 py-1 rounded bg-muted/20 border border-border hover:bg-muted/30 text-[11px]'
          }
          onClick={() => handleChangeMode('review')}
        >
          Needs Review
        </button>

        <button
          className={
            viewMode === 'quarantined'
              ? 'px-2 py-1 rounded bg-primary text-primary-foreground border border-primary text-[11px]'
              : 'px-2 py-1 rounded bg-muted/20 border border-border hover:bg-muted/30 text-[11px]'
          }
          onClick={() => handleChangeMode('quarantined')}
        >
          Quarantined
        </button>

        <button
          className={
            viewMode === 'archived'
              ? 'px-2 py-1 rounded bg-primary text-primary-foreground border border-primary text-[11px]'
              : 'px-2 py-1 rounded bg-muted/20 border border-border hover:bg-muted/30 text-[11px]'
          }
          onClick={() => handleChangeMode('archived')}
        >
          Archived
        </button>
      </div>

      {/* Summary Metrics Card */}
      {summaryError ? (
        <div className="text-[11px] text-red-400/80 border border-red-400/20 rounded-md p-3 mb-4 max-w-xl">
          {summaryError}
        </div>
      ) : summary ? (
        <div className="text-[11px] text-muted-foreground border border-border rounded-md p-3 leading-relaxed mb-4 max-w-xl">
          <div className="flex flex-wrap gap-4">
            <div>
              <div className="font-semibold text-foreground text-xs">
                {summary.quarantined}
              </div>
              <div className="text-[11px]">Quarantined</div>
            </div>
            <div>
              <div className="font-semibold text-foreground text-xs">
                {summary.archived}
              </div>
              <div className="text-[11px]">Archived</div>
            </div>
            <div>
              <div className="font-semibold text-foreground text-xs">
                {summary.muted_senders}
              </div>
              <div className="text-[11px] whitespace-nowrap">Muted senders</div>
            </div>
            <div>
              <div className="font-semibold text-foreground text-xs">
                {summary.safe_senders}
              </div>
              <div className="text-[11px] whitespace-nowrap">Safe senders</div>
            </div>
          </div>
        </div>
      ) : null}

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading && rows.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          Loading inbox...
        </div>
      ) : rows.length === 0 ? (
        <Alert className="max-w-md">
          <Info className="h-4 w-4" />
          <AlertDescription>
            No actionable emails found. All clean! 🎉
          </AlertDescription>
        </Alert>
      ) : (
        <div className="flex gap-4">
          {/* Left: Table */}
          <div className="flex-1 min-w-0">
            <div className="rounded-lg border border-border bg-card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b border-border">
                  <tr>
                    <th className="px-2 py-2 w-8">
                      {/* TODO(thread-viewer v1.4): Add "select all" checkbox here */}
                    </th>
                    <th className="px-4 py-2 text-left font-medium">From</th>
                    <th className="px-4 py-2 text-left font-medium">
                      Subject
                    </th>
                    <th className="px-4 py-2 text-left font-medium">
                      Received
                    </th>
                    <th className="px-4 py-2 text-left font-medium">
                      Reason
                    </th>
                    <th className="px-4 py-2 text-left font-medium">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(row => (
                    <>
                      <tr
                        key={row.message_id}
                        className={cn(
                          'cursor-pointer hover:bg-muted/20 border-b border-border',
                          thread.selectedId === row.message_id &&
                            'bg-muted/30 ring-1 ring-border'
                        )}
                      >
                        <td className="px-2 py-3">
                          {/* TODO(thread-viewer v1.4):
                              bulk triage selection checkbox.
                              Eventually we'll hide this unless we're in "batch mode" UI.
                          */}
                          <input
                            type="checkbox"
                            className="h-3 w-3 rounded border-zinc-400 text-zinc-800 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
                            checked={thread.selectedBulkIds.has(row.message_id)}
                            onChange={() => thread.toggleBulkSelect(row.message_id)}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </td>
                        <td className="px-4 py-3" onClick={() => handleOpenMessage(row.message_id)}>{row.from_name}</td>
                        <td className="px-4 py-3" onClick={() => handleOpenMessage(row.message_id)}>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span>{row.subject}</span>
                            {row.quarantined && (
                              <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
                                Quarantined
                              </Badge>
                            )}
                            {row.user_overrode_safe && (
                              <Badge variant="default" className="text-[10px] px-1.5 py-0 bg-emerald-600/20 text-emerald-200 border-emerald-700">
                                Safe by you
                              </Badge>
                            )}
                            {row.muted && (
                              <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                                Muted
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground" onClick={() => handleOpenMessage(row.message_id)}>
                          {safeFormatDate(row.received_at)}
                        </td>
                        <td className="px-4 py-3" onClick={() => handleOpenMessage(row.message_id)}>
                          <div className="text-xs space-y-1">
                            <div className="font-medium">
                              {row.reason.category}
                            </div>
                            <div className="text-muted-foreground">
                              Risk: {row.reason.risk_score}/100
                              {row.reason.quarantined && (
                                <span className="ml-2 text-red-400">
                                  🔒 Quarantined
                                </span>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {renderActionButtonsFor(row.message_id)}
                          </div>
                        </td>
                      </tr>
                      {explanations[row.message_id] && (
                        <tr className="bg-muted/10">
                          <td
                            colSpan={6}
                            className="px-4 py-3 border-b border-border"
                          >
                            <div className="text-xs rounded-md border border-border bg-background/60 p-3 leading-relaxed">
                              {explanations[row.message_id]}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              {rows.length} actionable email{rows.length !== 1 ? 's' : ''}
            </div>
          </div>
        </div>
      )}

      {/* Lifecycle Model Explanation */}
      <div className="mt-6 text-[11px] text-muted-foreground border border-border rounded-md p-3 leading-relaxed max-w-3xl">
        <span className="font-medium">Views:</span>
        <br />
        <span className="font-semibold">Needs Review</span>: Bulk, promo, or
        risky mail we think you should look at.
        <br />
        <span className="font-semibold">Quarantined</span>: Messages you or the
        system flagged as suspicious. We keep them away from your main view.
        <br />
        <span className="font-semibold">Archived</span>: Messages you've handled
        (archived, marked safe, or muted). We won't bug you about them again.
      </div>

      {/* Thread Viewer Drawer */}
      <ThreadViewer
        emailId={thread.selectedId}
        isOpen={thread.isOpen}
        onClose={thread.closeThread}
        goPrev={thread.goPrev}
        goNext={thread.goNext}
        advanceAfterAction={thread.advanceAfterAction}
        items={thread.items}
        selectedIndex={thread.selectedIndex}
        autoAdvance={thread.autoAdvance}
        setAutoAdvance={(val) => thread.setAutoAdvance(val)}
        handledCount={handledCount}
        totalCount={totalCount}
        bulkCount={bulkCount}
        onBulkArchive={thread.bulkArchive}
        onBulkMarkSafe={thread.bulkMarkSafe}
        onBulkQuarantine={thread.bulkQuarantine}
        onArchive={(id) => {
          const row = rows.find(r => r.message_id === id);
          if (row) handleArchive({ stopPropagation: () => {} } as React.MouseEvent, row);
        }}
        onMarkSafe={(id) => {
          const row = rows.find(r => r.message_id === id);
          if (row) handleMarkSafe({ stopPropagation: () => {} } as React.MouseEvent, row);
        }}
        onQuarantine={(id) => {
          const row = rows.find(r => r.message_id === id);
          if (row) handleMarkSuspicious({ stopPropagation: () => {} } as React.MouseEvent, row);
        }}
      />
    </div>
  )
}
