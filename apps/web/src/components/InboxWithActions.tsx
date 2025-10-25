import { useEffect, useState } from 'react'
import {
  fetchActionsInbox,
  explainMessage,
  fetchMessageDetail,
  postArchive,
  postMarkSafe,
  postMarkSuspicious,
  postUnsubscribe,
  ActionRow,
  MessageDetail,
} from '../lib/api'
import { safeFormatDate } from '../lib/date'
import { Alert, AlertDescription } from './ui/alert'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet'
import { Info } from 'lucide-react'

export default function InboxWithActions() {
  const [rows, setRows] = useState<ActionRow[]>([])
  const [loading, setLoading] = useState(false)
  const [explanations, setExplanations] = useState<Record<string, string>>({})
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Drawer state
  const [openMessageId, setOpenMessageId] = useState<string | null>(null)
  const [messageDetail, setMessageDetail] = useState<Record<string, MessageDetail>>({})
  const [loadingMessageId, setLoadingMessageId] = useState<string | null>(null)

  const loadInbox = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchActionsInbox()
      setRows(data)
    } catch (err) {
      setError('Failed to load inbox:' + String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInbox()
  }, [])

  // Handle opening message drawer
  const handleOpenMessage = async (message_id: string, e?: React.MouseEvent) => {
    // Don't open if clicking on buttons
    if (e && (e.target as HTMLElement).closest('button')) {
      return
    }

    setOpenMessageId(message_id)

    // Fetch detail if not already loaded
    if (!messageDetail[message_id]) {
      setLoadingMessageId(message_id)
      try {
        const detail = await fetchMessageDetail(message_id)
        setMessageDetail(prev => ({ ...prev, [message_id]: detail }))
      } catch (err) {
        setError('Failed to load message detail: ' + String(err))
      } finally {
        setLoadingMessageId(null)
      }
    }
  }

  // Handle explain action (toggle)
  const handleExplain = async (row: ActionRow, e: React.MouseEvent) => {
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
      setExplanations(prev => ({ ...prev, [row.message_id]: result.summary }))
    } catch (err) {
      setError('Explain failed: ' + String(err))
    }
  }

  // Handle archive action
  const handleArchive = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()
    setActionLoading(prev => ({ ...prev, [row.message_id]: true }))
    setError(null)
    setSuccessMsg(null)

    try {
      const res = await postArchive(row.message_id)
      if (res.ok) {
        setSuccessMsg('✅ Email archived')
        setTimeout(() => setSuccessMsg(null), 3000)
        setRows(prev => prev.filter(r => r.message_id !== row.message_id))
        if (openMessageId === row.message_id) setOpenMessageId(null)
      }
    } catch (err: any) {
      const errorMsg = err.message || String(err)
      if (errorMsg.includes('read-only') || errorMsg.includes('403')) {
        setError('⚠️ Actions are read-only in production')
      } else {
        setError('Archive failed: ' + errorMsg)
      }
    } finally {
      setActionLoading(prev => ({ ...prev, [row.message_id]: false }))
    }
  }

  // Handle mark safe action
  const handleMarkSafe = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()
    setActionLoading(prev => ({ ...prev, [row.message_id]: true }))
    setError(null)
    setSuccessMsg(null)

    try {
      const res = await postMarkSafe(row.message_id)
      if (res.ok) {
        setSuccessMsg('✅ Marked as safe')
        setTimeout(() => setSuccessMsg(null), 3000)
        setRows(prev => prev.map(r => {
          if (r.message_id === row.message_id) {
            return {
              ...r,
              reason: {
                ...r.reason,
                risk_score: res.new_risk_score ?? 10,
                quarantined: false,
                signals: ['Manually marked safe', ...r.reason.signals],
              },
            }
          }
          return r
        }))
      }
    } catch (err: any) {
      const errorMsg = err.message || String(err)
      if (errorMsg.includes('read-only') || errorMsg.includes('403')) {
        setError('⚠️ Actions are read-only in production')
      } else {
        setError('Mark safe failed: ' + errorMsg)
      }
    } finally {
      setActionLoading(prev => ({ ...prev, [row.message_id]: false }))
    }
  }

  // Handle mark suspicious action
  const handleMarkSuspicious = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()
    setActionLoading(prev => ({ ...prev, [row.message_id]: true }))
    setError(null)
    setSuccessMsg(null)

    try {
      const res = await postMarkSuspicious(row.message_id)
      if (res.ok) {
        setSuccessMsg('✅ Marked as suspicious')
        setTimeout(() => setSuccessMsg(null), 3000)
        setRows(prev => prev.map(r => {
          if (r.message_id === row.message_id) {
            return {
              ...r,
              reason: {
                ...r.reason,
                risk_score: res.new_risk_score ?? 95,
                quarantined: res.quarantined ?? true,
                signals: ['Flagged suspicious by user', ...r.reason.signals],
              },
            }
          }
          return r
        }))
      }
    } catch (err: any) {
      const errorMsg = err.message || String(err)
      if (errorMsg.includes('read-only') || errorMsg.includes('403')) {
        setError('⚠️ Actions are read-only in production')
      } else {
        setError('Mark suspicious failed: ' + errorMsg)
      }
    } finally {
      setActionLoading(prev => ({ ...prev, [row.message_id]: false }))
    }
  }

  // Handle unsubscribe action
  const handleUnsub = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()
    setActionLoading(prev => ({ ...prev, [row.message_id]: true }))
    setError(null)
    setSuccessMsg(null)

    try {
      const res = await postUnsubscribe(row.message_id)
      if (res.ok) {
        setSuccessMsg('✅ Unsubscribed from sender')
        setTimeout(() => setSuccessMsg(null), 3000)
        // Remove from actionable list like archive
        setRows(prev => prev.filter(r => r.message_id !== row.message_id))
        if (openMessageId === row.message_id) setOpenMessageId(null)
      }
    } catch (err: any) {
      const errorMsg = err.message || String(err)
      if (errorMsg.includes('read-only') || errorMsg.includes('403')) {
        setError('⚠️ Actions are read-only in production')
      } else {
        setError('Unsubscribe failed: ' + errorMsg)
      }
    } finally {
      setActionLoading(prev => ({ ...prev, [row.message_id]: false }))
    }
  }

  const btn = (label: string, onClick: (e: React.MouseEvent) => void, disabled = false, show = true) => {
    if (!show) return null
    return (
      <button
        className="px-2 py-1 text-xs rounded border hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
        onClick={onClick}
        disabled={disabled}
      >
        {label}
      </button>
    )
  }

  return (
    <div className="p-4 grid gap-4">
      <div>
        <h1 className="text-2xl font-bold">📬 Inbox Actions</h1>
        <p className="text-sm text-gray-600">Take quick actions on promotional and bulk emails</p>
      </div>

      {error && (
        <div className="p-3 rounded bg-red-50 text-red-800 text-sm border border-red-200">
          {error}
        </div>
      )}
      {successMsg && (
        <div className="p-3 rounded bg-green-50 text-green-800 text-sm border border-green-200">
          {successMsg}
        </div>
      )}

      <div className="flex justify-between items-center">
        <div className="text-sm text-gray-600">
          {loading ? 'Loading...' : rows.length + ' actionable emails'}
        </div>
        <button
          className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition font-medium"
          onClick={loadInbox}
          disabled={loading}
        >
          {loading ? '⏳ Loading…' : '🔄 Refresh'}
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b-2 border-gray-300">
              <th className="text-left py-3 px-2 font-semibold text-gray-700">From</th>
              <th className="text-left py-3 px-2 font-semibold text-gray-700">Subject</th>
              <th className="text-left py-3 px-2 font-semibold text-gray-700">Received</th>
              <th className="text-left py-3 px-2 font-semibold text-gray-700">Reason</th>
              <th className="text-left py-3 px-2 font-semibold text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-gray-500">
                  🎉 No actionable emails found! Your inbox is clean.
                </td>
              </tr>
            )}
            {rows.map(r => {
              const messageId = r.message_id
              const explanation = explanations[messageId]
              const isActionLoading = actionLoading[messageId]
              const allowedActions = r.allowed_actions || []

              return (
                <>
                  <tr
                    key={messageId}
                    className="border-b border-gray-200 hover:bg-gray-50 align-top cursor-pointer"
                    onClick={(e) => handleOpenMessage(messageId, e)}
                  >
                    <td className="py-3 px-2 text-sm">
                      <div className="text-gray-700 font-medium">{r.from_name || '—'}</div>
                      {r.from_email && <div className="text-xs text-gray-500">{r.from_email}</div>}
                    </td>

                    <td className="py-3 px-2">
                      <div className="font-medium text-gray-900">{r.subject}</div>
                      {r.labels && r.labels.length > 0 && (
                        <div className="mt-1 flex gap-1 flex-wrap">
                          {r.labels.slice(0, 3).map((lbl, i) => (
                            <span key={i} className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700">
                              {lbl.replace('CATEGORY_', '')}
                            </span>
                          ))}
                          {r.labels.length > 3 && <span className="text-xs text-gray-500">+{r.labels.length - 3}</span>}
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-2 text-sm text-gray-500">
                      {safeFormatDate(r.received_at) ?? '—'}
                    </td>

                    <td className="py-3 px-2">
                      <div>
                        <div className="text-sm text-gray-700 mb-1">
                          <span className="font-medium">{r.reason.category}</span>
                          {r.reason.quarantined && (
                            <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700">Quarantined</span>
                          )}
                          {r.reason.risk_score > 50 && (
                            <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700">Risk: {r.reason.risk_score}</span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">{r.reason.signals.slice(0, 2).join(' • ')}</div>
                        {allowedActions.includes('explain') && (
                          <button
                            className="text-xs text-blue-600 hover:underline mt-1"
                            onClick={(e) => handleExplain(r, e)}
                          >
                            {explanation ? '▼ Hide explanation' : '🔍 Explain why'}
                          </button>
                        )}
                      </div>
                    </td>

                    <td className="py-3 px-2">
                      <div className="flex gap-1 flex-wrap">
                        {btn('📥 Archive', (e) => handleArchive(e, r), isActionLoading, allowedActions.includes('archive'))}
                        {btn('✅ Safe', (e) => handleMarkSafe(e, r), isActionLoading, allowedActions.includes('mark_safe'))}
                        {btn('⚠️ Suspicious', (e) => handleMarkSuspicious(e, r), isActionLoading, allowedActions.includes('mark_suspicious'))}
                        {btn('🚫 Unsub', (e) => handleUnsub(e, r), isActionLoading, allowedActions.includes('unsubscribe'))}
                      </div>
                      {isActionLoading && <div className="text-xs text-gray-500 mt-1">Processing...</div>}
                    </td>
                  </tr>

                  {explanation && (
                    <tr key={`${messageId}-explain`}>
                      <td colSpan={5} className="px-2 pb-3">
                        <div className="rounded border border-border bg-muted/20 p-3 text-sm">
                          <strong className="text-gray-900">Explanation:</strong> {explanation}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Message Detail Drawer */}
      <Sheet open={!!openMessageId} onOpenChange={(open) => !open && setOpenMessageId(null)}>
        <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
          {openMessageId && (
            <>
              <SheetHeader>
                <SheetTitle>Email Detail</SheetTitle>
              </SheetHeader>

              {loadingMessageId === openMessageId ? (
                <div className="py-8 text-center text-gray-500">Loading...</div>
              ) : messageDetail[openMessageId] ? (
                <div className="mt-4 space-y-4">
                  {/* Header Info */}
                  <div className="space-y-2 border-b pb-4">
                    <div>
                      <span className="text-xs text-gray-500">From:</span>
                      <div className="text-sm">
                        {messageDetail[openMessageId].from_name && (
                          <span className="font-medium">{messageDetail[openMessageId].from_name} </span>
                        )}
                        <span className="text-gray-600">&lt;{messageDetail[openMessageId].from_email}&gt;</span>
                      </div>
                    </div>
                    {messageDetail[openMessageId].to_email && (
                      <div>
                        <span className="text-xs text-gray-500">To:</span>
                        <div className="text-sm text-gray-600">{messageDetail[openMessageId].to_email}</div>
                      </div>
                    )}
                    <div>
                      <span className="text-xs text-gray-500">Subject:</span>
                      <div className="text-sm font-medium">{messageDetail[openMessageId].subject}</div>
                    </div>
                    <div>
                      <span className="text-xs text-gray-500">Date:</span>
                      <div className="text-sm text-gray-600">
                        {safeFormatDate(messageDetail[openMessageId].received_at) ?? '—'}
                      </div>
                    </div>

                    {/* Risk Badges */}
                    <div className="flex gap-2 flex-wrap pt-2">
                      {messageDetail[openMessageId].category && (
                        <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-700">
                          {messageDetail[openMessageId].category}
                        </span>
                      )}
                      {messageDetail[openMessageId].risk_score !== undefined && messageDetail[openMessageId].risk_score! > 50 && (
                        <span className="text-xs px-2 py-1 rounded bg-orange-100 text-orange-700">
                          Risk: {messageDetail[openMessageId].risk_score}
                        </span>
                      )}
                      {messageDetail[openMessageId].quarantined && (
                        <span className="text-xs px-2 py-1 rounded bg-red-100 text-red-700">
                          Quarantined
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Email Body */}
                  <div className="border rounded p-4 bg-white">
                    {messageDetail[openMessageId].html_body ? (
                      <div
                        className="prose prose-sm max-w-none"
                        dangerouslySetInnerHTML={{ __html: messageDetail[openMessageId].html_body! }}
                      />
                    ) : messageDetail[openMessageId].text_body ? (
                      <pre className="whitespace-pre-wrap text-sm font-sans">
                        {messageDetail[openMessageId].text_body}
                      </pre>
                    ) : (
                      <div className="text-sm text-gray-500 italic">No email body available</div>
                    )}
                  </div>

                  {/* Action Buttons in Drawer */}
                  {(() => {
                    const row = rows.find(r => r.message_id === openMessageId)
                    if (!row) return null
                    const allowed = row.allowed_actions || []
                    const isLoading = actionLoading[openMessageId]

                    return (
                      <div className="border-t pt-4">
                        <div className="text-sm font-medium mb-2">Actions:</div>
                        <div className="flex gap-2 flex-wrap">
                          {allowed.includes('archive') && (
                            <button
                              className="px-3 py-1.5 text-sm rounded border hover:bg-gray-50 disabled:opacity-50 transition"
                              onClick={(e) => handleArchive(e, row)}
                              disabled={isLoading}
                            >
                              📥 Archive
                            </button>
                          )}
                          {allowed.includes('mark_safe') && (
                            <button
                              className="px-3 py-1.5 text-sm rounded border hover:bg-gray-50 disabled:opacity-50 transition"
                              onClick={(e) => handleMarkSafe(e, row)}
                              disabled={isLoading}
                            >
                              ✅ Mark Safe
                            </button>
                          )}
                          {allowed.includes('mark_suspicious') && (
                            <button
                              className="px-3 py-1.5 text-sm rounded border hover:bg-gray-50 disabled:opacity-50 transition"
                              onClick={(e) => handleMarkSuspicious(e, row)}
                              disabled={isLoading}
                            >
                              ⚠️ Mark Suspicious
                            </button>
                          )}
                          {allowed.includes('unsubscribe') && (
                            <button
                              className="px-3 py-1.5 text-sm rounded border hover:bg-gray-50 disabled:opacity-50 transition"
                              onClick={(e) => handleUnsub(e, row)}
                              disabled={isLoading}
                            >
                              🚫 Unsubscribe
                            </button>
                          )}
                        </div>
                        {isLoading && <div className="text-xs text-gray-500 mt-2">Processing...</div>}
                      </div>
                    )
                  })()}
                </div>
              ) : (
                <div className="py-8 text-center text-gray-500">Email not found</div>
              )}
            </>
          )}
        </SheetContent>
      </Sheet>

      <Alert className="mt-4">
        <Info className="h-4 w-4" />
        <AlertDescription>
          <strong>Actions:</strong> Mark emails as safe/suspicious to train the risk model. Archive removes them from this view. Unsubscribe marks the sender as muted.
          {!rows.some(r => r.allowed_actions.includes('archive')) && (
            <span className="ml-2 text-orange-700">(Mutations are read-only in production)</span>
          )}
        </AlertDescription>
      </Alert>
    </div>
  )
}
