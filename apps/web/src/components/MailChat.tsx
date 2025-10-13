/**
 * MailChat - Conversational mailbox assistant
 * 
 * Features:
 * - Quick-action chips for common queries
 * - Message history with user/assistant roles
 * - Citations from source emails
 * - Loading states and error handling
 */

import { useState } from 'react'
import { Send, Sparkles, AlertCircle, Mail, Play } from 'lucide-react'
import { sendChatMessage, Message, ChatResponse } from '@/lib/chatClient'
import PolicyAccuracyPanel from '@/components/PolicyAccuracyPanel'

interface QuickAction {
  label: string
  text: string
  icon?: string
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    label: 'Summarize',
    text: 'Summarize recent emails about my job applications.',
    icon: '📧',
  },
  {
    label: 'Bills Due',
    text: 'What bills are due before Friday? Create calendar reminders.',
    icon: '💰',
  },
  {
    label: 'Clean Promos',
    text: 'Clean up promos older than a week unless they\'re from Best Buy.',
    icon: '🧹',
  },
  {
    label: 'Unsubscribe',
    text: 'Unsubscribe from newsletters I haven\'t opened in 60 days.',
    icon: '🚫',
  },
  {
    label: 'Suspicious',
    text: 'Show suspicious emails from new domains this week and explain why.',
    icon: '⚠️',
  },
  {
    label: 'Follow-ups',
    text: 'Which recruiters haven\'t replied in 5 days? Draft follow-ups.',
    icon: '💬',
  },
  {
    label: 'Find Interviews',
    text: 'Find interviews from August with confirmed times.',
    icon: '🔍',
  },
  {
    label: 'Create Tasks',
    text: 'Create tasks from emails about pending action items.',
    icon: '✅',
  },
]

interface ConversationMessage extends Message {
  response?: ChatResponse
  error?: string
}

export default function MailChat() {
  const [messages, setMessages] = useState<ConversationMessage[]>([
    {
      role: 'assistant',
      content:
        'Hi! 👋 Ask me about your mailbox. I can summarize, find, clean, unsubscribe, flag suspicious emails, suggest follow-ups, and create calendar events or tasks.',
    },
  ])
  const [input, setInput] = useState('')
  const [lastQuery, setLastQuery] = useState<string>('')
  const [fileActions, setFileActions] = useState(false)
  const [explain, setExplain] = useState(false)
  const [remember, setRemember] = useState(false)
  const [mode, setMode] = useState<'' | 'networking' | 'money'>('')
  const [intentTokens, setIntentTokens] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dupes, setDupes] = useState<any[] | null>(null)
  const [summary, setSummary] = useState<any | null>(null)

  async function loadDupes() {
    try {
      const r = await fetch('/api/money/duplicates')
      setDupes(await r.json())
    } catch (err) {
      console.error('Failed to load duplicates:', err)
    }
  }

  async function loadSummary() {
    try {
      const r = await fetch('/api/money/summary')
      setSummary(await r.json())
    } catch (err) {
      console.error('Failed to load summary:', err)
    }
  }

  async function send(text: string, opts?: { propose?: boolean; explain?: boolean; remember?: boolean }) {
    if (!text.trim() || busy) return

    setLastQuery(text)
    setError(null)
    setIntentTokens([]) // Reset tokens for new query
    const userMessage: ConversationMessage = { role: 'user', content: text }
    setMessages((m) => [...m, userMessage])
    setInput('')
    setBusy(true)

    // Use streaming SSE for real-time updates
    const shouldPropose = opts?.propose ?? false
    const shouldExplain = opts?.explain ?? false
    const shouldRemember = opts?.remember ?? false
    const url = `/api/chat/stream?q=${encodeURIComponent(text)}`
      + (shouldPropose ? '&propose=1' : '')
      + (shouldExplain ? '&explain=1' : '')
      + (shouldRemember ? '&remember=1' : '')
      + (mode ? `&mode=${encodeURIComponent(mode)}` : '')
    
    let assistantText = ''
    let filedCount = 0

    try {
      const ev = new EventSource(url)
      
      ev.addEventListener('intent', (e: any) => {
        const data = JSON.parse(e.data)
        console.log('[Chat] Intent detected:', data.intent)
      })
      
      ev.addEventListener('intent_explain', (e: any) => {
        const data = JSON.parse(e.data)
        setIntentTokens(data.tokens || [])
        console.log('[Chat] Intent tokens:', data.tokens)
      })
      
      ev.addEventListener('memory', (e: any) => {
        const data = JSON.parse(e.data)
        const brands = data.kept_brands || []
        console.log('[Chat] Learned preferences:', brands)
        
        // Show confirmation message
        if (brands.length > 0) {
          setMessages((m) => [
            ...m,
            {
              role: 'assistant',
              content: `🧠 Learned preference: keep promos for ${brands.join(', ')}`,
            },
          ])
        }
      })

      ev.addEventListener('tool', (e: any) => {
        const data = JSON.parse(e.data)
        console.log('[Chat] Tool result:', data)
        // Update assistant message with tool progress
        if (data.matches !== undefined) {
          assistantText = `*Searching... found ${data.matches} matches*`
          setMessages((m) => {
            const newMessages = [...m]
            // Find or create assistant message for this response
            const lastMsg = newMessages[newMessages.length - 1]
            if (lastMsg.role === 'assistant' && !lastMsg.response) {
              lastMsg.content = assistantText
            } else {
              newMessages.push({ role: 'assistant', content: assistantText })
            }
            return newMessages
          })
        }
      })

      ev.addEventListener('answer', (e: any) => {
        const data = JSON.parse(e.data)
        assistantText = data.answer || data.text || ''
        console.log('[Chat] Answer received:', assistantText.substring(0, 100))
      })

      ev.addEventListener('filed', (e: any) => {
        const data = JSON.parse(e.data)
        filedCount = data.proposed || 0
        console.log('[Chat] Actions filed:', filedCount)
        
        // Show confirmation message
        if (filedCount > 0) {
          setMessages((m) => [
            ...m,
            {
              role: 'assistant',
              content: `✅ Filed ${filedCount} action${filedCount === 1 ? '' : 's'} to Approvals tray.`,
            },
          ])
        }
      })

      ev.addEventListener('done', async () => {
        ev.close()
        
        try {
          // Fetch the full response for citations
          const response = await sendChatMessage({
            messages: [...messages, userMessage].map((m) => ({
              role: m.role,
              content: m.content,
            })),
          })

          // Build final assistant message
          let finalText = assistantText || response.answer

          // Add intent explanation if interesting
          if (response.intent !== 'summarize' && response.intent_explanation) {
            finalText = `*${response.intent_explanation}*\n\n${finalText}`
          }

          // Add action count (only if not already filed)
          if (response.actions.length > 0 && !filedCount) {
            finalText += `\n\n**${response.actions.length} action${response.actions.length === 1 ? '' : 's'} proposed**`
          }

          // Add citations
          if (response.citations.length > 0) {
            finalText += '\n\n**Sources:**'
            response.citations.slice(0, 5).forEach((c) => {
              const date = c.received_at
                ? new Date(c.received_at).toLocaleDateString()
                : ''
              finalText += `\n• ${c.subject} — ${c.sender || '?'} ${date ? `(${date})` : ''}`
            })

            if (response.citations.length > 5) {
              finalText += `\n• ... and ${response.citations.length - 5} more`
            }
          }

          const assistantMessage: ConversationMessage = {
            role: 'assistant',
            content: finalText,
            response,
          }

          // Replace any temporary messages with final response
          setMessages((m) => {
            const newMessages = [...m]
            // Remove temporary assistant messages
            const filtered = newMessages.filter(
              (msg, idx) =>
                !(msg.role === 'assistant' && !msg.response && idx > newMessages.length - 3)
            )
            // Add final message
            filtered.push(assistantMessage)
            return filtered
          })
        } catch (err: any) {
          console.error('[Chat] Error fetching final response:', err)
          // Use whatever we got from the stream
          setMessages((m) => [
            ...m,
            {
              role: 'assistant',
              content: assistantText || 'Response received.',
            },
          ])
        } finally {
          setBusy(false)
        }
      })

      ev.addEventListener('error', (e: any) => {
        console.error('[Chat] EventSource error:', e)
        ev.close()
        
        const errorMsg = 'Stream connection failed'
        setError(errorMsg)
        setMessages((m) => [
          ...m,
          {
            role: 'assistant',
            content: `❌ Error: ${errorMsg}`,
            error: errorMsg,
          },
        ])
        setBusy(false)
      })

    } catch (err: any) {
      const errorMsg = err.message || 'Failed to get response'
      setError(errorMsg)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: `❌ Error: ${errorMsg}`,
          error: errorMsg,
        },
      ])
      setBusy(false)
    }
  }

  function handleKeyPress(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input, { propose: fileActions, explain, remember })
    }
  }

  return (
    <div className="max-w-7xl mx-auto p-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chat Column */}
        <div className="lg:col-span-2 space-y-4">
          {/* Header */}
          <div className="flex items-center gap-3 pb-2 border-b border-neutral-800">
            <Sparkles className="w-6 h-6 text-emerald-500" />
            <div>
              <h2 className="text-xl font-semibold">Mailbox Assistant</h2>
              <p className="text-sm text-neutral-400">
                Ask questions about your emails in natural language
              </p>
            </div>
          </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.label}
            onClick={() => send(action.text)}
            disabled={busy}
            className="px-3 py-1.5 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-xs transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
          >
            {action.icon && <span>{action.icon}</span>}
            <span>{action.label}</span>
          </button>
        ))}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="rounded-xl bg-red-950/30 border border-red-900/50 p-3 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-red-300">{error}</div>
        </div>
      )}

      {/* Message History */}
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-4 space-y-4 min-h-[400px] max-h-[600px] overflow-y-auto">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={msg.role === 'user' ? 'text-right' : 'text-left'}
          >
            <div
              className={`inline-block max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                msg.role === 'user'
                  ? 'bg-emerald-600/20 border border-emerald-600/30'
                  : msg.error
                  ? 'bg-red-950/30 border border-red-900/50'
                  : 'bg-neutral-800/50'
              }`}
            >
              {/* Message content with markdown-style formatting */}
              <div className="whitespace-pre-wrap break-words">
                {msg.content.split('\n').map((line, lineIdx) => {
                  // Handle bold **text**
                  const boldParts = line.split(/(\*\*.*?\*\*)/)
                  return (
                    <div key={lineIdx}>
                      {boldParts.map((part, partIdx) => {
                        if (part.startsWith('**') && part.endsWith('**')) {
                          return (
                            <strong key={partIdx}>
                              {part.slice(2, -2)}
                            </strong>
                          )
                        }
                        // Handle italic *text*
                        const italicParts = part.split(/(\*.*?\*)/)
                        return italicParts.map((iPart, iIdx) => {
                          if (
                            iPart.startsWith('*') &&
                            iPart.endsWith('*') &&
                            iPart.length > 2
                          ) {
                            return (
                              <em
                                key={`${partIdx}-${iIdx}`}
                                className="text-neutral-400"
                              >
                                {iPart.slice(1, -1)}
                              </em>
                            )
                          }
                          return (
                            <span key={`${partIdx}-${iIdx}`}>{iPart}</span>
                          )
                        })
                      })}
                    </div>
                  )
                })}
              </div>

              {/* Response metadata (for debugging) */}
              {msg.response && (
                <div className="mt-2 pt-2 border-t border-neutral-700 text-xs text-neutral-500">
                  <div className="flex items-center gap-2">
                    <Mail className="w-3 h-3" />
                    <span>
                      {msg.response.search_stats.returned_results} emails
                      searched • {msg.response.intent} intent
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {busy && (
          <div className="text-left">
            <div className="inline-block bg-neutral-800/50 rounded-2xl px-4 py-2.5">
              <div className="flex items-center gap-2 text-sm text-neutral-400">
                <div className="flex gap-1">
                  <div
                    className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce"
                    style={{ animationDelay: '0ms' }}
                  />
                  <div
                    className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce"
                    style={{ animationDelay: '150ms' }}
                  />
                  <div
                    className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce"
                    style={{ animationDelay: '300ms' }}
                  />
                </div>
                <span>Thinking...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Bar */}
      <div className="flex flex-wrap gap-2 items-center">
        <input
          className="flex-1 min-w-[200px] rounded-xl bg-neutral-900 border border-neutral-800 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 placeholder:text-neutral-500"
          placeholder="Ask your mailbox anything..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          disabled={busy}
        />
        <button
          onClick={() => send(input, { propose: fileActions, explain, remember })}
          disabled={busy || !input.trim()}
          className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:bg-neutral-700 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          {busy ? (
            <span className="text-sm">...</span>
          ) : (
            <>
              <Send className="w-4 h-4" />
              <span className="text-sm font-medium">Send</span>
            </>
          )}
        </button>

        {/* Action Controls */}
        <label className="flex items-center gap-2 text-xs text-neutral-400 cursor-pointer px-2 py-1 rounded-xl bg-neutral-900 border border-neutral-800">
          <input
            type="checkbox"
            checked={fileActions}
            onChange={(e) => setFileActions(e.target.checked)}
            className="rounded border-neutral-700 text-emerald-600 focus:ring-emerald-500/50"
          />
          file actions to Approvals
        </label>
        <label className="flex items-center gap-2 text-xs text-neutral-400 cursor-pointer px-2 py-1 rounded-xl bg-neutral-900 border border-neutral-800">
          <input
            type="checkbox"
            checked={explain}
            onChange={(e) => setExplain(e.target.checked)}
            className="rounded border-neutral-700 text-emerald-600 focus:ring-emerald-500/50"
          />
          explain my intent
        </label>
        <label className="flex items-center gap-2 text-xs text-neutral-400 cursor-pointer px-2 py-1 rounded-xl bg-neutral-900 border border-neutral-800">
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
            className="rounded border-neutral-700 text-emerald-600 focus:ring-emerald-500/50"
          />
          remember exceptions
        </label>
        
        {/* Mode Selector */}
        <label className="text-xs flex items-center gap-2 px-2 py-1 rounded-xl bg-neutral-900 border border-neutral-800">
          <span className="opacity-70">mode</span>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as '' | 'networking' | 'money')}
            className="bg-neutral-900 text-xs border border-neutral-800 rounded px-2 py-1"
            aria-label="assistant mode"
          >
            <option value="">off</option>
            <option value="networking">networking</option>
            <option value="money">money</option>
          </select>
        </label>
        
        {/* Money Mode: Export Receipts Link */}
        {mode === 'money' && (
          <a
            href="/api/money/receipts.csv"
            className="px-3 py-1 rounded-xl bg-neutral-800 text-xs underline"
            target="_blank"
            rel="noreferrer"
          >
            Export receipts (CSV)
          </a>
        )}
        
        <button
          onClick={() => lastQuery && send(lastQuery, { propose: true })}
          disabled={busy || !lastQuery}
          className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-700 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          title="Replay last query with actions filed to the Approvals tray"
        >
          <Play className="w-4 h-4" />
          <span className="text-sm font-medium">Run actions now</span>
        </button>
      </div>

      {/* Intent Tokens (if explain is enabled and tokens exist) */}
      {intentTokens.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="text-xs text-neutral-400 underline cursor-pointer">
            Intent tokens ({intentTokens.length})
          </summary>
          <div className="mt-2 flex flex-wrap gap-2">
            {intentTokens.map((token: string, idx: number) => (
              <span
                key={`${token}-${idx}`}
                className="px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 text-xs"
              >
                {token}
              </span>
            ))}
          </div>
        </details>
      )}

      {/* Tips */}
      <div className="text-xs text-neutral-500 text-center">
        💡 Try asking about specific time ranges, senders, or categories. The
        assistant will cite source emails.
      </div>
        </div>

        {/* Right Sidebar - Policy Accuracy Panel */}
        <div className="lg:col-span-1 space-y-3">
          <PolicyAccuracyPanel />
          
          {/* Money Tools Panel */}
          <div className="rounded-2xl border border-neutral-800 p-3 bg-neutral-900">
            <div className="text-sm font-semibold mb-2">Money tools</div>
            <div className="flex gap-2">
              <button 
                className="px-3 py-1 rounded-xl bg-neutral-800 text-xs hover:bg-neutral-700" 
                onClick={loadDupes}
              >
                View duplicates
              </button>
              <button 
                className="px-3 py-1 rounded-xl bg-neutral-800 text-xs hover:bg-neutral-700" 
                onClick={loadSummary}
              >
                Spending summary
              </button>
            </div>
            {dupes && (
              <pre className="mt-2 text-[11px] overflow-auto max-h-40 bg-neutral-950 p-2 rounded border border-neutral-800">
                {JSON.stringify(dupes, null, 2)}
              </pre>
            )}
            {summary && (
              <pre className="mt-2 text-[11px] overflow-auto max-h-40 bg-neutral-950 p-2 rounded border border-neutral-800">
                {JSON.stringify(summary, null, 2)}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
