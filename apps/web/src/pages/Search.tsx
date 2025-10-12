import { useEffect, useRef, useState, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { searchEmails, unifiedSuggest, SearchHit } from '../lib/api'
import SearchResultsHeader from '../components/SearchResultsHeader'
import EmailLabels from '../components/EmailLabels'
import { SearchFilters } from '../components/SearchFilters'
import { SearchControls } from '../components/search/SearchControls'
import { SortKey } from '../components/SortControl'
import { getRecencyScale } from '../state/searchPrefs'
import { loadUiState, saveUiState, RepliedFilter } from '../state/searchUi'
import { safeFormatDate } from '../lib/date'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { formatDistanceToNowStrict, format } from 'date-fns'
import { toMarkedHTML } from '@/lib/highlight'

export default function Search() {
  const [searchParams] = useSearchParams()
  const [q, setQ] = useState('Interview')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [sugs, setSugs] = useState<string[]>([])
  const [dym, setDym] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [total, setTotal] = useState<number | undefined>(undefined)
  
  // Parse ML filter params from URL
  const categories = useMemo(() => 
    (searchParams.get("cat") ?? "").split(",").filter(Boolean), 
    [searchParams]
  )
  const hideExpired = searchParams.get("hideExpired") !== "0"
  
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
      const res = await searchEmails(
        q, 
        20, 
        undefined, 
        scale, 
        labels, 
        dates.from, 
        dates.to, 
        repliedParam, 
        sort,
        categories,
        hideExpired
      )
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
  
  // Re-run search when filters change (including ML filters)
  useEffect(() => {
    if (q.trim()) onSearch()
  }, [labels, dates, replied, sort, categories, hideExpired])

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
      <form onSubmit={onSearch} className="flex gap-2 mb-3 relative">
        <div className="relative flex-1">
          <Input
            value={q}
            onChange={e => onChange(e.target.value)}
            placeholder="Search subject and body…"
            className="w-full"
          />
          {sugs.length > 0 && (
            <div className="absolute top-full left-0 right-0 bg-card border border-border rounded-b-lg z-10 max-h-[300px] overflow-y-auto shadow-lg">
              {sugs.map((s: string, i: number) => (
                <div 
                  key={`sug-${i}-${s}`} 
                  className="px-3 py-2 cursor-pointer hover:bg-secondary border-b last:border-b-0 border-border" 
                  onMouseDown={() => { setQ(s); setSugs([]); setTimeout(() => onSearch(), 0) }}
                >
                  {s}
                </div>
              ))}
            </div>
          )}
        </div>
        <Button type="submit">Search</Button>
      </form>

      {dym.length > 0 && (
        <div className="mb-3 text-sm text-muted-foreground">
          Did you mean: {dym.map((d: string, i: number) => (
            <Button
              key={`dym-${i}-${d}`}
              variant="link"
              size="sm"
              className="h-auto p-0 mr-2"
              onClick={() => { setQ(d); setDym([]); setTimeout(() => onSearch(), 0) }}
            >
              {d}
            </Button>
          ))}
        </div>
      )}

      {/* ML-powered category filters & hide expired toggle */}
      <SearchControls />

      <SearchFilters
        labels={labels}
        onLabelsChange={setLabels}
        dates={dates}
        onDatesChange={setDates}
        replied={replied}
        onRepliedChange={setReplied}
        sort={sort}
        onSortChange={setSort}
      />

      {loading && <div>Searching…</div>}
      {err && <div style={{ color: 'crimson' }}>Error: {err}</div>}
      {!loading && !err && hits.length === 0 && <div>Try a query like <code>Interview</code> or start typing to see suggestions.</div>}

      {!loading && !err && hits.length > 0 && (
        <SearchResultsHeader query={q} total={total} showHint />
      )}

      <div>
        {hits.map((h: any, i: number) => {
          // Ensure unique key even when id is missing/null
          const rawId = h?.id ?? h?._id ?? h?._source?.id ?? null;
          const safeKey = rawId ? `search-${String(rawId)}` : `row-${i}`;
          
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
            <div 
              key={safeKey} 
              data-testid="search-result-item"
              data-id={rawId || `fallback-${i}`}
              className="surface-card density-x density-y mb-3 transition-all hover:shadow-lg"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <h3 
                    data-testid="subject"
                    className="font-semibold leading-snug text-[color:hsl(var(--foreground))]"
                    dangerouslySetInnerHTML={toMarkedHTML(h.subject_highlight ?? h.subject ?? '(no subject)')}
                  />
                  <div className="mt-1 text-xs text-[color:hsl(var(--muted-foreground))]">
                    {h.sender || h.from_addr} · {safeFormatDate(h.received_at) ?? '—'}
                  </div>
                </div>
                <div className="flex shrink-0 flex-row items-center gap-2">
                  <span className="text-[11px] text-[color:hsl(var(--muted-foreground))]">
                    score: {h.score?.toFixed?.(2)}
                  </span>
                  <EmailLabels labels={h.label_heuristics || (h.label ? [h.label] : [])} />
                  
                  {/* ML Category Badge (Phase 35) */}
                  {h.category && (
                    <Badge data-testid="badge-category" variant="secondary" className="text-[10px] capitalize h-5">
                      {h.category}
                    </Badge>
                  )}
                  
                  {/* Expiry Badge (Phase 35) */}
                  {h.expires_at && (
                    <Badge data-testid="badge-expires" className="bg-amber-100 text-amber-900 border-amber-300 text-[10px] h-5">
                      ⏰ {formatDistanceToNowStrict(new Date(h.expires_at), { addSuffix: true })}
                    </Badge>
                  )}
                  
                  {/* Event Badge (Phase 35) */}
                  {h.event_start_at && (
                    <Badge data-testid="badge-event" className="bg-sky-100 text-sky-900 border-sky-300 text-[10px] h-5">
                      📅 {format(new Date(h.event_start_at), "MMM d")}
                    </Badge>
                  )}
                  
                  <span
                    title={h.first_user_reply_at ? `Replied ${ttrText} after receipt` : (h.replied ? 'Replied' : 'No reply yet')}
                    className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                      h.replied
                        ? 'border-blue-300 bg-blue-100 text-blue-800 dark:border-blue-700 dark:bg-blue-900/40 dark:text-blue-200'
                        : 'border-gray-300 bg-gray-100 text-gray-700 opacity-80 dark:border-gray-700 dark:bg-gray-800/40 dark:text-gray-300'
                    }`}
                  >
                    {h.replied ? `TTR ${ttrText}` : 'No reply'}
                  </span>
                </div>
              </div>
              {h.body_highlight && (
                <div
                  data-testid="snippet"
                  className="mt-2 text-sm text-[color:hsl(var(--muted-foreground))]"
                  dangerouslySetInnerHTML={toMarkedHTML(h.body_highlight)}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
