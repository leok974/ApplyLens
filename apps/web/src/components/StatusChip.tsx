type Status =
  | 'applied'
  | 'hr_screen'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'on_hold'
  | 'ghosted'

const COLORS: Record<Status, string> = {
  applied: 'bg-gray-100/80 text-gray-700 border-gray-300/50 dark:bg-gray-800/60 dark:text-gray-300 dark:border-gray-700',
  hr_screen: 'bg-sky-100/80 text-sky-700 border-sky-300/50 dark:bg-sky-900/40 dark:text-sky-300 dark:border-sky-700',
  interview: 'bg-emerald-100/80 text-emerald-700 border-emerald-300/50 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-700',
  offer: 'bg-emerald-100/80 text-emerald-700 border-emerald-300/50 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-700',
  rejected: 'bg-red-100/80 text-red-700 border-red-300/50 dark:bg-red-900/40 dark:text-red-300 dark:border-red-700',
  on_hold: 'bg-amber-100/80 text-amber-700 border-amber-300/50 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-700',
  ghosted: 'bg-amber-100/80 text-amber-700 border-amber-300/50 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-700',
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
