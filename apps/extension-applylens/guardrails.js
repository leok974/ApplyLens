// guardrails.js - Phase 3.1: Content sanitization for generated answers
// Strips URLs and forbidden phrases from AI-generated content

/**
 * Sanitizes generated content by removing URLs and forbidden phrases
 * @param {string} text - The generated text to sanitize
 * @returns {string} - Sanitized text
 */
export function sanitizeGeneratedContent(text) {
  if (!text) return text;

  let sanitized = text;

  // Strip URLs (http:// and https://)
  sanitized = sanitized.replace(/https?:\/\/[^\s]+/gi, '');

  // Remove forbidden phrase: "I worked at"
  sanitized = sanitized.replace(/I worked at\s+/gi, '');

  // Clean up extra whitespace that might be left after removal
  sanitized = sanitized.replace(/\s+/g, ' ').trim();

  return sanitized;
}
