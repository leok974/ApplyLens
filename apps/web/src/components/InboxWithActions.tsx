import { useEffect, useState } from 'react'
import { fetchActionsInbox, explainAction, inboxActions, ActionRow } from '../lib/api'
import { safeFormatDate } from '../lib/date'
import { Alert, AlertDescription } from './ui/alert'
import { Info } from 'lucide-react'

export default function InboxWithActions() {
  const [rows, setRows] = useState<ActionRow[]>([])
  const [loading, setLoading] = useState(false)
  const [explains, setExplains] = useState<Record<string, string>>({})
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

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

  const doExplain = async (messageId: string) => {
    try {
      const result = await explainAction(messageId)
      setExplains(prev => ({ ...prev, [messageId]: result.summary }))
    } catch (err) {
      setError('Explain failed: ' + String(err))
    }
  }

  const doAction = async (
    action: (id: string) => Promise<{ ok: boolean }>,
    messageId: string,
    actionName: string
  ) => {
    setActionLoading(prev => ({ ...prev, [messageId]: true }))
    setError(null)
    setSuccessMsg(null)
    try {
      await action(messageId)
      setSuccessMsg('✅ ' + actionName + ' action completed successfully')
      setTimeout(() => setSuccessMsg(null), 3000)
      await loadInbox()
    } catch (err: any) {
      const errorMsg = err.message || String(err)
      if (errorMsg.includes('read-only')) {
        setError('⚠️ Actions are read-only in production environment')
      } else {
        setError('Action failed: ' + errorMsg)
      }
    } finally {
      setActionLoading(prev => ({ ...prev, [messageId]: false }))
    }
  }

  const btn = (label: string, onClick: () => void, disabled = false, show = true) => {
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
              const explain = explains[messageId]
              const isActionLoading = actionLoading[messageId]
              const allowedActions = r.allowed_actions || []

              return (
                <tr key={messageId} className="border-b border-gray-200 hover:bg-gray-50 align-top">
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
                    {explain ? (
                      <div className="text-sm">
                        <div className="font-medium text-gray-900">{explain}</div>
                      </div>
                    ) : (
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
                          <button className="text-xs text-blue-600 hover:underline mt-1" onClick={() => doExplain(messageId)}>
                            🔍 Explain why
                          </button>
                        )}
                      </div>
                    )}
                  </td>

                  <td className="py-3 px-2">
                    <div className="flex gap-1 flex-wrap">
                      {btn('📥 Archive', () => doAction(inboxActions.archive, messageId, 'Archive'), isActionLoading, allowedActions.includes('archive'))}
                      {btn('✅ Safe', () => doAction(inboxActions.markSafe, messageId, 'Mark Safe'), isActionLoading, allowedActions.includes('mark_safe'))}
                      {btn('⚠️ Suspicious', () => doAction(inboxActions.markSuspicious, messageId, 'Mark Suspicious'), isActionLoading, allowedActions.includes('mark_suspicious'))}
                      {btn('🚫 Unsub', () => doAction(inboxActions.unsubscribe, messageId, 'Unsubscribe'), isActionLoading, allowedActions.includes('unsubscribe'))}
                    </div>
                    {isActionLoading && <div className="text-xs text-gray-500 mt-1">Processing...</div>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

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
