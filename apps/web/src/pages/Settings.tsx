import { useState, useEffect } from 'react'
import { getRecencyScale, setRecencyScale, RecencyScale } from '../state/searchPrefs'
import { Card } from '@/components/ui/card'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/select'
import { Info } from 'lucide-react'
import { features } from '../config/features'
import { ProfileMetrics } from '../components/ProfileMetrics'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { logoutUser } from '@/lib/api'
import { getCurrentUser, type User } from '@/api/auth'

export default function Settings() {
  const [scale, setScale] = useState<RecencyScale>(getRecencyScale())
  const [user, setUser] = useState<User | null>(null)

  // Load user info
  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => {
        // Not authenticated, ignore
      })
  }, [])

  function onChangeScale(value: RecencyScale) {
    setScale(value)
    setRecencyScale(value)
  }

  async function handleLogout() {
    await logoutUser()
  }

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      <h1 className="text-3xl font-bold">Settings</h1>

      {/* Account Card */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Account</h2>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-sm text-muted-foreground">
              {user?.email ? (
                <>Signed in as <span className="font-medium text-foreground">{user.email}</span></>
              ) : (
                'Signed in'
              )}
            </p>
          </div>
          <Button
            variant="outline"
            onClick={handleLogout}
            data-testid="logout-button"
          >
            Log out
          </Button>
        </div>
      </Card>

      {/* Warehouse Metrics (feature-flagged) */}
      {features.warehouseMetrics && (
        <ProfileMetrics />
      )}

      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <h2 className="text-xl font-semibold">Search Scoring</h2>
          <Badge variant="secondary" className="text-xs">Experimental</Badge>
        </div>

        <div className="mb-4">
          <label className="block mb-2 text-sm font-medium">
            Recency Scale:
          </label>
          <Select value={scale} onValueChange={onChangeScale}>
            <SelectTrigger className="w-full max-w-sm">
              <SelectValue placeholder="Select scale" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="3d">3 days (more freshness)</SelectItem>
              <SelectItem value="7d">7 days (balanced) - Default</SelectItem>
              <SelectItem value="14d">14 days (more recall)</SelectItem>
            </SelectContent>
          </Select>
          <div className="text-xs text-muted-foreground mt-2">
            Controls the Gaussian decay scale for search result recency.
            Applies to <code className="px-1 py-0.5 bg-muted rounded">/search</code> via{' '}
            <code className="px-1 py-0.5 bg-muted rounded">?scale=3d|7d|14d</code> parameter.
          </div>
        </div>

        <Alert className="mt-4">
          <Info className="h-4 w-4" />
          <AlertTitle>Current Scoring Weights</AlertTitle>
          <AlertDescription>
            <ul className="mt-2 space-y-1 text-sm">
              <li>Offer: <strong>4.0×</strong> (highest priority)</li>
              <li>Interview: <strong>3.0×</strong></li>
              <li>Others: <strong>1.0×</strong></li>
              <li>Rejection: <strong>0.5×</strong> (de-emphasized)</li>
            </ul>
          </AlertDescription>
        </Alert>
      </Card>

      <div className="text-xs text-muted-foreground mt-6">
        More settings coming soon: muted senders, safe senders, data sync controls.
      </div>
    </div>
  )
}
