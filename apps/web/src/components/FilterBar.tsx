import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"

export function FilterBar() {
  return (
    <div className="rounded-xl border bg-card p-4 shadow-card">
      <div className="flex flex-wrap items-center gap-2">
        <Input 
          className="w-full md:w-1/3" 
          placeholder="Search subject/body…" 
        />
        <Input 
          className="w-full md:w-1/4" 
          placeholder="Filter: sender domain" 
        />
        <Select>
          <SelectTrigger className="w-full md:w-1/5">
            <SelectValue placeholder="Label: Any" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">Any</SelectItem>
            <SelectItem value="interview">Interview</SelectItem>
            <SelectItem value="offer">Offer</SelectItem>
            <SelectItem value="rejection">Rejection</SelectItem>
          </SelectContent>
        </Select>
        <Button className="ml-auto">Search</Button>
      </div>
    </div>
  )
}
