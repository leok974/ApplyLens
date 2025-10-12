import * as React from "react";
import { cn } from "@/lib/utils";

export function Segmented<T extends string>({
  value, onChange, options, className,
}: {
  value: T; onChange: (v: T) => void;
  options: { value: T; label: string }[];
  className?: string;
}) {
  return (
    <div className={cn(
      "inline-flex rounded-lg border border-[color:hsl(var(--color-border))] bg-card p-0.5",
      className
    )}>
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            "px-2.5 py-1 text-xs font-medium transition",
            value === o.value
              ? "rounded-md bg-[color:hsl(var(--color-muted))] text-slate-900 dark:text-slate-100"
              : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
