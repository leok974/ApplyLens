import { FileText, AlertTriangle } from "lucide-react";

type ResumeStatusPillProps = {
  resumeUploadedAt?: string | null;
  skillsCount?: number;
  rolesCount?: number;
};

export function ResumeStatusPill({
  resumeUploadedAt,
  skillsCount = 0,
  rolesCount = 0,
}: ResumeStatusPillProps) {
  const hasResume =
    !!resumeUploadedAt || (skillsCount ?? 0) > 0 || (rolesCount ?? 0) > 0;

  const parsedDate =
    resumeUploadedAt && !Number.isNaN(Date.parse(resumeUploadedAt))
      ? new Date(resumeUploadedAt)
      : null;

  const dateLabel = parsedDate
    ? parsedDate.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;

  if (!hasResume) {
    return (
      <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-50">
        <AlertTriangle className="h-3 w-3 shrink-0" />
        <span className="flex flex-col sm:flex-row sm:items-center sm:gap-1">
          <span className="font-medium">Resume:</span>
          <span className="text-amber-100/90">Not uploaded yet</span>
        </span>
      </div>
    );
  }

  return (
    <div
      className="inline-flex items-center gap-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-50"
      title="This is what the ApplyLens Companion uses to prefill job applications."
    >
      <FileText className="h-3 w-3 shrink-0" />
      <span className="flex flex-col sm:flex-row sm:items-center sm:gap-1">
        <span className="font-medium">Resume:</span>
        <span className="text-emerald-50/90">
          Parsed
          {dateLabel ? ` ${dateLabel}` : ""}
          {" · "}
          {skillsCount} skills
          {" · "}
          {rolesCount} roles
        </span>
      </span>
    </div>
  );
}
