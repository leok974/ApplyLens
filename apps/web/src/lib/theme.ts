// apps/web/src/lib/theme.ts
type Theme = 'light' | 'dark';

const STORAGE_KEY = 'ui:theme';

export function getStoredTheme(): Theme | null {
  const t = localStorage.getItem(STORAGE_KEY);
  return t === 'light' || t === 'dark' ? t : null;
}

export function getSystemTheme(): Theme {
  return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === 'dark') root.classList.add('dark');
  else root.classList.remove('dark');
  localStorage.setItem(STORAGE_KEY, theme);
}

export function initTheme() {
  const theme = getStoredTheme() ?? getSystemTheme();
  applyTheme(theme);

  // keep in sync if user changes OS setting while app is open
  const mq = matchMedia('(prefers-color-scheme: dark)');
  const onChange = () => {
    if (!getStoredTheme()) applyTheme(getSystemTheme());
  };
  mq.addEventListener?.('change', onChange);
}

export function toggleTheme() {
  const rootIsDark = document.documentElement.classList.contains('dark');
  applyTheme(rootIsDark ? 'light' : 'dark');
}
