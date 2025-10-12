import { useEffect, useRef, useState, useMemo } from 'react'
import { searchEmails, unifiedSuggest, SearchHit } from '../lib/api'
import SearchResultsHeader from '../components/SearchResultsHeader'
import EmailLabels from '../components/EmailLabels'
import { LabelFilterChips } from '../components/LabelFilterChips'
import { DateRangeControls } from '../components/DateRangeControls'
import { RepliedFilterChips } from '../components/RepliedFilterChips'
import { SortControl, SortKey } from '../components/SortControl'
import { getRecencyScale } from '../state/searchPrefs'
import { loadUiState, saveUiState, RepliedFilter } from '../state/searchUi'
import { safeFormatDate } from '../lib/date'

function allowOnlyMark(html: string) {
  // strips all tags except <mark>…</mark>
  return html
    .replace(/<(?!(\/?mark\b))[^>]*>/gi, '') // drop any non-<mark> tags
    .replace(/ on\w+="[^"]*"/gi, '');        // drop inline event handlers if any
}

export default function Search() {
  const [q, setQ] = useState('Interview')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [sugs, setSugs] = useState<string[]>([])
  const [dym, setDym] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [total, setTotal] = useState<number | undefined>(undefined)
  
  // Initialize from localStorage (sticky)
  const init = useMemo(() => loadUiState(), [])
  const [labels, setLabels] = useState<string[]>(init.labels || [])
  const [dates, setDates] = useState<{ from?: string; to?: string }>({
    from: init.date_from,
    to: init.date_to,
  })
  const [replied, setReplied] = useState<RepliedFilter>(init.replied)
  const [sort, setSort] = useState<SortKey>(init.sort as SortKey)
  const t = useRef<number | null>(null)

  async function onSearch(e?: React.FormEvent) {
    e?.preventDefault()
    if (!q.trim()) return
    setLoading(true)
    setErr(null)
    setSugs([]) // Clear suggestions when searching
    try {
      const scale = getRecencyScale()
      const repliedParam = replied === "all" ? undefined : replied === "true"
      const res = await searchEmails(q, 20, undefined, scale, labels, dates.from, dates.to, repliedParam, sort)
      setHits(res)
      setTotal(res.length) // Note: API should return total count
    } catch (e:any) {
      setErr(String(e.message || e))
    } finally {
      setLoading(false)
    }
  }

  function onChange(v: string) {
    setQ(v)
    if (t.current) window.clearTimeout(t.current)
    t.current = window.setTimeout(async () => {
      if (!v.trim()) { setSugs([]); setDym([]); return }
      try {
        const res = await unifiedSuggest(v, 8)
        setSugs(res.suggestions.concat(res.body_prefix).filter(Boolean).slice(0, 8))
        setDym(res.did_you_mean)
      } catch { /* ignore */ }
    }, 200)
  }

  useEffect(() => { onSearch() }, [])
  
  // Re-run search when filters change
  useEffect(() => {
    if (q.trim()) onSearch()
  }, [labels, dates, replied, sort])

  // Persist to localStorage whenever user changes filters/sort
  useEffect(() => {
    saveUiState({
      labels,
      date_from: dates.from,
      date_to: dates.to,
      replied,
      sort,
    })
  }, [labels, dates.from, dates.to, replied, sort])

  // Keep the URL shareable by reflecting current params (without page reload)
  useEffect(() => {
    if (!q) return
    const params = new URLSearchParams()
    params.set('q', q)
    params.set('scale', getRecencyScale())
    labels.forEach(l => params.append('labels', l))
    if (dates.from) params.set('date_from', dates.from)
    if (dates.to) params.set('date_to', dates.to)
    if (replied !== 'all') params.set('replied', replied)
    params.set('sort', sort)
    const url = `/search?${params.toString()}`
    window.history.replaceState(null, '', url)
  }, [q, labels, dates.from, dates.to, replied, sort])

  return (
    <div>
      <style>{`
        mark {
          background-color: #ffeb3b;
          color: #000;
          padding: 2px 4px;
          border-radius: 3px;
          font-weight: 500;
        }
      `}</style>
      <form onSubmit={onSearch} style={{ display: 'flex', gap: 8, marginBottom: 12, position: 'relative' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <input
            value={q}
            onChange={e => onChange(e.target.value)}
            placeholder="Search subject and body…"
            style={{ width: '100%', padding: '10px 12px', border: '1px solid #ccc', borderRadius: 8 }}
          />
          {sugs.length > 0 && (
            <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, background: '#fff', border: '1px solid #ddd', borderTop: 'none', zIndex: 10, borderRadius: '0 0 8px 8px', maxHeight: '300px', overflowY: 'auto' }}>
              {sugs.map((s, i) => (
                <div key={i} style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: i < sugs.length - 1 ? '1px solid #eee' : 'none' }} onMouseDown={() => { setQ(s); setSugs([]); setTimeout(() => onSearch(), 0) }}>
                  {s}
                </div>
              ))}
            </div>
          )}
        </div>
        <button type="submit" style={{ padding: '10px 14px', borderRadius: 8, border: '1px solid #111', background: '#111', color: '#fff' }}>
          Search
        </button>
      </form>

      {dym.length > 0 && (
        <div style={{ marginBottom: 12, fontSize: 14, color: '#555' }}>
          Did you mean: {dym.map((d, i) => (
            <button key={i} onClick={() => { setQ(d); setDym([]); setTimeout(() => onSearch(), 0) }} style={{ background: 'transparent', border: 'none', color: '#0a58ca', cursor: 'pointer', padding: 0, marginRight: 8, textDecoration: 'underline' }}>
              {d}
            </button>
          ))}
        </div>
      )}

      <div style={{ marginBottom: 16, padding: 12, background: '#f8f9fa', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 6, color: '#555' }}>Filter by label:</div>
          <LabelFilterChips value={labels} onChange={setLabels} />
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 6, color: '#555' }}>Filter by date:</div>
          <DateRangeControls from={dates.from} to={dates.to} onChange={setDates} />
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 6, color: '#555' }}>Filter by reply status:</div>
          <RepliedFilterChips value={replied} onChange={setReplied} />
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 6, color: '#555' }}>Sort results:</div>
          <SortControl value={sort} onChange={setSort} />
        </div>
        {(labels.length > 0 || dates.from || dates.to || replied !== 'all' || sort !== 'relevance') && (
          <div style={{ textAlign: 'right' }}>
            <button
              onClick={() => {
                setLabels([])
                setDates({})
                setReplied('all')
                setSort('relevance')
              }}
              style={{
                fontSize: 12,
                color: '#6c757d',
                textDecoration: 'underline',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                padding: 0,
              }}
            >
              Clear all filters
            </button>
          </div>
        )}
      </div>

      {loading && <div>Searching…</div>}
      {err && <div style={{ color: 'crimson' }}>Error: {err}</div>}
      {!loading && !err && hits.length === 0 && <div>Try a query like <code>Interview</code> or start typing to see suggestions.</div>}

      {!loading && !err && hits.length > 0 && (
        <SearchResultsHeader query={q} total={total} showHint />
      )}

      <div>
        {hits.map(h => {
          // Format time-to-response as a compact badge if present
          const ttrH: number | null = typeof h.time_to_response_hours === 'number' ? h.time_to_response_hours : null
          const ttrText = ttrH == null
            ? (h.replied ? 'Replied' : 'No reply')
            : (ttrH < 1
                ? `${Math.round(ttrH * 60)}m`
                : ttrH < 24
                ? `${Math.round(ttrH)}h`
                : `${Math.round(ttrH / 24)}d`)
          
          return (
            <div key={h.id} style={{ border: '1px solid #ddd', borderRadius: 12, padding: 12, marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'start' }}>
                <div style={{ flex: 1 }}>
                  <strong>{h.subject || '(no subject)'}</strong>
                  <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>
                    {h.sender || h.from_addr} · {safeFormatDate(h.received_at) ?? '—'}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'row', gap: 8, alignItems: 'center' }}>
                  <span style={{ opacity: 0.6, fontSize: 11 }}>score: {h.score?.toFixed?.(2)}</span>
                  <EmailLabels labels={h.label_heuristics || (h.label ? [h.label] : [])} />
                  <span
                    title={h.first_user_reply_at ? `Replied ${ttrText} after receipt` : (h.replied ? 'Replied' : 'No reply yet')}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      borderRadius: 9999,
                      padding: '2px 8px',
                      fontSize: 10,
                      fontWeight: 500,
                      border: '1px solid',
                      ...(h.replied
                        ? { backgroundColor: '#dbeafe', borderColor: '#93c5fd' }
                        : { backgroundColor: '#f3f4f6', borderColor: '#d1d5db', opacity: 0.8 })
                    }}
                  >
                    {h.replied ? `TTR ${ttrText}` : 'No reply'}
                  </span>
                </div>
              </div>
              {h.highlight?.body_text && (
                <div
                  style={{ marginTop: 6, fontSize: 14 }}
                  dangerouslySetInnerHTML={{ __html: allowOnlyMark(h.highlight.body_text.join(' … ')) }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
