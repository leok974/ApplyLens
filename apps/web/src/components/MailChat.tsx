/**
 * MailChat - Conversational mailbox assistant
 *
 * Features:
 * - Quick-action chips for common queries
 * - Message history with user/assistant roles
 * - Citations from source emails
 * - Loading states and error handling
 */

import { useState, useEffect, useRef } from 'react'
import { Send, Sparkles, AlertCircle, Mail, Play } from 'lucide-react'
import { sendChatMessage, Message, ChatResponse } from '@/lib/chatClient'
import PolicyAccuracyPanel from '@/components/PolicyAccuracyPanel'
import { sync7d, sync60d } from '@/lib/api'
import { useNavigate } from 'react-router-dom'

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
  const navigate = useNavigate()
  const [userEmail] = useState('leoklemet.pa@gmail.com') // TODO: Read from auth context

  // Time window with localStorage persistence
  const [windowDays, setWindowDays] = useState<number>(() => {
    const v = Number(localStorage.getItem('chat:windowDays') || '30')
    return [7, 30, 60, 90].includes(v) ? v : 30
  })

  const [messages, setMessages] = useState<ConversationMessage[]>([
    {
      role: 'assistant',
      content:
        'Hi! 👋 Ask me about your mailbox. I can summarize, find, clean, unsubscribe, flag suspicious emails, suggest follow-ups, and create calendar events or tasks.',
    },
  ])
  const [input, setInput] = useState('')
  const [lastQuery, setLastQuery] = useState<string>('*')
  const [fileActions, setFileActions] = useState(false)
  const [explain, setExplain] = useState(false)
  const [remember, setRemember] = useState(false)
  const [mode, setMode] = useState<'' | 'networking' | 'money'>('')
  const [intentTokens, setIntentTokens] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dupes, setDupes] = useState<any[] | null>(null)
  const [summary, setSummary] = useState<any | null>(null)
  const [timing, setTiming] = useState<{es_ms?: number; llm_ms?: number; client_ms?: number}>({})
  const [isStreamAlive, setIsStreamAlive] = useState(false)
  const streamHeartbeatRef = useRef<number | null>(null)
  const currentEventSourceRef = useRef<EventSource | null>(null)
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

  // Keyboard shortcuts
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Ctrl/Cmd+R to re-run last query
      if (e.key.toLowerCase() === 'r' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        if (lastQuery) {
          send(lastQuery, { propose: fileActions, explain, remember })
        }
      }
      // 1/2/3/4 to quickly set days (7/30/60/90)
      if (!e.ctrlKey && !e.metaKey && !e.altKey) {
        if (e.key === '1') changeWindowDays(7)
        if (e.key === '2') changeWindowDays(30)
        if (e.key === '3') changeWindowDays(60)
        if (e.key === '4') changeWindowDays(90)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lastQuery, windowDays, fileActions, explain, remember])

  // Cleanup on unmount - abort any active streams
  useEffect(() => {
    return () => {
      if (currentEventSourceRef.current) {
        currentEventSourceRef.current.close()
        clearStreamHeartbeat()
      }
    }
  }, [])

  // UX Heartbeat - track active sessions (30s interval)
  useEffect(() => {
    const sendHeartbeat = async () => {
      try {
        await fetch('/api/ux/heartbeat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            page: '/chat',
            ts: Date.now() / 1000,
          }),
        })
      } catch (err) {
        // Silently fail - this is just telemetry
        console.debug('[Heartbeat] Failed:', err)
      }
    }

    // Send initial heartbeat when chat opens
    sendHeartbeat()
    fetch('/api/ux/chat/opened', { method: 'POST' }).catch(() => {})

    // Send heartbeat every 30s while component is mounted
    const interval = setInterval(sendHeartbeat, 30000)

    return () => {
      clearInterval(interval)
    }
  }, [])

  async function handleSync(days: number) {
    setBusy(true)
    try {
      if (days === 7) {
        await sync7d()
      } else if (days === 60) {
        await sync60d()
      }
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: `✅ Synced ${days} days of emails. Try your search again!`,
        },
      ])
    } catch (err) {
      console.error('Sync failed:', err)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: `❌ Sync failed: ${err}`,
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  function openSearchPrefilled() {
    const q = lastQuery?.trim() || '*'
    navigate(`/search?q=${encodeURIComponent(q)}&window=${windowDays}`)
  }

  function changeWindowDays(days: number) {
    setWindowDays(days)
    localStorage.setItem('chat:windowDays', String(days))
    // Re-run last query with new window
    if (lastQuery) {
      send(lastQuery, { propose: fileActions, explain, remember })
    }
  }

  // Heartbeat management for connection status
  function resetStreamHeartbeat() {
    setIsStreamAlive(true)

    // Clear existing timeout
    if (streamHeartbeatRef.current) {
      window.clearTimeout(streamHeartbeatRef.current)
    }

    // Set new timeout - mark as dead after 35s of silence
    streamHeartbeatRef.current = window.setTimeout(() => {
      setIsStreamAlive(false)
    }, 35000)
  }

  function clearStreamHeartbeat() {
    setIsStreamAlive(false)
    if (streamHeartbeatRef.current) {
      window.clearTimeout(streamHeartbeatRef.current)
      streamHeartbeatRef.current = null
    }
  }

  async function send(text: string, opts?: { propose?: boolean; explain?: boolean; remember?: boolean }) {
    if (!text.trim() || busy) return

    setLastQuery(text)
    setError(null)
    setTiming({}) // Reset timing
    const t0 = performance.now()
    setIntentTokens([]) // Reset tokens for new query
    const userMessage: ConversationMessage = { role: 'user', content: text }
    setMessages((m) => [...m, userMessage])
    setInput('')
    setBusy(true)

    // Abort any existing stream
    if (currentEventSourceRef.current) {
      console.log('[Chat] Aborting previous stream')
      currentEventSourceRef.current.close()
      clearStreamHeartbeat()
    }

    // Use streaming SSE for real-time updates
    const shouldPropose = opts?.propose ?? false
    const shouldExplain = opts?.explain ?? false
    const shouldRemember = opts?.remember ?? false
    const url = `/api/chat/stream?q=${encodeURIComponent(text)}`
      + (shouldPropose ? '&propose=1' : '')
      + (shouldExplain ? '&explain=1' : '')
      + (shouldRemember ? '&remember=1' : '')
      + (mode ? `&mode=${encodeURIComponent(mode)}` : '')
      + `&window_days=${windowDays}` // Add window_days parameter

    let assistantText = ''
    let filedCount = 0

    try {
      const ev = new EventSource(url)
      currentEventSourceRef.current = ev // Store reference for cleanup

      // Reset heartbeat on connection
      resetStreamHeartbeat()

      ev.addEventListener('ready', () => {
        resetStreamHeartbeat()
      })

      ev.addEventListener('intent', (e: any) => {
        resetStreamHeartbeat()
        const data = JSON.parse(e.data)
        console.log('[Chat] Intent detected:', data.intent)
      })

      ev.addEventListener('intent_explain', (e: any) => {
        resetStreamHeartbeat()
        const data = JSON.parse(e.data)
        setIntentTokens(data.tokens || [])
        console.log('[Chat] Intent tokens:', data.tokens)
      })
      ev.addEventListener('memory', (e: any) => {
        resetStreamHeartbeat()
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
        resetStreamHeartbeat()
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
        resetStreamHeartbeat()
        const data = JSON.parse(e.data)
        assistantText = data.answer || data.text || ''
        console.log('[Chat] Answer received:', assistantText.substring(0, 100))
      })

      ev.addEventListener('filed', (e: any) => {
        resetStreamHeartbeat()
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
        clearStreamHeartbeat()
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

          // Capture timing from response
          const t1 = performance.now()
          setTiming({
            es_ms: response?.search_stats?.took_ms ?? response?.timing?.es_ms,
            llm_ms: response?.timing?.llm_ms,
            client_ms: Math.round(t1 - t0),
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
        clearStreamHeartbeat()
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
      clearStreamHeartbeat()

      // Canary fallback: if streaming disabled (503 + header), use non-streaming /chat
      if (err instanceof Response && err.status === 503) {
        const streamingDisabled = err.headers?.get('X-Chat-Streaming-Disabled')
        if (streamingDisabled === '1') {
          console.log('[Chat] Streaming disabled, falling back to non-streaming endpoint')
          try {
            const response = await sendChatMessage({
              messages: [...messages, userMessage].map((m) => ({
                role: m.role,
                content: m.content,
              })),
              window_days: windowDays,
            })

            // Build assistant message from response
            let finalText = response.answer || 'Response received.'

            if (response.intent !== 'summarize' && response.intent_explanation) {
              finalText = `*${response.intent_explanation}*\n\n${finalText}`
            }

            if (response.actions.length > 0) {
              finalText += `\n\n**${response.actions.length} action${response.actions.length === 1 ? '' : 's'} proposed**`
            }

            if (response.citations.length > 0) {
              finalText += '\n\n**Sources:**'
              response.citations.slice(0, 5).forEach((c) => {
                const date = c.received_at ? new Date(c.received_at).toLocaleDateString() : ''
                finalText += `\n• ${c.subject} — ${c.sender || '?'} ${date ? `(${date})` : ''}`
              })
              if (response.citations.length > 5) {
                finalText += `\n• ... and ${response.citations.length - 5} more`
              }
            }

            setMessages((m) => [
              ...m,
              {
                role: 'assistant',
                content: finalText,
                response,
              },
            ])

            // Capture timing
            const t1 = performance.now()
            setTiming({
              es_ms: response?.search_stats?.took_ms ?? response?.timing?.es_ms,
              llm_ms: response?.timing?.llm_ms,
              client_ms: Math.round(t1 - t0),
            })

            setBusy(false)
            return
          } catch (fallbackErr: any) {
            console.error('[Chat] Fallback to non-streaming also failed:', fallbackErr)
            setError(fallbackErr?.message || 'Failed to get response')
            setBusy(false)
            return
          }
        }
      }

      // Handle rate limit errors
      if (err instanceof Response && err.status === 429) {
        setError("You're sending requests a bit too fast. Please wait a moment and try again.")
        setBusy(false)
        return
      }

      // Handle other errors
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

      {/* Scope Indicator with Time Window Dropdown */}
      <div className="mb-3 text-xs text-neutral-400 flex flex-wrap items-center gap-3 justify-between">
        <span>
          Searching as <span className="text-neutral-200 font-medium">{userEmail}</span>
        </span>

        <div className="flex items-center gap-2">
          <span>Time window:</span>
          <select
            className="bg-neutral-900 border border-neutral-800/80 rounded-md px-2 py-1 text-neutral-200
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-600"
            value={windowDays}
            onChange={(e) => changeWindowDays(Number(e.target.value))}
            aria-label="Time window (days)"
          >
            <option value={7}>7d</option>
            <option value={30}>30d</option>
            <option value={60}>60d</option>
            <option value={90}>90d</option>
          </select>

          <button
            className="ml-2 px-3 py-1.5 rounded-md bg-neutral-900 border border-neutral-800/80
                       hover:bg-neutral-800 transition-colors
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-600"
            onClick={openSearchPrefilled}
            title="Open Search with the same query and window"
          >
            Open Search
          </button>
        </div>
      </div>

      {/* Loading State */}
      {busy && (
        <div className="text-sm text-neutral-500 my-2">🔄 Searching mailbox …</div>
      )}

      {/* Error Alert - Enhanced with friendly messaging */}
      {error && (
        <div className="mt-2 rounded-md border border-amber-600/40 bg-amber-900/20 p-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-amber-300 mt-0.5 flex-shrink-0" />
            <div>
              <div className="font-medium text-sm text-amber-300">Connection hiccup</div>
              <div className="text-sm text-amber-200/80 mt-1">{error}</div>
            </div>
          </div>
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

              {/* Timing Footer */}
              {msg.role === 'assistant' && i === messages.length - 1 && (timing.es_ms || timing.llm_ms || timing.client_ms) && (
                <div className="mt-2 flex items-center gap-2 text-[11px] text-neutral-500">
                  <span
                    className={`inline-block h-2 w-2 rounded-full ${
                      isStreamAlive ? 'bg-green-500' : 'bg-neutral-600'
                    }`}
                    title={isStreamAlive ? 'Connected' : 'Disconnected'}
                  />
                  {typeof timing.es_ms === 'number' && <span>ES: {Math.round(timing.es_ms)} ms</span>}
                  {typeof timing.llm_ms === 'number' && <span>{' · '}LLM: {Math.round(timing.llm_ms)} ms</span>}
                  {typeof timing.client_ms === 'number' && <span>{' · '}Client: {Math.round(timing.client_ms)} ms</span>}
                </div>
              )}

              {/* Empty State - Show sync buttons when no results */}
              {msg.response && msg.response.search_stats.returned_results === 0 && (
                <div className="rounded-xl bg-neutral-900 p-4 border border-neutral-800 mt-3">
                  <div className="text-sm">
                    🕵️ No emails found in the last {windowDays} days for <b>{userEmail}</b>.
                  </div>
                  <div className="mt-3 flex gap-2">
                    <button
                      className="px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 transition-colors"
                      onClick={() => handleSync(7)}
                    >
                      Sync 7 days
                    </button>
                    <button
                      className="px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 transition-colors"
                      onClick={() => handleSync(60)}
                    >
                      Sync 60 days
                    </button>
                    <button
                      className="px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 transition-colors"
                      onClick={openSearchPrefilled}
                    >
                      Open Search
                    </button>
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
            {dupes === null && summary === null && (
              <div className="text-sm text-neutral-500 mt-2">
                No data yet — try "Sync 60 days."
              </div>
            )}
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
