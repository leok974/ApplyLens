import { useTheme } from '@/hooks/useTheme'
import { Sun, Moon } from 'lucide-react'

export default function ThemeToggle({ className = '' }: { className?: string }) {
  const { theme, setTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={
        'inline-flex items-center gap-2 rounded-md border px-2 py-1.5 text-xs transition-colors ' +
        'bg-zinc-100 text-zinc-800 border-zinc-300 ' +
        'dark:bg-zinc-800 dark:text-zinc-200 dark:border-zinc-600 ' +
        'hover:bg-zinc-200 dark:hover:bg-zinc-700 ' +
        className
      }
    >
      {isDark ? (
        <Sun className="h-3.5 w-3.5" />
      ) : (
        <Moon className="h-3.5 w-3.5" />
      )}
      <span className="leading-none">{isDark ? 'Light' : 'Dark'}</span>
    </button>
  )
}
