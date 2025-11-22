/**
 * Agent UI Utilities
 *
 * Helper functions for mapping Agent V2 API responses to UI-friendly formats.
 */

import type { AgentCard } from '@/types/agent';

/**
 * Map agent result to cards array.
 *
 * This is a simple pass-through for now since the API already returns
 * properly structured AgentCard objects. Future enhancements could add:
 * - Client-side card filtering
 * - Card metadata enrichment
 * - Default card generation for missing data
 */
export function mapAgentResultToCards(agentResult: {
  status: string;
  intent?: string;
  cards?: AgentCard[];
  metrics?: Record<string, any>;
}): AgentCard[] {
  return agentResult.cards ?? [];
}
