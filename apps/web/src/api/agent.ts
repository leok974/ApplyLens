/**
 * Agent v2 - API Client
 *
 * Type-safe client for mailbox agent endpoints.
 * Supports both v1 (/agent/mailbox/run) and v2 (/api/v2/agent/run) endpoints.
 */

import { apiFetch } from '@/lib/apiBase';
import { FLAGS } from '@/lib/flags';
import type {
  AgentRunResponse,
  ToolsListResponse,
  AgentHealthResponse,
} from '../types/agent';

export interface RunAgentOptions {
  timeWindowDays?: number;
  filters?: Record<string, unknown>;
}

/**
 * Execute a mailbox agent run.
 *
 * Uses Agent v2 (/api/v2/agent/run) if CHAT_AGENT_V2 flag is enabled,
 * otherwise falls back to v1 (/agent/mailbox/run).
 *
 * @example
 * ```ts
 * const response = await runMailboxAgent(
 *   "Show suspicious emails from new domains this week",
 *   { timeWindowDays: 7 }
 * );
 * ```
 */
export async function runMailboxAgent(
  query: string,
  options?: RunAgentOptions
): Promise<AgentRunResponse> {
  const body = {
    run_id: crypto.randomUUID(),
    user_id: undefined, // Backend derives user from session
    query,
    mode: 'preview_only' as const,
    context: {
      time_window_days: options?.timeWindowDays ?? 30,
      filters: options?.filters ?? {},
    },
  };

  // Use v2 endpoint if flag is enabled, otherwise v1
  const endpoint = FLAGS.CHAT_AGENT_V2
    ? '/v2/agent/run'  // Agent v2 with structured LLM answering
    : '/agent/mailbox/run';  // Legacy v1 endpoint

  const response = await apiFetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
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
