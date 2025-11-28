import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRecencyScale, setRecencyScale, RecencyScale } from '../state/searchPrefs'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/select'
import { Info, User as UserIcon, Sun, Moon, Laptop } from 'lucide-react'
import { features } from '../config/features'
import { FLAGS } from '@/lib/flags'
import { ProfileMetrics } from '../components/ProfileMetrics'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { logout } from '@/api/auth'
import { getCurrentUser, fetchAndCacheCurrentUser } from '@/api/auth'
import { VersionCard } from '@/components/settings/VersionCard'
import { HealthBadge } from '@/components/HealthBadge'
import { MailboxThemePanel } from '@/components/settings/MailboxThemePanel'
import { ResumeUploadPanel } from '@/components/settings/ResumeUploadPanel'
import { useTheme } from '@/hooks/useTheme'
import { startBackfillJob } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'

export default function Settings() {
  const navigate = useNavigate()
  const [scale, setScale] = useState<RecencyScale>(getRecencyScale())
  const [accountEmail, setAccountEmail] = useState<string | null>(null)
  const [isLoadingUser, setIsLoadingUser] = useState(true)
  const [authError, setAuthError] = useState<string | null>(null)
  const { theme, setTheme } = useTheme()
  const { toast } = useToast()
  const [syncing, setSyncing] = useState(false)

  // Load user email with proper auth failure handling
  useEffect(() => {
    let cancelled = false

    async function loadUser() {
      try {
        // Try cached first (fast path)
        const cached = getCurrentUser()
        if (cached?.email) {
          if (!cancelled) {
            setAccountEmail(cached.email)
            setIsLoadingUser(false)
          }
          return
        }

        // Fallback: fetch from API and cache it
        const fresh = await fetchAndCacheCurrentUser()

        if (cancelled) return

        // 🔑 If user is null, we treat this as "not authenticated"
        if (!fresh) {
          setAuthError('Session expired or missing.')
          navigate('/welcome', { replace: true })
          return
        }

        if (fresh.email) {
          setAccountEmail(fresh.email)
        } else {
          // User object exists but no email - shouldn''t happen, but handle gracefully
          setAuthError('Unable to load account information.')
          navigate('/welcome', { replace: true })
        }
      } catch (error) {
        console.error('[Settings] Failed to load current user:', error)
        if (!cancelled) {
          setAuthError('Unable to load account. Please log in again.')
          navigate('/welcome', { replace: true })
        }
      } finally {
        if (!cancelled) {
          setIsLoadingUser(false)
        }
      }
    }

    loadUser()

    return () => {
      cancelled = true
    }
  }, [navigate])

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

  async function handleSync(window: "7d" | "60d") {
    if (!accountEmail) return;
    setSyncing(true);
    try {
      const days = window === "7d" ? 7 : 60;
      toast({
        title: `🔄 Starting ${days}-day sync...`,
        description: "This will run in the background.",
      });
      const result = await startBackfillJob(days, accountEmail);
      toast({
        title: "✅ Sync started!",
        description: `Job ID: ${result.job_id}. Check the header for progress.`,
      });
    } catch (error: any) {
      console.error("Sync error:", error);
      toast({
        title: "❌ Failed to start sync",
        description: error?.message || "Please try again",
        variant: "destructive",
      });
    } finally {
      setSyncing(false);
    }
  }

  // Show loading state while fetching user
  if (isLoadingUser) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-muted-foreground">Loading your settings…</p>
      </div>
    )
  }

  // Show auth error state (shouldn''t normally be visible due to redirect)
  if (authError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <p className="font-medium">You''re not signed in.</p>
        <p className="text-sm text-muted-foreground">
          {authError} Please sign in again to manage your ApplyLens settings.
        </p>
        <Button onClick={() => navigate('/welcome', { replace: true })}>
          Go to sign-in
        </Button>
      </div>
    )
  }

  // Defensive guard: no account email after loading
  if (!accountEmail) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <p className="font-medium">We couldn''t find your account.</p>
        <Button onClick={() => navigate('/welcome', { replace: true })}>
          Re-authenticate
        </Button>
      </div>
    )
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
                <span className="text-zinc-900 dark:text-white font-medium break-all">{accountEmail}</span>
              </div>
            </div>

            {/* right side: logout button */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
              className="shrink-0"
            >
              Log out
            </Button>
          </div>
      </Card>

      {/* Gmail Sync */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Gmail Sync</CardTitle>
          <CardDescription className="text-xs">
            Manually trigger ApplyLens to pull the latest emails from your connected inbox.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleSync("7d")}
            disabled={syncing}
          >
            {syncing ? "⏳ Syncing..." : "Sync last 7 days"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleSync("60d")}
            disabled={syncing}
          >
            {syncing ? "⏳ Syncing..." : "Sync last 60 days"}
          </Button>
        </CardContent>
      </Card>

      {/* Appearance / Theme */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Appearance</CardTitle>
          <CardDescription className="text-xs">
            Choose how ApplyLens looks on this device.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant={theme === "light" ? "default" : "outline"}
            onClick={() => setTheme("light")}
            className="gap-1"
          >
            <Sun className="h-4 w-4" />
            Light
          </Button>
          <Button
            size="sm"
            variant={theme === "dark" ? "default" : "outline"}
            onClick={() => setTheme("dark")}
            className="gap-1"
          >
            <Moon className="h-4 w-4" />
            Dark
          </Button>
          <Button
            size="sm"
            variant={theme === "system" ? "default" : "outline"}
            onClick={() => setTheme("system")}
            className="gap-1"
          >
            <Laptop className="h-4 w-4" />
            System
          </Button>
        </CardContent>
      </Card>

      {/* Resume Upload */}
      <ResumeUploadPanel />

      {/* Mailbox Theme */}
      <MailboxThemePanel />

      {/* Search Scoring */}
      {features.searchScoring && (
        <Card className="p-6 surface-card">
          <div className="mb-4 flex items-center gap-2">
            <h2 className="text-xl font-semibold">Search Scoring</h2>
            <Badge variant="secondary" className="text-xs">Experimental</Badge>
          </div>
          <Alert className="mb-4">
            <Info className="h-4 w-4" />
            <AlertTitle>What is this?</AlertTitle>
            <AlertDescription>
              Control the Gaussian decay scale for search result recency. Applies to <code>search</code> via <code>?recalc=d|7d|14d</code> parameter.
            </AlertDescription>
          </Alert>
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
            <label htmlFor="recencyScale" className="text-sm font-medium">
              Recency Scale:
            </label>
            <Select value={scale} onValueChange={onChangeScale}>
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">7 days (balanced)</SelectItem>
                <SelectItem value="30d">30 days</SelectItem>
                <SelectItem value="60d">60 days</SelectItem>
                <SelectItem value="90d">90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </Card>
      )}

      {/* Profile Metrics */}
      {FLAGS?.PROFILE_METRICS && <ProfileMetrics />}

      {/* Version info */}
      <VersionCard />

      {/* Health Badge */}
      <HealthBadge />

      <div className="text-xs text-muted-foreground pb-6">
        More settings coming soon: muted senders, safe senders, data sync controls.
      </div>
    </div>
  )
}
