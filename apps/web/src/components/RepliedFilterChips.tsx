import { cn } from "@/lib/utils";

type Value = "all" | "true" | "false";

export function RepliedFilterChips({
  value = "all",
  onChange,
}: {
  value?: Value;
  onChange: (v: Value) => void;
}) {
  const opts: { key: Value; label: string }[] = [
    { key: "all", label: "All" },
    { key: "true", label: "Replied" },
    { key: "false", label: "Not replied" },
  ];
  return (
    <div className="flex items-center gap-1">
      {opts.map(({ key, label }) => {
        const active = value === key;
        return (
          <button
            key={key}
            type="button"
            onClick={() => onChange(key)}
            data-testid={`filter-replied-${key}`}
            className={cn(
              "filter-pill",
              active && "filter-pill-active"
            )}
            title={label}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
