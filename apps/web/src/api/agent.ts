/**
 * Agent v2 - API Client
 *
 * Type-safe client for mailbox agent endpoints.
 */

import { apiFetch } from '@/lib/apiBase';
import type {
  AgentRunRequest,
  AgentRunResponse,
  ToolsListResponse,
  AgentHealthResponse,
} from '../types/agent';

/**
 * Execute a mailbox agent run.
 *
 * @example
 * ```ts
 * const response = await runMailboxAgent({
 *   query: "Show suspicious emails from new domains this week",
 *   mode: "preview_only",
 *   context: {
 *     time_window_days: 7,
 *     filters: { labels: ["INBOX"], risk_min: 80 }
 *   },
 *   user_id: "user@gmail.com"
 * });
 * ```
 */
export async function runMailboxAgent(
  request: AgentRunRequest
): Promise<AgentRunResponse> {
  const response = await apiFetch('/agent/mailbox/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Agent run failed' }));
    throw new Error(error.detail || 'Failed to execute agent run');
  }

  return response.json();
}

/**
 * Get agent run by ID.
 *
 * Note: Not implemented yet - runs are not persisted.
 */
export async function getAgentRun(runId: string): Promise<AgentRunResponse> {
  const response = await apiFetch(`/agent/mailbox/run/${runId}`);

  if (!response.ok) {
    throw new Error('Run not found or history not available');
  }

  return response.json();
}

/**
 * List available tools for the agent.
 *
 * Returns tool metadata for UI/debugging.
 */
export async function listAgentTools(): Promise<ToolsListResponse> {
  const response = await apiFetch('/agent/tools');

  if (!response.ok) {
    throw new Error('Failed to list agent tools');
  }

  return response.json();
}

/**
 * Check agent subsystem health.
 *
 * Checks Redis, ES, LLM connectivity.
 */
export async function getAgentHealth(): Promise<AgentHealthResponse> {
  const response = await apiFetch('/agent/health');

  if (!response.ok) {
    throw new Error('Failed to check agent health');
  }

  return response.json();
}

/**
 * Helper: Build agent request from chat query.
 *
 * Extracts context from current page state and builds proper request.
 */
export function buildAgentRequest(
  query: string,
  userId: string,
  options?: {
    mode?: 'preview_only' | 'apply_actions';
    timeWindowDays?: number;
    filters?: Record<string, any>;
    sessionId?: string;
  }
): AgentRunRequest {
  return {
    query,
    user_id: userId,
    mode: options?.mode || 'preview_only',
    context: {
      time_window_days: options?.timeWindowDays || 30,
      filters: options?.filters || {},
      session_id: options?.sessionId,
    },
  };
}
