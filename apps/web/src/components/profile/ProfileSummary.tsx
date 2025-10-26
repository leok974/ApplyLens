import { useEffect, useState } from 'react'
import { Card, CardHeader, CardContent } from '../ui/card'
import { fetchProfileSummary, type ProfileSummaryResponse } from '../../lib/api'
import { Mail, TrendingUp, Tag, Heart } from 'lucide-react'

/**
 * ProfileSummary: Warehouse-backed profile dashboard
 *
 * Data source: BigQuery marts via /api/metrics/profile/summary
 * - Totals from mart_email_activity_daily
 * - Top senders from mart_top_senders_30d
 * - Top categories from mart_categories_30d
 * - Top interests from keyword extraction
 *
 * Cache: 60s backend, graceful degradation on failure
 */
export function ProfileSummary() {
  const [data, setData] = useState<ProfileSummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      setLoading(true)
      const summary = await fetchProfileSummary()
      setData(summary)
      setLoading(false)
    }
    loadData()
  }, [])

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-48 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="p-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">
            Unable to load profile data. Please try again later.
          </p>
        </div>
      </div>
    )
  }

  const { totals, top_senders_30d, top_categories_30d, top_interests } = data

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Profile Summary</h1>
        <p className="text-sm text-gray-600 mt-1">
          Account: {data.account}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Email Activity */}
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 pb-2">
            <Mail className="h-5 w-5 text-blue-600" />
            <h2 className="text-lg font-semibold">Email Activity</h2>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <p className="text-sm text-gray-600">Total Emails (All Time)</p>
                <p className="text-3xl font-bold text-gray-900">
                  {totals.all_time_emails.toLocaleString()}
                </p>
              </div>
              <div className="pt-3 border-t">
                <p className="text-sm text-gray-600">Last 30 Days</p>
                <p className="text-2xl font-semibold text-blue-600">
                  {totals.last_30d_emails.toLocaleString()}
                </p>
              </div>
              <div className="pt-3 border-t">
                <p className="text-xs text-gray-500">
                  Active account • Data refreshed hourly
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Top Senders */}
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 pb-2">
            <TrendingUp className="h-5 w-5 text-green-600" />
            <h2 className="text-lg font-semibold">Top Senders (Last 30 Days)</h2>
          </CardHeader>
          <CardContent>
            {top_senders_30d.length === 0 ? (
              <p className="text-sm text-gray-500">No data yet</p>
            ) : (
              <div className="space-y-3">
                {top_senders_30d.map((sender, idx) => (
                  <div key={idx} className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {sender.sender}
                      </p>
                      <p className="text-xs text-gray-500 truncate">
                        {sender.email}
                      </p>
                    </div>
                    <span className="ml-2 text-sm font-semibold text-green-600 flex-shrink-0">
                      {sender.count}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Card 3: Top Categories */}
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 pb-2">
            <Tag className="h-5 w-5 text-purple-600" />
            <h2 className="text-lg font-semibold">Top Categories (Last 30 Days)</h2>
          </CardHeader>
          <CardContent>
            {top_categories_30d.length === 0 ? (
              <p className="text-sm text-gray-500">No data yet</p>
            ) : (
              <div className="space-y-3">
                {top_categories_30d.map((cat, idx) => (
                  <div key={idx} className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-900 capitalize">
                      {cat.category}
                    </span>
                    <span className="text-sm font-semibold text-purple-600">
                      {cat.count}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Card 4: Top Interests */}
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 pb-2">
            <Heart className="h-5 w-5 text-pink-600" />
            <h2 className="text-lg font-semibold">Top Interests</h2>
          </CardHeader>
          <CardContent>
            {top_interests.length === 0 ? (
              <p className="text-sm text-gray-500">No data yet</p>
            ) : (
              <div className="space-y-3">
                {top_interests.map((interest, idx) => (
                  <div key={idx} className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-900 capitalize">
                      {interest.keyword}
                    </span>
                    <span className="text-sm font-semibold text-pink-600">
                      {interest.count}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          📊 Warehouse analytics • Fivetran + BigQuery
        </p>
      </div>
    </div>
  )
}
