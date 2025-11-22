/**
 * Agent v2 - TypeScript types
 *
 * Mirrors backend Pydantic schemas for type-safe frontend integration.
 */

import type { MailThreadSummary } from '@/lib/mailThreads';

// ============================================================================
// Agent Run Contract
// ============================================================================

export type AgentMode = 'preview_only' | 'apply_actions';

export type AgentStatus = 'running' | 'done' | 'error';

export interface AgentContext {
  time_window_days: number;
  filters: Record<string, any>;
  session_id?: string;
}

export interface ToolResult {
  tool_name: string;
  status: 'success' | 'error' | 'timeout';
  summary: string;
  data: Record<string, any>;
  duration_ms: number;
  error_message?: string;
}

export type AgentCardKind =
  | 'suspicious_summary'
  | 'bills_summary'
  | 'followups_summary'
  | 'interviews_summary'
  | 'generic_summary'
  | 'thread_list'
  | 'error';

export interface AgentCard {
  kind: AgentCardKind;
  title: string;
  body: string;
  email_ids: string[];
  meta: Record<string, any>;
  threads?: MailThreadSummary[]; // For thread_list cards
  intent?: string; // For thread_list cards - e.g. "followups", "suspicious", etc.
}

export interface AgentMetrics {
  emails_scanned: number;
  tool_calls: number;
  rag_sources: number;
  duration_ms: number;
  redis_hits?: number;
  redis_misses?: number;
  llm_used?: string;
}

export interface AgentRunRequest {
  query: string;
  mode?: AgentMode;
  context?: AgentContext;
  user_id: string;
}

export interface AgentRunResponse {
  run_id: string;
  user_id: string;
  query: string;
  mode: string;
  context: AgentContext;

  // Results
  status: AgentStatus;
  intent?: string;  // Classified intent: suspicious, bills, interviews, followups, profile, generic
  answer: string;
  cards: AgentCard[];
  tools_used: string[];
  metrics: AgentMetrics;

  // Metadata
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

// ============================================================================
// Tool Schemas
// ============================================================================

export interface EmailSearchParams {
  query_text: string;
  time_window_days?: number;
  labels?: string[];
  risk_min?: number;
  max_results?: number;
}

export interface SecurityScanParams {
  email_ids: string[];
  force_rescan?: boolean;
}

export interface ThreadDetailParams {
  thread_id: string;
  include_body?: boolean;
}

// ============================================================================
// Tool Results
// ============================================================================

export interface EmailSearchResult {
  emails: any[];
  total_found: number;
  query_used: string;
  filters_applied: Record<string, any>;
}

export interface SecurityScanResult {
  scanned_count: number;
  risky_emails: any[];
  safe_emails: any[];
  domains_checked: string[];
}

// ============================================================================
// Cache Schemas
// ============================================================================

export interface DomainRiskCache {
  domain: string;
  risk_score: number;
  first_seen_at: string;
  last_seen_at: string;
  email_count: number;
  flags: string[];
  evidence: Record<string, any>;
}

export interface ChatSessionCache {
  user_id: string;
  session_id: string;
  last_query: string;
  last_intent?: string;
  pinned_thread_ids: string[];
  last_time_window: number;
  updated_at: string;
}

// ============================================================================
// API Responses
// ============================================================================

export interface ToolsListResponse {
  total_tools: number;
  tools: Record<string, {
    name: string;
    description: string;
    parameters: string[];
  }>;
}

export interface AgentHealthResponse {
  status: 'ok' | 'degraded' | 'error';
  orchestrator: string;
  components: {
    redis?: {
      status: 'ok' | 'error';
      latency_ms?: number;
      error?: string;
    };
    elasticsearch?: {
      status: 'ok' | 'error';
      error?: string;
    };
  };
}
