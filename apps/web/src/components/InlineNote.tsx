import { useEffect, useRef, useState } from 'react'

export default function InlineNote({
  value,
  onSave,
  updatedAt,
  maxPreviewChars = 80,
  placeholder = 'Add a quick note…',
  testId,
  snippets = [
    'Sent thank-you',
    'Follow-up scheduled',
    'Left voicemail',
    'Recruiter screen scheduled',
    'Sent take-home',
    'Referred by X',
    'Declined offer',
  ],
}: {
  value: string | null | undefined
  onSave: (next: string) => Promise<void> | void
  updatedAt?: string | null
  maxPreviewChars?: number
  placeholder?: string
  testId?: string
  snippets?: string[]
}) {
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(value || '')
  const [saving, setSaving] = useState(false)
  const taRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (editing) taRef.current?.focus()
  }, [editing])

  useEffect(() => {
    // if external value changes (reload), sync when not editing
    if (!editing) setText(value || '')
  }, [value, editing])

  function preview(v: string) {
    const s = v?.trim() || ''
    if (!s) return '—'
    if (s.length <= maxPreviewChars) return s
    return s.slice(0, maxPreviewChars - 1) + '…'
  }

  async function commit() {
    const next = text.trim()
    if ((value || '') === next) {
      setEditing(false)
      return
    }
    try {
      setSaving(true)
      await onSave(next)
    } finally {
      setSaving(false)
      setEditing(false)
    }
  }

  function insertSnippet(snippet: string) {
    const current = (text ?? '').trim()
    if (!current) {
      setText(snippet)
    } else {
      // Split to lines and dedupe exact matches
      const lines = current.split(/\r?\n/)
      const alreadyPresent = lines.some((l) => l.trim() === snippet.trim())
      let next = current
      if (!alreadyPresent) {
        next = `${current}\n${snippet}`
      } else {
        // If duplicate, do nothing (but still focus the editor)
        next = current
      }
      setText(next)
    }
    // Focus for immediate further typing / cursor to end
    requestAnimationFrame(() => {
      const el = taRef.current
      if (!el) return
      el.focus()
      const len = el.value?.length ?? 0
      try {
        el.setSelectionRange(len, len)
      } catch {
        /* noop */
      }
    })
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    const isCmdEnter = (e.metaKey || e.ctrlKey) && e.key === 'Enter'
    if (isCmdEnter) {
      e.preventDefault()
      void commit()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setText(value || '')
      setEditing(false)
    }
  }

  const stamp = updatedAt ? new Date(updatedAt).toLocaleString() : null

  if (!editing) {
    return (
      <div className="group max-w-full">
        <button
          type="button"
          className="text-left w-full px-2 py-1 border rounded hover:bg-white transition"
          onClick={() => setEditing(true)}
          data-testid={testId ? `${testId}-preview` : undefined}
          title={value || ''}
        >
          <div className="truncate text-sm">{preview(text)}</div>
          {stamp && <div className="text-[11px] opacity-60 mt-0.5">Last updated: {stamp}</div>}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <textarea
        ref={taRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={() => void commit()}
        placeholder={placeholder}
        className="w-full min-h-[64px] border rounded p-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
        data-testid={testId ? `${testId}-editor` : undefined}
        disabled={saving}
      />
      {/* Snippet chips */}
      {snippets?.length ? (
        <div className="flex flex-wrap gap-2">
          {snippets.map((s) => (
            <button
              key={s}
              type="button"
              className="px-2 py-0.5 text-xs border rounded hover:bg-white"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => insertSnippet(s)}
              data-testid={testId ? `${testId}-chip-${s.replace(/\s+/g, '-').toLowerCase()}` : undefined}
            >
              {s}
            </button>
          ))}
        </div>
      ) : null}
      <div className="flex items-center justify-between">
        <div className="text-[11px] opacity-70">
          {saving ? 'Saving…' : 'Ctrl/Cmd+Enter to save · Esc to cancel'}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="px-2 py-1 text-xs border rounded hover:bg-white transition"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => {
              setText(value || '')
              setEditing(false)
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            className="px-2 py-1 text-xs border rounded bg-black text-white hover:opacity-90 disabled:opacity-50 transition"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => void commit()}
            disabled={saving}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  )
}
