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
}
