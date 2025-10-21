import { NavigationMenu, NavigationMenuItem, NavigationMenuList, NavigationMenuLink } from "@/components/ui/navigation-menu"
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
import { HealthBadge } from "@/components/HealthBadge"
import { Link } from "react-router-dom"
import { relabel, rebuildProfile, sync7d, sync60d } from "@/lib/api"
import { useState, useEffect } from "react"
import { useToast } from "@/components/ui/use-toast"
import { ActionsTray } from "@/components/ActionsTray"
import { fetchTray } from "@/lib/actionsClient"
import { Sparkles, LogOut, User } from "lucide-react"
import { logout, getCurrentUser, type User as UserType } from "@/api/auth"

const USER_EMAIL = "leoklemet.pa@gmail.com" // TODO: Read from auth context

export function AppHeader() {
  const [syncing, setSyncing] = useState(false)
  const [trayOpen, setTrayOpen] = useState(false)
  const [pendingCount, setPendingCount] = useState(0)
  const [user, setUser] = useState<UserType | null>(null)
  const { toast } = useToast()

  // Load user info
  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => {
        // Not authenticated, ignore
      })
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

  const handleLogout = async () => {
    try {
      await logout()
      window.location.href = "/welcome"
    } catch (error) {
      console.error("Logout failed:", error)
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
          {/* Warehouse Health Badge */}
          <HealthBadge />
          
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
                <DropdownMenuItem asChild>
                  <Link to="/settings" className="cursor-pointer">
                    <User className="mr-2 h-4 w-4" />
                    Settings
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

      {/* Actions Tray */}
      <ActionsTray isOpen={trayOpen} onClose={() => setTrayOpen(false)} />
    </header>
  )
}
