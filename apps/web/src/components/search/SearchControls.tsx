import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { useSearchParams } from "react-router-dom"

const CATEGORIES = ["ats", "bills", "banks", "events", "promotions"] as const

export function SearchControls() {
  const [searchParams, setSearchParams] = useSearchParams()
  const hideExpired = searchParams.get("hideExpired") !== "0"
  const selectedCats = new Set(
    (searchParams.get("cat") ?? "").split(",").filter(Boolean)
  )

  const toggleCategory = (category: string) => {
    const newSet = new Set(selectedCats)
    if (newSet.has(category)) {
      newSet.delete(category)
    } else {
      newSet.add(category)
    }
    
    if (newSet.size > 0) {
      searchParams.set("cat", [...newSet].join(","))
    } else {
      searchParams.delete("cat")
    }
    setSearchParams(searchParams, { replace: true })
  }

  const setHideExpired = (value: boolean) => {
    if (value) {
      searchParams.delete("hideExpired")
    } else {
      searchParams.set("hideExpired", "0")
    }
    setSearchParams(searchParams, { replace: true })
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-3">
      <span className="text-sm font-medium text-muted-foreground">Filter by:</span>
      {CATEGORIES.map((cat) => (
        <Button
          key={cat}
          variant={selectedCats.has(cat) ? "default" : "secondary"}
          size="sm"
          onClick={() => toggleCategory(cat)}
          className="capitalize h-8"
          data-testid={`cat-${cat}`}
        >
          {cat}
        </Button>
      ))}
      
      <div className="ml-auto flex items-center gap-2">
        <Label htmlFor="hide-expired" className="text-sm cursor-pointer">
          Hide expired
        </Label>
        <Switch
          id="hide-expired"
          checked={hideExpired}
          onCheckedChange={setHideExpired}
          data-testid="switch-hide-expired"
        />
        <Button
          variant={hideExpired ? "secondary" : "default"}
          size="sm"
          onClick={() => setHideExpired(!hideExpired)}
          className="rounded-full h-8"
          data-testid="chip-expired-toggle"
        >
          {hideExpired ? "Show expired" : "Hide expired"}
        </Button>
      </div>
    </div>
  )
}
