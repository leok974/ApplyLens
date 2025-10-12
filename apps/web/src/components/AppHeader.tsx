import { NavigationMenu, NavigationMenuItem, NavigationMenuList, NavigationMenuLink } from "@/components/ui/navigation-menu"
import { Button } from "@/components/ui/button"
import ThemeToggle from "@/components/ThemeToggle"
import { Link } from "react-router-dom"
import { relabel, rebuildProfile, sync7d, sync60d } from "@/lib/api"
import { useState } from "react"
import { useToast } from "@/components/ui/use-toast"

const USER_EMAIL = "leoklemet.pa@gmail.com" // TODO: Read from auth context

export function AppHeader() {
  const [syncing, setSyncing] = useState(false)
  const { toast } = useToast()

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
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
