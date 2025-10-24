import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getSuggestions } from '../lib/api'
import SearchResultsHeader from '../components/SearchResultsHeader'
import EmailLabels from '../components/EmailLabels'
import { SearchFilters } from '../components/SearchFilters'
import { SecurityFilterControls } from '../components/search/SecurityFilterControls'
import { SortKey } from '../components/SortControl'
import { loadUiState, saveUiState } from '../state/searchUi'
import { safeFormatDate } from '../lib/date'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { formatDistanceToNowStrict, format } from 'date-fns'
import { toMarkedHTML } from '@/lib/highlight'
import { useSearchModel } from '../hooks/useSearchModel'
import { mapHit } from '@/lib/searchMap'
import { Loader2 } from 'lucide-react'

// Default filter values to reset to
const DEFAULT_FILTERS = {
  scale: '60d',
  hideExpired: false,
  quarantinedOnly: false,
  riskMin: undefined,
  labels: [],
  categories: { ats: false, bills: false, banks: false, events: false, promotions: false },
  replied: 'all' as const,
  limit: 50,
}

export default function Search() {
  const [searchParams] = useSearchParams()
  const [sugs, setSugs] = useState<string[]>([])
  const [dym, setDym] = useState<string[]>([])
  const [hasSearched, setHasSearched] = useState(false)
  const suggestionTimer = useRef<number | null>(null)
  const suggestionAbortController = useRef<AbortController | null>(null)
  const hydratedRef = useRef(false)

  // Initialize from URL and localStorage
  const initialState = useMemo(() => {
    const urlQuery = searchParams.get('q') || ''
    const urlWindow = searchParams.get('window')
    const init = loadUiState()

    // Calculate date range from window if present
    let dateFrom = init.date_from
    let dateTo = init.date_to

    if (urlWindow) {
      const days = Number(urlWindow)
      if ([7, 30, 60, 90].includes(days)) {
        const to = new Date()
        const from = new Date(to)
        from.setDate(from.getDate() - days)
        dateFrom = from.toISOString().split('T')[0]
        dateTo = to.toISOString().split('T')[0]
      }
    }

    // Parse URL params STRICTLY - don't accidentally enable filters
    const categoryList = (searchParams.get("cat") ?? "").split(",").filter(Boolean)
    const categories = categoryList.reduce((acc, cat) => ({ ...acc, [cat]: true }), {} as Record<string, boolean>)

    // Only enable hideExpired if explicitly set to "true"
    const hideExpired = searchParams.get("hideExpired") === "true"

    // Only enable quarantinedOnly if explicitly set to "true"
    const quarantinedOnly = searchParams.get("quarantined") === "true"

    // Only set riskMin if it's a valid number
    const riskMinRaw = searchParams.get("risk_min")
    const riskMin = riskMinRaw !== null ? Number(riskMinRaw) : undefined
    const riskMinValid = typeof riskMin === 'number' && Number.isFinite(riskMin) ? riskMin : undefined

    // Friendlier default for scale
    const scale = searchParams.get("scale") ?? '60d'

    return {
      query: urlQuery || 'Interview',
      filters: {
        labels: init.labels || [],
        dateFrom,
        dateTo,
        replied: init.replied,
        categories,
        scale,
        hideExpired,
        riskMin: riskMinValid,
        quarantinedOnly,
      },
      sort: init.sort as SortKey,
    }
  }, []) // Only run once

  const {
    query,
    setQuery,
    filters,
    setFilters,
    sort,
    setSort,
    loading,
    results,
    error,
    lastStatus,
    total,
    runSearch,
  } = useSearchModel(initialState.query, initialState.filters, initialState.sort)

  // Clear all filters and reset to defaults
  const clearAllFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS)
    runSearch()
  }, [setFilters, runSearch])

  // Handle form submission
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    setSugs([]) // Clear suggestions when searching
    setDym([]) // Clear did-you-mean
    runSearch().then(() => setHasSearched(true))
  }, [runSearch])

  // Handle query input changes with autocomplete
  const handleQueryChange = useCallback((value: string) => {
    setQuery(value)

    // Cancel any pending debounce timer
    if (suggestionTimer.current) {
      window.clearTimeout(suggestionTimer.current)
    }

    // Abort any in-flight suggestion request (drop stale)
    if (suggestionAbortController.current) {
      suggestionAbortController.current.abort()
      suggestionAbortController.current = null
    }

    suggestionTimer.current = window.setTimeout(async () => {
      if (!value.trim()) {
        setSugs([])
        setDym([])
        return
      }

      // Create new AbortController for this request
      const controller = new AbortController()
      suggestionAbortController.current = controller

      try {
        // Use fail-soft getSuggestions - NEVER throws, NEVER blocks results
        const suggestions = await getSuggestions(value, 8)

        // Only update if this request wasn't aborted
        if (!controller.signal.aborted) {
          setSugs(suggestions)
          setDym([])
          suggestionAbortController.current = null
        }
      } catch (err) {
        // Silently ignore aborted requests
        if (!controller.signal.aborted) {
          console.warn('[suggest] request failed:', err)
        }
      }
    }, 180) // 180ms debounce for better UX
  }, [setQuery])

  // Hydrate from URL once on mount
  useEffect(() => {
    if (hydratedRef.current) return
    hydratedRef.current = true

    // Initial state already loaded from URL in useMemo
    // Run first search immediately - don't gate on query existence
    runSearch().then(() => setHasSearched(true))
  }, [])

  // Persist to localStorage whenever user changes filters/sort
  useEffect(() => {
    saveUiState({
      labels: filters.labels,
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      replied: filters.replied,
      sort,
    })
  }, [filters.labels, filters.dateFrom, filters.dateTo, filters.replied, sort])

  // Keep URL in sync with state (after successful search, prevent hydration loop)
  // Omit defaults to avoid stale URL params silently re-applying strict filters
  useEffect(() => {
    if (!hasSearched || loading || error) return

    const params = new URLSearchParams()
    if (query) params.set('q', query)

    if (filters.labels.length > 0) {
      filters.labels.forEach(l => params.append('labels', l))
    }
    if (filters.dateFrom) params.set('date_from', filters.dateFrom)
    if (filters.dateTo) params.set('date_to', filters.dateTo)
    if (filters.replied !== 'all') params.set('replied', filters.replied)
    if (sort !== 'relevance') params.set('sort', sort)

    // Only set scale if it's not the default
    if (filters.scale && filters.scale !== '60d') params.set('scale', filters.scale)

    // Only set hideExpired if true (default is false)
    if (filters.hideExpired) params.set('hideExpired', 'true')

    // Only set quarantinedOnly if true (default is false)
    if (filters.quarantinedOnly) params.set('quarantined', 'true')

    // Only set riskMin if it's a valid number
    if (typeof filters.riskMin === 'number') params.set('risk_min', String(filters.riskMin))

    // Only set categories if any are active
    if (filters.categories && typeof filters.categories === 'object') {
      const cats = Object.entries(filters.categories).filter(([, v]) => v).map(([k]) => k)
      if (cats.length) params.set('cat', cats.join(','))
    }

    const url = `/search?${params.toString()}`
    window.history.replaceState(null, '', url)
  }, [hasSearched, loading, error, query, filters, sort])

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
      <form onSubmit={handleSubmit} data-testid="search-form" className="flex gap-2 mb-3 relative">
        <div className="relative flex-1">
          <Input
            value={query}
            onChange={e => handleQueryChange(e.target.value)}
            placeholder="Search subject and body…"
            className="w-full"
            data-testid="search-input"
          />
          {sugs.length > 0 && (
            <div className="absolute top-full left-0 right-0 bg-card border border-border rounded-b-lg z-10 max-h-[300px] overflow-y-auto shadow-lg">
              {sugs.map((s: string, i: number) => (
                <div
                  key={`sug-${i}-${s}`}
                  className="px-3 py-2 cursor-pointer hover:bg-secondary border-b last:border-b-0 border-border"
                  onMouseDown={() => {
                    setQuery(s)
                    setSugs([])
                    setTimeout(() => runSearch(), 0)
                  }}
                >
                  {s}
                </div>
              ))}
            </div>
          )}
        </div>
        <Button type="submit" data-testid="search-button" disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Search'}
        </Button>
      </form>

      {dym.length > 0 && (
        <div className="mb-3 text-sm text-muted-foreground">
          Did you mean: {dym.map((d: string, i: number) => (
            <Button
              key={`dym-${i}-${d}`}
              type="button"
              variant="link"
              size="sm"
              className="h-auto p-0 mr-2"
              onClick={() => {
                setQuery(d)
                setDym([])
                setTimeout(() => runSearch(), 0)
              }}
            >
              {d}
            </Button>
          ))}
        </div>
      )}

      {/* ML-powered category filters - now controlled */}
      <div className="mb-3">
        <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-3">
          <span className="text-sm font-medium text-muted-foreground">Filter by:</span>
          {(['ats', 'bills', 'banks', 'events', 'promotions'] as const).map((cat) => (
            <Button
              key={cat}
              type="button"
              variant={filters.categories?.[cat] ? "default" : "outline"}
              size="sm"
              onClick={() => {
                setFilters(f => ({
                  ...f,
                  categories: { ...f.categories, [cat]: !f.categories?.[cat] }
                }))
              }}
              className={`capitalize h-8 rounded-full transition ${
                filters.categories?.[cat]
                  ? 'bg-primary/20 border-primary text-primary font-medium'
                  : ''
              }`}
              data-testid={`filter-${cat}`}
            >
              {cat}
            </Button>
          ))}

          <div className="ml-auto flex items-center gap-2">
            <Button
              type="button"
              variant={filters.hideExpired ? "default" : "outline"}
              size="sm"
              onClick={() => setFilters(f => ({ ...f, hideExpired: !f.hideExpired }))}
              className={`rounded-full h-8 transition ${
                filters.hideExpired
                  ? 'bg-primary/20 border-primary text-primary font-medium'
                  : ''
              }`}
              data-testid="filter-hide-expired"
            >
              {filters.hideExpired ? "✓ Hide expired" : "Hide expired"}
            </Button>
          </div>
        </div>

        {/* Active Filters Bar */}
        {(Object.entries(filters.categories || {}).some(([, v]) => v) ||
          filters.hideExpired ||
          filters.quarantinedOnly ||
          (filters.labels && filters.labels.length > 0) ||
          (filters.riskMin !== undefined && filters.riskMin !== null)) && (
          <div className="flex flex-wrap items-center gap-2 mt-2 px-3">
            <span className="text-xs text-muted-foreground">Active filters:</span>

            {Object.entries(filters.categories || {}).filter(([, v]) => v).map(([cat]) => (
              <Badge key={cat} variant="secondary" className="text-xs capitalize">
                {cat}
              </Badge>
            ))}

            {filters.hideExpired && (
              <Badge variant="secondary" className="text-xs">
                Hide expired
              </Badge>
            )}

            {filters.quarantinedOnly && (
              <Badge variant="secondary" className="text-xs">
                Quarantined only
              </Badge>
            )}

            {filters.riskMin !== undefined && filters.riskMin !== null && (
              <Badge variant="secondary" className="text-xs">
                Risk ≥ {filters.riskMin}
              </Badge>
            )}

            {filters.labels && filters.labels.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                Labels: {filters.labels.join(', ')}
              </Badge>
            )}

            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground h-6 px-2"
              onClick={() => setFilters({ ...DEFAULT_FILTERS, scale: filters.scale })}
            >
              Clear all
            </Button>
          </div>
        )}
      </div>

      {/* Security filters - now controlled */}
      <div className="mb-3">
        <SecurityFilterControls
          highRisk={!!filters.riskMin && filters.riskMin >= 80}
          onHighRiskChange={(v) => setFilters(f => ({ ...f, riskMin: v ? 80 : undefined }))}
          quarantinedOnly={filters.quarantinedOnly}
          onQuarantinedOnlyChange={(v) => setFilters(f => ({ ...f, quarantinedOnly: v }))}
        />
      </div>

      <SearchFilters
        labels={filters.labels}
        onLabelsChange={(labels) => setFilters(f => ({ ...f, labels }))}
        dates={{ from: filters.dateFrom, to: filters.dateTo }}
        onDatesChange={({ from, to }) => setFilters(f => ({ ...f, dateFrom: from, dateTo: to }))}
        replied={filters.replied}
        onRepliedChange={(replied) => setFilters(f => ({ ...f, replied }))}
        sort={sort}
        onSortChange={setSort}
      />

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-12" data-testid="search-loading">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">Searching…</span>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Empty state - only show if we've searched and got nothing back */}
      {!loading && !error && hasSearched && results.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-center" data-testid="empty-state">
          <div className="text-6xl mb-4">🔍</div>
          <h3 className="text-lg font-semibold mb-2">No results found</h3>
          <p className="text-muted-foreground mb-4">
            Try different keywords or adjust your filters.
          </p>

          {/* Show helpful message for 422 errors */}
          {lastStatus === 422 && (
            <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
              <strong>Note:</strong> Search requires a query. We sent <code className="px-1 py-0.5 bg-amber-100 dark:bg-amber-900/40 rounded">*</code> (match-all) automatically.
              <br />
              <span className="text-xs opacity-80">If you're seeing this, the search index may be empty. Try syncing data first.</span>
            </div>
          )}

          {/* Show active filters for debugging */}
          <div className="flex flex-wrap gap-2 justify-center text-xs text-muted-foreground mb-4">
            <span>Query: <code className="px-2 py-1 bg-muted rounded">{query || '(match-all)'}</code></span>
            {filters.scale && filters.scale !== '60d' && <Badge variant="outline">Scale: {filters.scale}</Badge>}
            {filters.hideExpired && <Badge variant="outline">Hide expired</Badge>}
            {filters.quarantinedOnly && <Badge variant="outline">Quarantined only</Badge>}
            {typeof filters.riskMin === 'number' && <Badge variant="outline">Risk ≥ {filters.riskMin}</Badge>}
            {filters.labels && filters.labels.length > 0 && <Badge variant="outline">Labels: {filters.labels.join(', ')}</Badge>}
            {filters.categories && Object.entries(filters.categories).filter(([, v]) => v).length > 0 && (
              <Badge variant="outline">
                Categories: {Object.entries(filters.categories).filter(([, v]) => v).map(([k]) => k).join(', ')}
              </Badge>
            )}
          </div>

          <Button
            onClick={clearAllFilters}
            variant="outline"
            size="sm"
            data-testid="clear-filters-button"
          >
            Clear all filters
          </Button>
        </div>
      )}

      {/* Results header */}
      {!loading && !error && results.length > 0 && (
        <SearchResultsHeader query={query} total={total} showHint />
      )}

      {/* Results list - only render when we have results */}
      {!loading && !error && results.length > 0 && (
        <ul data-testid="results-list" className="space-y-3">
          {(Array.isArray(results) ? results : []).map((rawHit: any, i: number) => {
          // Map raw ES hit to consistent shape with friendly subject derivation
          const h = mapHit(rawHit);
          const safeKey = h.id ? `search-${h.id}` : `row-${i}`;

          // Format time-to-response as a compact badge if present
          const ttrH: number | null = h.time_to_response_hours;
          const ttrText = ttrH == null
            ? (h.replied ? 'Replied' : 'No reply')
            : (ttrH < 1
                ? `${Math.round(ttrH * 60)}m`
                : ttrH < 24
                ? `${Math.round(ttrH)}h`
                : `${Math.round(ttrH / 24)}d`)

          return (
            <li
              key={safeKey}
              data-testid="result-item"
              data-id={h.id || `fallback-${i}`}
              tabIndex={0}
              role="article"
              aria-label={`Email: ${h.subject}`}
              className="surface-card density-x density-y transition-all hover:shadow-lg focus:ring-2 focus:ring-primary focus:outline-none cursor-pointer"
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  // Could open email detail view here
                  console.log('Selected email:', h.id)
                }
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <h3
                    data-testid="result-subject"
                    data-derived={h.derived ? "1" : "0"}
                    className="font-semibold leading-snug text-[color:hsl(var(--foreground))]"
                    dangerouslySetInnerHTML={toMarkedHTML(h.subject)}
                  />
                  <div className="mt-1 text-xs text-[color:hsl(var(--muted-foreground))]">
                    {h.from} · {safeFormatDate(h.date) ?? '—'}
                  </div>
                </div>
                <div className="flex shrink-0 flex-row items-center gap-2">
                  {h.score !== undefined && h.score !== null && Math.round(h.score) > 0 && (
                    <span className="text-[11px] text-[color:hsl(var(--muted-foreground))]">
                      score: {Math.round(h.score)}
                    </span>
                  )}
                  <EmailLabels labels={h.labels} />

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
              {h.snippet && (
                <div
                  data-testid="snippet"
                  className="mt-2 text-sm text-[color:hsl(var(--muted-foreground))]"
                  dangerouslySetInnerHTML={toMarkedHTML(h.snippet)}
                />
              )}
            </li>
          )
          })}
        </ul>
      )}
    </div>
  )
}
