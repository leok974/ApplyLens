import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRecencyScale, setRecencyScale, RecencyScale } from '../state/searchPrefs'
import { Card } from '@/components/ui/card'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/select'
import { Info, User as UserIcon } from 'lucide-react'
import { features } from '../config/features'
import { FLAGS } from '@/lib/flags'
import { ProfileMetrics } from '../components/ProfileMetrics'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { logout } from '@/api/auth'
import { getCurrentUser, fetchAndCacheCurrentUser } from '@/api/auth'

export default function Settings() {
  const navigate = useNavigate()
  const [scale, setScale] = useState<RecencyScale>(getRecencyScale())
  const [accountEmail, setAccountEmail] = useState<string | null>(null)

  // Load user email
  useEffect(() => {
    // Try cached first (fast path)
    const cached = getCurrentUser()
    if (cached?.email) {
      setAccountEmail(cached.email)
      return
    }

    // Fallback: fetch from API and cache it
    (async () => {
      const fresh = await fetchAndCacheCurrentUser()
      if (fresh?.email) {
        setAccountEmail(fresh.email)
      } else {
        setAccountEmail(null)
      }
    })()
  }, [])

  function onChangeScale(value: RecencyScale) {
    setScale(value)
    setRecencyScale(value)
  }

  async function handleLogout() {
    console.log('[Settings] handleLogout called - starting logout');
    try {
      await logout();
      console.log('[Settings] logout() completed, navigating to /welcome');
      navigate('/welcome', { replace: true });
      console.log('[Settings] navigate() called');
    } catch (error) {
      console.error('[Settings] logout failed:', error);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold">Settings</h1>

      {/* Account Card */}
      <Card className="p-6 surface-card">
        <h2 className="text-xl font-semibold mb-4">Account</h2>
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            {/* left side: icon + email */}
            <div className="flex items-start gap-3 text-sm">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-100 border border-zinc-300 text-zinc-700 dark:bg-zinc-800 dark:border-zinc-700 dark:text-zinc-300">
                <UserIcon className="h-4 w-4" />
              </div>
              <div className="flex flex-col leading-tight">
                <span className="text-zinc-600 dark:text-zinc-300">Signed in as</span>
                <span className="text-zinc-900 dark:text-white font-medium break-all">{accountEmail ?? "Loading..."}</span>
              </div>
            </div>

            {/* right side: logout button */}
            <div className="flex-shrink-0">
              <Button
                variant="outline"
                onClick={handleLogout}
                data-testid="logout-button"
              >
                Log out
              </Button>
            </div>
          </div>
        </Card>

        {/* Warehouse Metrics (feature-flagged) */}
        {features.warehouseMetrics && (
          <ProfileMetrics />
        )}

        <Card className="p-6 surface-card">
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
            <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-2">
              Controls the Gaussian decay scale for search result recency.
              Applies to <code className="px-1 py-0.5 bg-zinc-200 dark:bg-zinc-800 rounded">{"search"}</code> via{' '}
              <code className="px-1 py-0.5 bg-zinc-200 dark:bg-zinc-800 rounded">?scale=3d|7d|14d</code> parameter.
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

        <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-6">
          More settings coming soon: muted senders, safe senders, data sync controls.
        </div>

        {/* Browser Companion link (feature-flagged) */}
        {FLAGS.COMPANION && (
          <div className="mt-6 p-4 rounded-lg border bg-zinc-50 dark:bg-zinc-800/50">
            <h3 className="text-sm font-medium mb-2">Browser Companion</h3>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-3">
              Install the Chrome extension to autofill ATS forms and draft recruiter messages.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/settings/companion')}
            >
              View Companion Settings
            </Button>
          </div>
        )}
    </div>
  )
}
