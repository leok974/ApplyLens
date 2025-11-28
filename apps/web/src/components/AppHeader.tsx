import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import ThemeToggle from "@/components/ThemeToggle"
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom"
import { relabel, rebuildProfile, startBackfillJob, cancelJob } from "@/lib/api"
import { useState, useEffect } from "react"
import { useToast } from "@/components/ui/use-toast"
import { ActionsTray } from "@/components/ActionsTray"
import { fetchTray } from "@/lib/actionsClient"
import { Sparkles, LogOut, User, ShieldCheck, X } from "lucide-react"
import { logout, getCurrentUser, fetchAndCacheCurrentUser, type User as UserType } from "@/api/auth"
import { cn } from "@/lib/utils"
import { useJobPoller } from "@/hooks/useJobPoller"
import { FLAGS } from "@/lib/flags"

const USER_EMAIL = "leoklemet.pa@gmail.com" // TODO: Read from auth context

export function AppHeader() {
  const [syncing, setSyncing] = useState(false)
  const [trayOpen, setTrayOpen] = useState(false)
  const [pendingCount, setPendingCount] = useState(0)
  const [user, setUser] = useState<UserType | null>(null)
  const [jobId, setJobId] = useState<string | undefined>()
  const { toast } = useToast()
  const location = useLocation()
  const navigate = useNavigate()

  // Poll job status with exponential backoff
  const jobStatus = useJobPoller(jobId)

  // Load user info
  useEffect(() => {
    // Try cached first (fast path)
    const cached = getCurrentUser()
    if (cached) {
      setUser(cached)
      return
    }

    // Fallback: fetch from API and cache it
    (async () => {
      const fresh = await fetchAndCacheCurrentUser()
      if (fresh) {
        setUser(fresh)
      }
    })()
  }, [])

  // Poll for pending actions count
  useEffect(() => {
    async function checkPending() {
      try {
        const actions = await fetchTray(100) // Fetch up to 100 to get accurate count
        setPendingCount(actions.length)
      } catch (error) {
        // Silently fail - don't spam user with errors
        console.error("Failed to fetch pending actions:", error)
      }
    }

    checkPending()
    const interval = setInterval(checkPending, 30000) // Poll every 30s
    return () => clearInterval(interval)
  }, [])

  // Handle job status changes
  useEffect(() => {
    if (!jobStatus) return

    console.log('[AppHeader] Job status update:', jobStatus)

    if (jobStatus.state === 'done') {
      // Backfill completed, proceed with ML labeling and profile rebuild
      toast({
        title: "✅ Gmail sync complete!",
        description: `Fetched ${jobStatus.inserted || 0} emails. Running ML classifier...`,
      })

      continueWithMLAndProfile()

      // Auto-refresh search results if user is on search page
      // Give ES a moment after refresh (network latency)
      if (location.pathname === '/search') {
        console.log('[AppHeader] Triggering search refresh after sync complete (800ms delay)')
        setTimeout(() => {
          window.dispatchEvent(new CustomEvent('search:refresh'))
        }, 800)
      }
    } else if (jobStatus.state === 'error') {
      toast({
        title: "❌ Sync failed",
        description: jobStatus.error || "Unknown error",
        variant: "destructive",
      })
      setSyncing(false)
      setJobId(undefined)
    } else if (jobStatus.state === 'canceled') {
      toast({
        title: "⏹️ Sync canceled",
        description: "Backfill was canceled",
      })
      setSyncing(false)
      setJobId(undefined)
    }
  }, [jobStatus])

  async function continueWithMLAndProfile() {
    try {
      // Step 2: Apply ML labels
      toast({
        title: "🏷️ Applying smart labels...",
        description: "Categorizing emails with ML",
      })
      const labelResult = await relabel(2000)

      // Step 3: Rebuild user profile
      toast({
        title: "👤 Updating your profile...",
        description: "Analyzing senders and interests",
      })
      await rebuildProfile(USER_EMAIL)

      // Success!
      toast({
        title: "🎉 All done!",
        description: `Pipeline complete. ${labelResult.updated} emails labeled.`,
      })
    } catch (error: any) {
      console.error("ML/Profile error:", error)
      toast({
        title: "⚠️ Partial failure",
        description: "Sync succeeded but ML/profile failed. Try refreshing.",
        variant: "destructive",
      })
    } finally {
      setSyncing(false)
      setJobId(undefined)
    }
  }

  async function runPipeline(days: 7 | 60) {
    setSyncing(true)

    try {
      // Start async backfill job
      toast({
        title: `🔄 Starting ${days}-day sync...`,
        description: "This will run in the background. You'll be notified when ready.",
      })

      const result = await startBackfillJob(days, USER_EMAIL)

      // Store job ID to start polling
      setJobId(result.job_id)

      console.log(`[AppHeader] Started backfill job: ${result.job_id}`)

    } catch (error: any) {
      console.error("Pipeline error:", error)


      toast({
        title: "❌ Failed to start sync",
        description: error?.message || "Please try again",
        variant: "destructive",
      })
      setSyncing(false)
    }
  }

  async function handleCancelJob() {
    if (!jobId) return

    try {
      await cancelJob(jobId)
      toast({
        title: "⏹️ Job canceled",
        description: "The sync has been stopped",
      })
      setSyncing(false)
      setJobId(undefined)
    } catch (error: any) {
      console.error("Cancel error:", error)
      toast({
        title: "Failed to cancel",
        description: error?.message || "Please try again",
        variant: "destructive",
      })
    }
  }

  const handleLogout = async () => {
    console.log('[AppHeader] handleLogout called - starting logout');
    try {
      await logout();
      console.log('[AppHeader] logout() completed, navigating to /welcome');
      navigate('/welcome', { replace: true });
      console.log('[AppHeader] navigate() called');
    } catch (error) {
      console.error("[AppHeader] Logout failed:", error);
      toast({
        title: "Logout failed",
        description: "Please try again",
        variant: "destructive",
      })
    }
  }

  const getUserInitials = () => {
    if (!user) return "?"
    if (user.name) {
      const parts = user.name.split(" ")
      return parts.length > 1
        ? `${parts[0][0]}${parts[1][0]}`.toUpperCase()
        : user.name.substring(0, 2).toUpperCase()
    }
    return user.email.substring(0, 2).toUpperCase()
  }

  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b backdrop-blur bg-white/80 text-zinc-900 border-zinc-300 dark:bg-[#0f172a]/80 dark:text-zinc-100 dark:border-zinc-800">
        <div className="mx-auto max-w-6xl px-4 md:px-6 lg:px-8">
          <div className="flex h-14 items-center gap-4">
            {/* BRAND — never shrink */}
            <Link
              to="/"
              className="group flex items-center gap-2 shrink-0 select-none"
              data-testid="header-brand"
              aria-label="ApplyLens Home"
            >
              <img
                src="/brand/applylens.png"
                alt=""
                className="logo-hover brand-enter h-9 w-9 object-contain"
                draggable={false}
              />
              <span className="brand-tight text-lg font-semibold leading-none whitespace-nowrap transition-colors duration-150 group-hover:text-primary">
                ApplyLens
              </span>
            </Link>

            {/* NAV — scrollable middle section */}
            <nav className="flex min-w-0 flex-1 items-center overflow-x-auto gap-1 scrollbar-none">
              <Tab to="/" label="Inbox" />
              <Tab to="/inbox-actions" label="Actions" />
              <Tab to="/search" label="Search" />
              <Tab to="/chat" label="Chat" />
              <Tab to="/today" label="Today" data-testid="nav-today" />
              <Tab to="/followups" label="Follow-ups" data-testid="nav-followup-queue" />
              <Tab to="/tracker" label="Tracker" />
              <Tab to="/opportunities" label="Opportunities" data-testid="nav-opportunities" />
              <Tab to="/profile" label="Profile" />
              {FLAGS.COMPANION && <Tab to="/extension" label="Companion" data-testid="nav-companion" />}
              <Tab to="/settings" label="Settings" />
            </nav>

            {/* RIGHT ACTIONS — never shrink, always visible */}
            <div className="flex items-center gap-2 shrink-0">
            {/* Job Progress Indicator */}
            {jobStatus && jobStatus.state !== 'done' && (
              <div className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-md bg-muted border">
                {jobStatus.state === 'running' && (
                  <>
                    <span className="animate-pulse">🔄</span>
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {jobStatus.processed || 0}
                          {jobStatus.total && ` / ${jobStatus.total}`}
                          {jobStatus.total && ` (${Math.round((jobStatus.processed / jobStatus.total) * 100)}%)`}
                        </span>
                        {jobStatus.total && jobStatus.processed > 0 && (
                          <span className="text-muted-foreground">
                            {(() => {
                              const rate = jobStatus.processed / ((Date.now() / 1000) - (jobStatus.started_at || 0))
                              const remaining = jobStatus.total - jobStatus.processed
                              const etaSeconds = Math.ceil(remaining / rate)
                              return etaSeconds > 60
                                ? `~${Math.ceil(etaSeconds / 60)}m remaining`
                                : `~${etaSeconds}s remaining`
                            })()}
                          </span>
                        )}
                      </div>
                      {jobStatus.total && (
                        <div className="w-32 h-1 bg-background rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all duration-300"
                            style={{ width: `${Math.min((jobStatus.processed / jobStatus.total) * 100, 100)}%` }}
                          />
                        </div>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0"
                      onClick={handleCancelJob}
                      title="Cancel sync"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </>
                )}
                {jobStatus.state === 'queued' && (
                  <>
                    <span className="animate-pulse">⏳</span>
                    <span className="font-medium">Queued...</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0"
                      onClick={handleCancelJob}
                      title="Cancel sync"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </>
                )}
                {jobStatus.state === 'error' && (
                  <>
                    <span>⚠️</span>
                    <span className="font-medium text-destructive">Error</span>
                  </>
                )}
                {jobStatus.state === 'canceled' && (
                  <>
                    <span>⏹️</span>
                    <span className="font-medium">Canceled</span>
                  </>
                )}
              </div>
            )}

            {/* Sync buttons - only show on larger screens since inbox page has them */}
            <Button
              size="sm"
              variant="secondary"
              onClick={() => runPipeline(7)}
              disabled={syncing}
              className="hidden lg:inline-flex"
              data-testid="sync-7d"
            >
              {syncing ? "⏳" : "Sync 7d"}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => runPipeline(60)}
              disabled={syncing}
              className="hidden lg:inline-flex"
              data-testid="sync-60d"
            >
              {syncing ? "⏳" : "Sync 60d"}
            </Button>

            {/* Actions Tray Button */}
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setTrayOpen(true)}
              className="relative"
              data-testid="quick-actions"
            >
              <Sparkles className="h-4 w-4 mr-1" />
              <span className="hidden sm:inline">Actions</span>
              {pendingCount > 0 && (
                <span className="ml-2 rounded-full bg-red-600 text-white text-[10px] px-1.5 py-[2px] leading-none">
                  {pendingCount}
                </span>
              )}
            </Button>

            <ThemeToggle data-testid="theme-toggle" />

            {/* User menu */}
            {user && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                    <Avatar className="h-9 w-9">
                      <AvatarImage src={user.picture_url} alt={user.name || user.email} />
                      <AvatarFallback>{getUserInitials()}</AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56" align="end" forceMount>
                  <DropdownMenuLabel className="font-normal">
                    <div className="flex flex-col space-y-1">
                      <p className="text-sm font-medium leading-none">
                        {user.name || "User"}
                      </p>
                      <p className="text-xs leading-none text-muted-foreground">
                        {user.email}
                      </p>
                      {user.is_demo && (
                        <Badge variant="secondary" className="w-fit mt-1">
                          Demo Mode
                        </Badge>
                      )}
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />

                  {/* Settings Section */}
                  <DropdownMenuItem asChild>
                    <Link to="/settings" className="cursor-pointer">
                      <User className="mr-2 h-4 w-4" />
                      Settings
                    </Link>
                  </DropdownMenuItem>

                  {/* Sender Controls */}
                  <DropdownMenuItem asChild>
                    <Link to="/settings/senders" className="cursor-pointer" data-testid="settings-senders-link">
                      <ShieldCheck className="mr-2 h-4 w-4 text-green-400" />
                      <div className="flex flex-col">
                        <span className="font-medium">Sender Controls</span>
                        <span className="text-xs text-muted-foreground">Trusted / muted senders</span>
                      </div>
                    </Link>
                  </DropdownMenuItem>

                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-destructive">
                    <LogOut className="mr-2 h-4 w-4" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </div>
      </div>
    </header>

    {/* Actions Tray - Rendered outside header as fixed overlay */}
    <ActionsTray isOpen={trayOpen} onClose={() => setTrayOpen(false)} />
  </>
  )
}

function Tab({ to, label, "data-testid": dataTestId }: { to: string; label: string; "data-testid"?: string }) {
  return (
    <NavLink
      to={to}
      data-testid={dataTestId}
      className={({ isActive }) =>
        cn(
          "shrink-0 px-3 h-8 inline-flex items-center rounded-md text-xs sm:text-sm whitespace-nowrap",
          "hover:bg-muted/70 transition-colors",
          isActive ? "bg-muted font-medium" : "text-muted-foreground"
        )
      }
    >
      {label}
    </NavLink>
  )
}
