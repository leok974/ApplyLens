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
            onClick={() => onChange(key)}
            className={
              "inline-flex items-center rounded-full px-2 py-0.5 text-xs ring-1 transition " +
              (active ? "bg-blue-200 ring-blue-300" : "bg-blue-100 ring-blue-200")
            }
            title={label}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
