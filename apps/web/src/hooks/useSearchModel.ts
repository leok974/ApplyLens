import { useState, useCallback, useEffect } from 'react'
import { SearchHit } from '../lib/api'
import { SortKey } from '../components/SortControl'
import { RepliedFilter } from '../state/searchUi'
import { apiUrl } from '../lib/apiUrl'

export interface SearchFilters {
  labels: string[]
  dateFrom?: string
  dateTo?: string
  replied: RepliedFilter
  categories: Record<string, boolean>
  scale?: string
  hideExpired: boolean
  riskMin?: number
  quarantinedOnly: boolean
  limit?: number
}

const DEFAULT_FILTERS: SearchFilters = {
  labels: [],
  replied: 'all',
  categories: {},
  scale: '60d',
  hideExpired: false,
  riskMin: undefined,
  quarantinedOnly: false,
  limit: 50,
}

// Build query params matching backend API expectations
// Omit defaults to avoid stale URL params silently re-applying strict filters
// Always send a query - use "*" as fallback to avoid 422 errors
function toQueryParams({ query, filters, sort }: { query: string; filters: SearchFilters; sort: SortKey }) {
  const p = new URLSearchParams()

  // 🔥 Fallback to "*" (match-all) if query is empty to avoid 422 errors
  p.set('q', query?.trim() ? query.trim() : '*')

  // Only set scale if it's not the default (60d)
  if (filters.scale && filters.scale !== '60d') p.set('scale', String(filters.scale))

  // Only set replied if not 'all'
  if (filters.replied !== 'all') p.set('replied', String(filters.replied === 'true'))

  // Only set hideExpired if true (default is false)
  if (filters.hideExpired) p.set('hideExpired', 'true')

  // Only set riskMin if it's a valid number
  if (typeof filters.riskMin === 'number') p.set('risk_min', String(filters.riskMin))

  // Only set quarantinedOnly if true (default is false)
  if (filters.quarantinedOnly) p.set('quarantine', 'true')

  // Only set labels if there are any
  if (filters.labels?.length) p.set('labels', filters.labels.join(','))

  // Only set categories if any are active
  // Backend expects 'categories' as a list parameter (not 'cat')
  if (filters.categories) {
    const cats = Object.entries(filters.categories).filter(([, v]) => v).map(([k]) => k)
    if (cats.length) {
      // Send each category as a separate 'categories' parameter for FastAPI List[str]
      cats.forEach(cat => p.append('categories', cat))
    }
  }

  if (filters.dateFrom) p.set('from', filters.dateFrom)
  if (filters.dateTo) p.set('to', filters.dateTo)
  if (sort && sort !== 'relevance') p.set('sort', sort)

  // Always set limit
  p.set('limit', String(filters.limit ?? 50))
  return p
}

export function useSearchModel(initialQuery = '', initialFilters: Partial<SearchFilters> = {}, initialSort: SortKey = 'relevance') {
  const [query, setQuery] = useState(initialQuery)
  const [filters, setFilters] = useState<SearchFilters>({ ...DEFAULT_FILTERS, ...initialFilters })
  const [sort, setSort] = useState<SortKey>(initialSort)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<SearchHit[]>([])
  const [error, setError] = useState<string | null>(null)
  const [lastStatus, setLastStatus] = useState<number | null>(null)
  const [total, setTotal] = useState<number | undefined>(undefined)

  const runSearch = useCallback(async () => {
    // Don't block search if query is empty - we'll send "*" as fallback
    setLoading(true)
    setError(null)
    setLastStatus(null)

    try {
      const params = toQueryParams({ query, filters, sort })
      const url = apiUrl('/api/search', params)  // apiUrl auto-adds trailing slash
      const res = await fetch(url, {
        method: 'GET',
        credentials: 'include',
        redirect: 'follow',
      })

      // Handle 204 No Content
      if (res.status === 204) {
        setResults([])
        setTotal(0)
        setLoading(false)
        setLastStatus(204)
        console.debug('[search] 204 No Content', { query, filters, sort })
        return
      }

      if (!res.ok) {
        // Capture status for UI feedback
        setLastStatus(res.status)

        // Log response details for debugging
        const contentType = res.headers.get('content-type')
        console.error('[search] HTTP error', {
          status: res.status,
          statusText: res.statusText,
          contentType,
          url: res.url,
        })

        // Try to get error body
        const text = await res.text().catch(() => 'Unable to read response')

        // Special handling for 422 (Unprocessable Entity)
        if (res.status === 422) {
          throw new Error(`Search requires a query. We sent "*" automatically, but the server returned an error.`)
        }

        throw new Error(`Search failed: ${res.status} ${res.statusText}. ${text.substring(0, 100)}`)
      }

      // Success - capture status
      setLastStatus(res.status)

      // Check content type before parsing JSON
      const contentType = res.headers.get('content-type') || ''
      if (!contentType.includes('application/json')) {
        const body = (await res.text()).slice(0, 200)
        console.error('[search] Non-JSON response', {
          url: res.url,
          status: res.status,
          ct: contentType,
          body,
        })
        throw new Error(`Expected JSON but got ${contentType || 'unknown content-type'}`)
      }

      // SAFETY: Normalize all plausible response shapes (single source of truth)
      const j = await res.json()

      // Handle all observed backend shapes:
      // 1. { items: [...], total: N }
      // 2. { results: [...], total: N }
      // 3. { hits: [...] }  (backend already flattened)
      // 4. { hits: { hits: [...], total: {...} } }  (native ES shape)
      const esHitsArray = Array.isArray(j.hits) ? j.hits :           // backend already flattened
                          j.hits?.hits ?? []                          // native ES shape

      const rawItems = j.items
        ?? j.results
        ?? esHitsArray.map((h: any) => h._source ?? h.source ?? h)  // tolerate all ES variants
        ?? []

      const responseTotal = j.total
        ?? j.info?.total
        ?? (typeof j.hits?.total?.value === 'number' ? j.hits.total.value : rawItems.length)

      // Map fields to a stable schema that ResultRow expects
      const items = rawItems.map((x: any) => ({
        id: x.id ?? x.gmail_id ?? x._id ?? crypto.randomUUID(),
        subject: x.subject ?? x.title ?? '(no subject)',
        snippet: x.snippet ?? x.preview ?? x.body_preview ?? '',
        from: x.from_email ?? x.sender ?? x.from ?? '',
        from_addr: x.from_addr ?? x.from_email ?? x.sender ?? x.from ?? '',
        date: x.sent_at ?? x.received_at ?? x.date ?? null,
        received_at: x.received_at ?? x.sent_at ?? x.date ?? null,
        ...x,  // Preserve all other fields
      }))

      console.debug('[search] normalized', {
        q: query,
        filters,
        sort,
        status: res.status,
        total: responseTotal,
        sample: items?.[0],
        rawKeys: Object.keys(j || {}),
        rawShape: { hasItems: !!j.items, hasResults: !!j.results, hasHits: !!j.hits, isHitsArray: Array.isArray(j.hits) },
      })

      setResults(items)
      setTotal(responseTotal)
    } catch (err: any) {
      setError(err.message || 'Search failed')
      setResults([])
      setTotal(0)
      console.error('[search] error', err)
    } finally {
      setLoading(false)
    }
  }, [query, filters, sort])

  // Optional: auto-run when query/filters/sort change (debounced)
  useEffect(() => {
    if (!query.trim()) return

    const timer = setTimeout(() => {
      void runSearch()
    }, 400)

    return () => clearTimeout(timer)
  }, [runSearch])

  return {
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
  }
}
