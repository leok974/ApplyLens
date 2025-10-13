export function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="rounded border border-[color:hsl(var(--color-border))] bg-[color:hsl(var(--color-muted))] px-1.5 py-0.5 text-[11px] font-medium text-slate-700 shadow-sm dark:text-slate-200">
      {children}
    </kbd>
  );
}
