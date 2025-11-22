/**
 * Tracker Filters
 *
 * Helper functions for filtering tracker applications
 */

import { AppOut, AppStatus } from './api'

/**
 * Early-stage application statuses that typically need follow-up
 */
export const EARLY_STAGE_STATUSES: AppStatus[] = ['applied', 'hr_screen', 'interview']

/**
 * Determine if an application likely needs follow-up
 *
 * Heuristic: Application has an email thread AND is in an early stage
 * (applied, hr_screen, or interview).
 *
 * This is a client-side approximation. The backend agent's followups
 * intent may use more sophisticated logic based on message direction
 * and timestamps.
 *
 * @param app Application to check
 * @returns true if application likely needs follow-up
 */
export function needsFollowup(app: AppOut): boolean {
  if (!app.thread_id) return false
  return EARLY_STAGE_STATUSES.includes(app.status)
}

/**
 * Check if an application is linked to a mailbox thread
 *
 * @param app Application to check
 * @returns true if application has a thread_id
 */
export function isFromMailbox(app: AppOut): boolean {
  return !!app.thread_id
}

/**
 * Apply filters to a list of applications
 *
 * @param applications List of applications to filter
 * @param filters Filter options
 * @returns Filtered list of applications
 */
export function applyTrackerFilters(
  applications: AppOut[],
  filters: {
    fromMailbox?: boolean
    needsFollowup?: boolean
  }
): AppOut[] {
  let filtered = applications

  if (filters.fromMailbox) {
    filtered = filtered.filter(isFromMailbox)
  }

  if (filters.needsFollowup) {
    filtered = filtered.filter(needsFollowup)
  }

  return filtered
}
