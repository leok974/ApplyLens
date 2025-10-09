export function DateRangeControls({
  from,
  to,
  onChange,
}: {
  from?: string;
  to?: string;
  onChange: (next: { from?: string; to?: string }) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-xs">
        From:&nbsp;
        <input
          type="date"
          value={from?.slice(0, 10) || ""}
          onChange={(e) => onChange({ from: e.target.value || undefined, to })}
          className="rounded border px-2 py-1 text-xs"
        />
      </label>
      <label className="text-xs">
        To:&nbsp;
        <input
          type="date"
          value={to?.slice(0, 10) || ""}
          onChange={(e) => onChange({ from, to: e.target.value || undefined })}
          className="rounded border px-2 py-1 text-xs"
        />
      </label>
      {(from || to) && (
        <button
          onClick={() => onChange({ from: undefined, to: undefined })}
          className="text-xs text-muted-foreground underline"
        >
          Clear dates
        </button>
      )}
    </div>
  );
}
