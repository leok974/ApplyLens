/**
 * Chat API client for mailbox assistant.
 */

import { API_BASE } from './apiBase'

/**
 * Retry fetch with exponential backoff for rate limits and network errors
 */
async function withBackoff<T>(fn: () => Promise<T>, maxRetries = 3): Promise<T> {
  let delay = 300
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn()
    } catch (e: any) {
      const shouldRetry = 
        e?.status === 429 || 
        e?.name === 'FetchError' ||
        e?.name === 'TypeError' // Network errors
      
      if (shouldRetry && attempt < maxRetries - 1) {
        console.log(`[Backoff] Retry ${attempt + 1}/${maxRetries} after ${delay}ms`)
        await new Promise(r => setTimeout(r, delay))
        delay = Math.min(delay * 2, 2000) // Cap at 2s
        continue
      }
      throw e
    }
  }
  return fn() // Final attempt without catch
}

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
  window_days?: number
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
    took_ms?: number  // ES timing
  }
  timing?: {
    es_ms?: number
    llm_ms?: number
  }
}

export interface Intent {
  patterns: string[]
  description: string
}

/**
 * Send a chat message and get a response.
 * Automatically retries with backoff on rate limits or network errors.
 */
export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  return withBackoff(async () => {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      const err: any = new Error(error.detail || `Chat failed: ${response.statusText}`)
      err.status = response.status // Preserve status for backoff logic
      throw err
    }

    return response.json()
  })
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
