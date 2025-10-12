import * as React from "react"
import { listApplicationsPaged, type ApplicationRow, type AppsSort, type AppsOrder } from "@/lib/api"

/**
 * ApplicationsList - Paginated applications list with Load More
 * 
 * Uses the new /api/applications endpoint with cursor-based pagination
 * and sorting support.
 */
export default function ApplicationsList() {
  const [rows, setRows] = React.useState<ApplicationRow[]>([])
  const [cursor, setCursor] = React.useState<string | null>(null)
  const [sort, setSort] = React.useState<AppsSort>("updated_at")
  const [order, setOrder] = React.useState<AppsOrder>("desc")
  const [statusFilter, setStatusFilter] = React.useState<string>("")
  const [loading, setLoading] = React.useState(false)
  const [total, setTotal] = React.useState<number | null>(null)

  async function load(reset = false) {
    setLoading(true)
    try {
      const res = await listApplicationsPaged({
        limit: 25,
        sort,
        order,
        status: statusFilter || null,
        cursor: reset ? null : cursor,
      })
      setRows(prev => reset ? res.items : [...prev, ...res.items])
      setCursor(res.next_cursor ?? null)
      setTotal(res.total ?? null)
    } catch (error) {
      console.error("Failed to load applications:", error)
    } finally {
      setLoading(false)
    }
  }

  // Reset when sort/order/status changes
  React.useEffect(() => {
    load(true)
  }, [sort, order, statusFilter])

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex gap-3 items-center flex-wrap">
        <div className="flex gap-2 items-center">
          <label className="text-sm font-medium">Sort:</label>
          <select
            value={sort}
            onChange={e => setSort(e.target.value as AppsSort)}
            className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="updated_at">Updated</option>
            <option value="applied_at">Applied</option>
            <option value="company">Company</option>
            <option value="status">Status</option>
          </select>
        </div>

        <div className="flex gap-2 items-center">
          <label className="text-sm font-medium">Order:</label>
          <select
            value={order}
            onChange={e => setOrder(e.target.value as AppsOrder)}
            className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>

        <div className="flex gap-2 items-center">
          <label className="text-sm font-medium">Status:</label>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All</option>
            <option value="applied">Applied</option>
            <option value="interview">Interview</option>
            <option value="offer">Offer</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        {total !== null && (
          <div className="ml-auto text-sm text-gray-600">
            Total: {total}
          </div>
        )}
      </div>

      {/* Applications List */}
      <div className="divide-y rounded-lg border overflow-hidden bg-white">
        {rows.length === 0 && !loading && (
          <div className="p-12 text-center text-gray-500">
            <div className="text-5xl mb-3">📭</div>
            <p>No applications found</p>
          </div>
        )}

        {rows.map((r, i) => (
          <div
            key={r.id ?? `row-${i}`}
            className="p-4 hover:bg-gray-50 transition"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-base mb-1">
                  {r.company ?? "—"} · {r.role ?? ""}
                </div>
                <div className="text-sm text-gray-600 space-x-3">
                  <span className="inline-flex items-center gap-1">
                    <span className="font-medium">Status:</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      r.status === 'offer' ? 'bg-green-100 text-green-800' :
                      r.status === 'interview' ? 'bg-blue-100 text-blue-800' :
                      r.status === 'applied' ? 'bg-gray-100 text-gray-800' :
                      r.status === 'rejected' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {r.status ?? "—"}
                    </span>
                  </span>
                  {r.applied_at && (
                    <span>
                      <span className="font-medium">Applied:</span> {new Date(r.applied_at).toLocaleDateString()}
                    </span>
                  )}
                  {r.updated_at && (
                    <span>
                      <span className="font-medium">Updated:</span> {new Date(r.updated_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
              {r.source && (
                <div className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                  {r.source}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Load More Button */}
      <div className="flex items-center justify-center gap-3">
        <button
          disabled={!cursor || loading}
          onClick={() => load(false)}
          className="px-4 py-2 rounded-lg border font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition"
        >
          {loading ? "Loading…" : cursor ? "Load more" : "No more results"}
        </button>
        
        {cursor && !loading && (
          <span className="text-sm text-gray-500">
            Showing {rows.length} {total !== null ? `of ${total}` : ''}
          </span>
        )}
      </div>
    </div>
  )
}
