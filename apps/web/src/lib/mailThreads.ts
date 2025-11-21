/**
 * Mail thread types for Thread Viewer v1
 */

export interface MailThreadSummary {
  threadId: string;
  subject: string;
  from: string;
  to?: string;
  lastMessageAt: string; // ISO 8601
  unreadCount?: number;
  riskScore?: number;
  labels: string[];
  snippet: string;
  gmailUrl: string;
}

export interface MailMessage {
  id: string;
  sentAt: string;
  from: string;
  to: string;
  subject: string;
  bodyHtml?: string;
  bodyText?: string;
  isImportant?: boolean;
}

export interface MailThreadDetail extends MailThreadSummary {
  messages: MailMessage[];
}

export interface AgentThreadResult {
  type: 'thread_list';
  intent: 'followups' | 'suspicious' | 'bills' | 'interviews' | string;
  title: string; // e.g. "People you still owe a reply"
  description?: string;
  threads: MailThreadSummary[];
}
