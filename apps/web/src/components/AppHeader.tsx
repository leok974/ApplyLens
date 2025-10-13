import { NavigationMenu, NavigationMenuItem, NavigationMenuList, NavigationMenuLink } from "@/components/ui/navigation-menu"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import ThemeToggle from "@/components/ThemeToggle"
import { Link } from "react-router-dom"
import { relabel, rebuildProfile, sync7d, sync60d } from "@/lib/api"
import { useState, useEffect } from "react"
import { useToast } from "@/components/ui/use-toast"
import { ActionsTray } from "@/components/ActionsTray"
import { fetchTray } from "@/lib/actionsClient"
import { Sparkles } from "lucide-react"

const USER_EMAIL = "leoklemet.pa@gmail.com" // TODO: Read from auth context

export function AppHeader() {
  const [syncing, setSyncing] = useState(false)
  const [trayOpen, setTrayOpen] = useState(false)
  const [pendingCount, setPendingCount] = useState(0)
  const { toast } = useToast()

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

  async function runPipeline(days: 7 | 60) {
    setSyncing(true)
    const syncFn = days === 7 ? sync7d : sync60d
    
    try {
      // Step 1: Gmail backfill
      toast({
        title: `🔄 Syncing last ${days} days...`,
        description: "Fetching emails from Gmail",
      })
      await syncFn()
      
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
        title: "✅ Sync complete!",
        description: `Labels + Profile updated. ${labelResult.updated} emails processed.`,
      })
    } catch (error: any) {
      console.error("Pipeline error:", error)
      toast({
        title: "❌ Sync failed",
        description: error?.message ?? String(error),
        variant: "destructive",
      })
    } finally {
      setSyncing(false)
    }
  }

  return (
    <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
        <h1 className="text-xl font-semibold">Gmail Inbox</h1>

        <NavigationMenu className="ml-4 hidden md:block">
          <NavigationMenuList>
            {[
              ["Inbox", "/"],
              ["Inbox (Actions)", "/inbox-actions"],
              ["Search", "/search"],
              ["Chat", "/chat"],
              ["Tracker", "/tracker"],
              ["Profile", "/profile"],
              ["Settings", "/settings"],
            ].map(([label, to]) => (
              <NavigationMenuItem key={to}>
                <NavigationMenuLink asChild>
                  <Link 
                    className="px-3 py-2 rounded-lg border bg-card hover:bg-secondary text-sm transition-colors" 
                    to={to}
                    data-testid={label === "Profile" ? "nav-profile" : undefined}
                  >
                    {label}
                  </Link>
                </NavigationMenuLink>
              </NavigationMenuItem>
            ))}
          </NavigationMenuList>
        </NavigationMenu>

        <div className="ml-auto flex items-center gap-2">
          <Button 
            size="sm" 
            onClick={() => runPipeline(7)}
            disabled={syncing}
            data-testid="btn-sync-7"
          >
            {syncing ? "⏳ Syncing..." : "Sync 7 days"}
          </Button>
          <Button 
            size="sm" 
            onClick={() => runPipeline(60)}
            disabled={syncing}
            data-testid="btn-sync-60"
          >
            {syncing ? "⏳ Syncing..." : "Sync 60 days"}
          </Button>
          
          {/* Actions Tray Button */}
          <Button
            size="sm"
            variant="outline"
            onClick={() => setTrayOpen(true)}
            className="relative"
            data-testid="btn-actions-tray"
          >
            <Sparkles className="h-4 w-4 mr-1" />
            Actions
            {pendingCount > 0 && (
              <Badge
                variant="destructive"
                className="ml-2 px-1.5 py-0 text-xs h-5 min-w-5"
              >
                {pendingCount}
              </Badge>
            )}
          </Button>

          <ThemeToggle />
        </div>
      </div>

      {/* Actions Tray */}
      <ActionsTray isOpen={trayOpen} onClose={() => setTrayOpen(false)} />
    </header>
  )
}
