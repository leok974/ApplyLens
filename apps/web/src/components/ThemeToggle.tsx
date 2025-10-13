import { useEffect, useState } from 'react';
import { toggleTheme, initTheme } from '../lib/theme';

export default function ThemeToggle({ className = '' }: { className?: string }) {
  const [isDark, setIsDark] = useState<boolean>(() =>
    typeof document !== 'undefined' ? document.documentElement.classList.contains('dark') : true
  );

  useEffect(() => {
    // Ensure theme is initialized once on mount (safe if called multiple times)
    initTheme();
    setIsDark(document.documentElement.classList.contains('dark'));
  }, []);

  const onClick = () => {
    toggleTheme();
    setIsDark(document.documentElement.classList.contains('dark'));
  };

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Light mode' : 'Dark mode'}
      className={
        'inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm transition-colors ' +
        'border-[var(--border)] bg-[var(--elev-1)] hover:bg-[var(--elev-2)] ' + className
      }
    >
      {/* simple, dependency-free icons */}
      <span aria-hidden="true">
        {isDark ? '☀️' : '🌙'}
      </span>
      <span>{isDark ? 'Light' : 'Dark'}</span>
    </button>
  );
}
