/**
 * Chat API client for mailbox assistant.
 */

import { API_BASE } from './apiBase'

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export interface ChatRequest {
  messages: Message[]
  filters?: {
    category?: string
    risk_min?: number
    risk_max?: number
    sender_domain?: string
    date_from?: string
    date_to?: string
    labels?: string[]
  }
  max_results?: number
}

export interface Citation {
  id: string
  subject: string
  sender?: string
  received_at?: string
  category?: string
  risk_score?: number
}

export interface ActionItem {
  action: string
  email_id: string
  params: Record<string, any>
}

export interface ChatResponse {
  intent: string
  intent_explanation: string
  answer: string
  actions: ActionItem[]
  citations: Citation[]
  search_stats: {
    total_results: number
    returned_results: number
    query: string
    filters: Record<string, any>
  }
}

export interface Intent {
  patterns: string[]
  description: string
}

/**
 * Send a chat message and get a response.
 */
export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `Chat failed: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Get list of available intents with descriptions.
 */
export async function listIntents(): Promise<Record<string, Intent>> {
  const response = await fetch(`${API_BASE}/chat/intents`)

  if (!response.ok) {
    throw new Error(`Failed to fetch intents: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Health check for chat service.
 */
export async function chatHealth(): Promise<{ status: string; service: string }> {
  const response = await fetch(`${API_BASE}/chat/health`)

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`)
  }

  return response.json()
}
