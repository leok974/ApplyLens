import { sortLabelsByImpact, labelTitle } from "../lib/searchScoring";

type Props = { labels?: string[]; className?: string };

export default function EmailLabels({ labels = [], className }: Props) {
  const ordered = sortLabelsByImpact(labels);
  if (!ordered.length) return null;
  return (
    <div className={className ?? "flex flex-wrap gap-1"}>
      {ordered.map((l: string) => (
        <span
          key={l}
          title={labelTitle(l)}
          className={
            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset " +
            (l === "offer"
              ? "bg-yellow-100 ring-yellow-300"
              : l === "interview"
              ? "bg-green-100 ring-green-300"
              : l === "rejection"
              ? "bg-gray-100 ring-gray-300 opacity-80"
              : "bg-blue-50 ring-blue-200")
          }
        >
          {labelTitle(l)}
        </span>
      ))}
    </div>
  );
}
