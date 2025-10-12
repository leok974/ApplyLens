import { NavigationMenu, NavigationMenuItem, NavigationMenuList, NavigationMenuLink } from "@/components/ui/navigation-menu"
import { Button } from "@/components/ui/button"
import ThemeToggle from "@/components/ThemeToggle"
import { Link } from "react-router-dom"

export function AppHeader() {
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
              ["Settings", "/settings"],
            ].map(([label, to]) => (
              <NavigationMenuItem key={to}>
                <NavigationMenuLink asChild>
                  <Link 
                    className="px-3 py-2 rounded-lg border bg-card hover:bg-secondary text-sm transition-colors" 
                    to={to}
                  >
                    {label}
                  </Link>
                </NavigationMenuLink>
              </NavigationMenuItem>
            ))}
          </NavigationMenuList>
        </NavigationMenu>

        <div className="ml-auto flex items-center gap-2">
          <Button size="sm">Sync 7 days</Button>
          <Button size="sm">Sync 60 days</Button>
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
