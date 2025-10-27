export type SortKey = 'relevance' | 'received_desc' | 'received_asc' | 'ttr_asc' | 'ttr_desc'

export function SortControl({
  value,
  onChange,
}: {
  value: SortKey
  onChange: (v: SortKey) => void
}) {
  return (
    <label className="text-xs inline-flex items-center gap-2">
      Sort:&nbsp;
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as SortKey)}
        data-testid="filter-sort"
      >
        <option value="relevance">Relevance</option>
        <option value="received_desc">Newest</option>
        <option value="received_asc">Oldest</option>
        <option value="ttr_asc">Fastest response</option>
        <option value="ttr_desc">Slowest / no-reply first</option>
      </select>
    </label>
  )
}
