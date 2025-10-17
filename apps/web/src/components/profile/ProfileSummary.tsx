import { useEffect, useState } from "react"
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { API_BASE } from "@/lib/apiBase"
import { getEmailCount, getEmailStats, EmailStatsResponse } from "@/lib/api"

const USER_EMAIL = "leoklemet.pa@gmail.com" // TODO: Read from auth context

type ProfileData = {
  user_email: string
  top_senders: Array<{
    domain: string
    total: number
    categories: Record<string, number>
    open_rate: number
  }>
  categories: Array<{
    category: string
    total: number
  }>
  interests: Array<{
    keyword: string
    score: number
  }>
}

export function ProfileSummary() {
  const [data, setData] = useState<ProfileData | null>(null)
  const [emailStats, setEmailStats] = useState<EmailStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [statsLoading, setStatsLoading] = useState(true)

  useEffect(() => {
    // Load email stats (fast cached endpoint)
    Promise.all([getEmailCount(), getEmailStats()])
      .then(([_count, stats]) => {
        setEmailStats(stats)
      })
      .catch((err) => {
        console.error('Failed to load email stats:', err)
      })
      .finally(() => setStatsLoading(false))

    // Load profile data
    fetch(`${API_BASE}/profile/db-summary?user_email=${encodeURIComponent(USER_EMAIL)}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-5 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-20 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center text-muted-foreground py-8">
        No profile data available. Click "Sync" to build your profile.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Fast Email Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Total Emails</CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-10 w-20" />
            ) : (
              <div className="text-3xl font-bold">{emailStats?.total ?? '—'}</div>
            )}
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Last 30 Days</CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-10 w-20" />
            ) : (
              <div className="text-3xl font-bold">{emailStats?.last_30d ?? '—'}</div>
            )}
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Active Account</CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-6 w-40" />
            ) : (
              <div className="text-sm font-medium truncate">{emailStats?.owner_email ?? '—'}</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Top Senders from Stats Endpoint */}
      {emailStats && emailStats.top_senders.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Senders (Last 30 Days)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {emailStats.top_senders.map((sender) => (
              <div
                key={sender.sender}
                className="flex justify-between text-sm items-center"
              >
                <span className="truncate flex-1 font-mono text-xs">
                  {sender.sender}
                </span>
                <span className="text-muted-foreground ml-2">
                  {sender.count}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Top Categories from Stats Endpoint */}
      {emailStats && emailStats.top_categories.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Categories</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {emailStats.top_categories.map((cat) => (
              <div
                key={cat.category}
                className="flex justify-between text-sm items-center"
              >
                <span className="capitalize">{cat.category}</span>
                <span className="text-muted-foreground">{cat.count}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Original Profile Data */}
      <div className="grid gap-4 md:grid-cols-3">
      {/* Top Senders */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Top Senders (All Time)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {data?.top_senders?.slice(0, 10).map((sender) => (
            <div
              key={sender.domain}
              className="flex justify-between text-sm items-center"
            >
              <span className="truncate flex-1 font-mono text-xs">
                {sender.domain}
              </span>
              <span className="text-muted-foreground ml-2">
                {sender.total}
              </span>
            </div>
          ))}
          {(!data?.top_senders || data.top_senders.length === 0) && (
            <p className="text-sm text-muted-foreground">No senders found</p>
          )}
        </CardContent>
      </Card>

      {/* Top Categories */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Top Categories (All Time)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {data?.categories?.slice(0, 10).map((cat) => (
            <div
              key={cat.category}
              className="flex justify-between text-sm items-center"
            >
              <span className="capitalize">{cat.category}</span>
              <span className="text-muted-foreground">{cat.total}</span>
            </div>
          ))}
          {(!data?.categories || data.categories.length === 0) && (
            <p className="text-sm text-muted-foreground">No categories found</p>
          )}
        </CardContent>
      </Card>

      {/* Interests */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Top Interests</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {data?.interests?.slice(0, 10).map((interest) => (
            <div
              key={interest.keyword}
              className="flex justify-between text-sm items-center"
            >
              <span className="truncate flex-1">{interest.keyword}</span>
              <span className="text-muted-foreground ml-2">
                {Math.round(interest.score)}
              </span>
            </div>
          ))}
          {(!data?.interests || data.interests.length === 0) && (
            <p className="text-sm text-muted-foreground">No interests found</p>
          )}
        </CardContent>
      </Card>
      </div>
    </div>
  )
}
