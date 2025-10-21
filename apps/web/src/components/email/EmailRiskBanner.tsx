import * as React from "react";
import { AlertTriangle, ShieldAlert, CheckCircle2, Mail } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export type EmailRiskAdvice = {
  suspicious: boolean;
  suspicion_score: number;
  explanations: string[];
  suggested_actions: string[];
  verify_checks: string[];
};

type EmailRiskBannerProps = {
  emailId: string;
  riskAdvice: EmailRiskAdvice;
  onMarkScam?: () => void;
  onRequestOfficial?: () => void;
  onDismiss?: () => void;
};

export function EmailRiskBanner({
  emailId,
  riskAdvice,
  onMarkScam,
  onRequestOfficial,
  onDismiss,
}: EmailRiskBannerProps) {
  const { suspicious, suspicion_score, explanations, suggested_actions, verify_checks } = riskAdvice;

  // Determine banner color based on risk level
  const isHighRisk = suspicious;
  const isWarn = !suspicious && suspicion_score >= 25;
  const isOk = !isHighRisk && !isWarn;

  if (isOk) {
    // No banner for low-risk emails
    return null;
  }

  const bannerClass = cn(
    "border-l-4 p-4 space-y-3",
    isHighRisk
      ? "bg-red-50 border-red-500 dark:bg-red-950/20 dark:border-red-600"
      : "bg-yellow-50 border-yellow-500 dark:bg-yellow-950/20 dark:border-yellow-600"
  );

  const titleClass = cn(
    "flex items-center gap-2 font-semibold text-sm",
    isHighRisk ? "text-red-700 dark:text-red-400" : "text-yellow-700 dark:text-yellow-400"
  );

  const Icon = isHighRisk ? ShieldAlert : AlertTriangle;

  return (
    <Card className={bannerClass} data-testid="email-risk-banner">
      {/* Header */}
      <div className={titleClass}>
        <Icon className="h-5 w-5" />
        <span>
          {isHighRisk
            ? `This email looks suspicious (score: ${suspicion_score})`
            : `Some risk indicators found (score: ${suspicion_score})`}
        </span>
      </div>

      {/* Why it's suspicious */}
      {explanations.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs font-medium text-slate-700 dark:text-slate-300">
            Why it's flagged:
          </div>
          <ul className="ml-4 list-disc space-y-0.5 text-xs text-slate-600 dark:text-slate-400">
            {explanations.map((reason, i) => (
              <li key={i}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      <Separator className="bg-slate-200 dark:bg-slate-700" />

      {/* What you should do */}
      {suggested_actions.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs font-medium text-slate-700 dark:text-slate-300">
            What you should do:
          </div>
          <ul className="ml-4 list-disc space-y-0.5 text-xs text-slate-600 dark:text-slate-400">
            {suggested_actions.map((action, i) => (
              <li key={i}>{action}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Verify/double-check */}
      {verify_checks.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs font-medium text-slate-700 dark:text-slate-300">
            Verify with sender:
          </div>
          <ul className="ml-4 list-disc space-y-0.5 text-xs text-slate-600 dark:text-slate-400">
            {verify_checks.map((check, i) => (
              <li key={i}>{check}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2 pt-2">
        {onMarkScam && (
          <Button
            variant="destructive"
            size="sm"
            onClick={onMarkScam}
            className="text-xs"
          >
            <ShieldAlert className="mr-1 h-3.5 w-3.5" />
            Mark as Scam
          </Button>
        )}
        {onRequestOfficial && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRequestOfficial}
            className="text-xs"
          >
            <Mail className="mr-1 h-3.5 w-3.5" />
            Request Official Invite
          </Button>
        )}
        {onDismiss && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onDismiss}
            className="text-xs text-slate-500"
          >
            <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
            Dismiss
          </Button>
        )}
      </div>
    </Card>
  );
}

/**
 * Fetch risk advice from API
 */
export async function fetchEmailRiskAdvice(emailId: string): Promise<EmailRiskAdvice | null> {
  try {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const response = await fetch(`${API_BASE}/emails/${emailId}/risk-advice`);

    if (!response.ok) {
      if (response.status === 404) {
        // Email not found in ES
        return null;
      }
      throw new Error(`Failed to fetch risk advice: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching email risk advice:", error);
    return null;
  }
}

/**
 * Generate prefilled verification email template
 */
export function generateVerificationEmailDraft(recruiterName: string = "Recruiter", userName: string = "[Your Name]"): string {
  return `Subject: Verification before scheduling

Hi ${recruiterName},

Thanks for reaching out. Before we proceed, could you please:
1) Share the public job posting link on your official careers site, and
2) Send a calendar invite from your corporate domain (e.g., @prometric.com) with a meeting link?

This helps me verify details and prepare properly.

Best regards,
${userName}`;
}
