type Status =
  | 'applied'
  | 'hr_screen'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'on_hold'
  | 'ghosted'

const COLORS: Record<Status, string> = {
  applied: 'bg-gray-100 text-gray-800 border-gray-200',
  hr_screen: 'bg-sky-100 text-sky-800 border-sky-200',
  interview: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  offer: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  rejected: 'bg-red-100 text-red-800 border-red-200',
  on_hold: 'bg-amber-100 text-amber-800 border-amber-200',
  ghosted: 'bg-amber-100 text-amber-800 border-amber-200',
}

const LABELS: Record<Status, string> = {
  applied: 'Applied',
  hr_screen: 'HR Screen',
  interview: 'Interview',
  offer: 'Offer',
  rejected: 'Rejected',
  on_hold: 'On Hold',
  ghosted: 'Ghosted',
}

export default function StatusChip({ status }: { status: Status }) {
  return (
    <span
      className={`inline-flex items-center rounded-2xl border px-2 py-0.5 text-xs font-medium ${COLORS[status]}`}
      data-testid={`status-chip-${status}`}
    >
      {LABELS[status]}
    </span>
  )
}
