import { Card } from "@/components/ui/card"
import { LabelFilterChips } from "./LabelFilterChips"
import { DateRangeControls } from "./DateRangeControls"
import { RepliedFilterChips } from "./RepliedFilterChips"
import { SortControl, SortKey } from "./SortControl"
import { Button } from "@/components/ui/button"
import { RepliedFilter } from "../state/searchUi"

interface SearchFiltersProps {
  labels: string[]
  onLabelsChange: (labels: string[]) => void
  dates: { from?: string; to?: string }
  onDatesChange: (dates: { from?: string; to?: string }) => void
  replied: RepliedFilter
  onRepliedChange: (replied: RepliedFilter) => void
  sort: SortKey
  onSortChange: (sort: SortKey) => void
}

export function SearchFilters({
  labels,
  onLabelsChange,
  dates,
  onDatesChange,
  replied,
  onRepliedChange,
  sort,
  onSortChange,
}: SearchFiltersProps) {
  const hasActiveFilters =
    labels.length > 0 ||
    dates.from ||
    dates.to ||
    replied !== "all" ||
    sort !== "relevance"

  const clearAllFilters = () => {
    onLabelsChange([])
    onDatesChange({})
    onRepliedChange("all")
    onSortChange("relevance")
  }

  return (
    <Card className="p-4 mb-4">
      <div className="space-y-4">
        <div>
          <div className="text-xs font-medium mb-2 text-muted-foreground">
            Filter by label:
          </div>
          <LabelFilterChips value={labels} onChange={onLabelsChange} />
        </div>

        <div>
          <div className="text-xs font-medium mb-2 text-muted-foreground">
            Filter by date:
          </div>
          <DateRangeControls
            from={dates.from}
            to={dates.to}
            onChange={onDatesChange}
          />
        </div>

        <div>
          <div className="text-xs font-medium mb-2 text-muted-foreground">
            Filter by reply status:
          </div>
          <RepliedFilterChips value={replied} onChange={onRepliedChange} />
        </div>

        <div>
          <div className="text-xs font-medium mb-2 text-muted-foreground">
            Sort results:
          </div>
          <SortControl value={sort} onChange={onSortChange} />
        </div>

        {hasActiveFilters && (
          <div className="text-right pt-2 border-t">
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="text-xs text-muted-foreground"
            >
              Clear all filters
            </Button>
          </div>
        )}
      </div>
    </Card>
  )
}
