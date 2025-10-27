/**
 * Thread Viewer Types
 * Shared types for the unified message/thread detail viewer component
 */

export interface ThreadMessage {
  id: string;
  from: string;
  to: string[];
  date: string;
  snippet?: string;
  body_html?: string;
  body_text?: string;
}

// Thread-level risk/analysis returned by security/agent backend
export interface ThreadRiskAnalysis {
  summary: string; // short human-readable verdict from the agent
  factors: string[]; // bullet-point reasons / signals
  riskLevel: "low" | "medium" | "high" | "critical";
  recommendedAction?: string; // e.g. "Quarantine" / "Reply" / "Ignore"
}

export interface ThreadData {
  message_id: string;
  thread_id?: string;
  subject: string;
  from_name: string;
  from_email: string;
  to_email: string;
  received_at: string;
  category?: string;
  categories?: string[];
  risk_score?: number;
  quarantined?: boolean;
  archived?: boolean;
  muted?: boolean;
  user_overrode_safe?: boolean;
  reply_status?: 'replied' | 'not_replied';
  html_body?: string;
  text_body?: string;
  messages?: ThreadMessage[]; // For multi-message threads
  analysis?: ThreadRiskAnalysis; // Agent-backed risk analysis
}
