/**
 * Feature Flags for Phase 4 AI Features
 *
 * These flags control the visibility of AI-powered features in the UI.
 * Set corresponding VITE_FEATURE_* environment variables to '1' to enable.
 */

export const FLAGS = {
  /**
   * Email thread summarization with Ollama
   * Enables the "Summarize" button in email detail views
   */
  SUMMARIZE: import.meta.env.VITE_FEATURE_SUMMARIZE === '1',

  /**
   * Smart risk badge with security scoring
   * Shows color-coded risk badges on emails with expandable details
   */
  RISK_BADGE: import.meta.env.VITE_FEATURE_RISK_BADGE === '1',

  /**
   * RAG-powered semantic search
   * Enables "Ask your inbox" search functionality
   */
  RAG_SEARCH: import.meta.env.VITE_FEATURE_RAG_SEARCH === '1',

  /**
   * Demo mode with seeded data
   * Shows demo indicators and may use sample data
   */
  DEMO_MODE: import.meta.env.VITE_DEMO_MODE === '1',

  /**
   * Browser Companion extension
   * Shows navigation link to extension landing page and settings
   */
  COMPANION: import.meta.env.VITE_FEATURE_COMPANION === '1',

  /**
   * Agent v2 - Structured LLM answering with citations
   * Uses new /api/v2/agent/run endpoint with tool-based architecture
   */
  CHAT_AGENT_V2: import.meta.env.VITE_CHAT_AGENT_V2 === '1',
};

/**
 * Check if any AI features are enabled
 */
export const hasAnyAIFeatures = (): boolean => {
  return FLAGS.SUMMARIZE || FLAGS.RISK_BADGE || FLAGS.RAG_SEARCH || FLAGS.CHAT_AGENT_V2;
};

/**
 * Get list of enabled feature names
 */
export const getEnabledFeatures = (): string[] => {
  const features: string[] = [];
  if (FLAGS.SUMMARIZE) features.push('Summarize');
  if (FLAGS.RISK_BADGE) features.push('Risk Badge');
  if (FLAGS.RAG_SEARCH) features.push('RAG Search');
  if (FLAGS.DEMO_MODE) features.push('Demo Mode');
  if (FLAGS.COMPANION) features.push('Companion');
  if (FLAGS.CHAT_AGENT_V2) features.push('Chat Agent V2');
  return features;
};
