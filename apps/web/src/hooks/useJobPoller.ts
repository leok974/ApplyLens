/**
 * useJobPoller - Poll async job status with exponential backoff
 *
 * Usage:
 *   const [jobId, setJobId] = useState<string | undefined>()
 *   const status = useJobPoller(jobId)
 *
 *   if (status?.state === 'done') {
 *     toast.success(`Synced ${status.inserted} emails!`)
 *   }
 */

import { useEffect, useState } from 'react'
import { apiUrl } from '@/lib/apiUrl'

export type JobStatus = {
  job_id: string
  state: 'queued' | 'running' | 'done' | 'error' | 'canceled'
  processed: number
  total: number | null
  error: string | null
  inserted: number | null
  started_at?: number  // Unix timestamp when job started
  completed_at?: number  // Unix timestamp when job completed
}

export function useJobPoller(jobId?: string): JobStatus | null {
  const [status, setStatus] = useState<JobStatus | null>(null)

  useEffect(() => {
    if (!jobId) {
      setStatus(null)
      return
    }

    let stopped = false
    let interval = 1500 // Start at 1.5s

    async function tick() {
      if (!jobId) return // Safety check

      try {
        const url = apiUrl(`/api/gmail/backfill/status?job_id=${encodeURIComponent(jobId)}`)
        const res = await fetch(url, { credentials: 'include' })

        if (!res.ok) {
          console.error('[useJobPoller] Failed to fetch status:', res.status)
          return
        }

        const s: JobStatus = await res.json()
        setStatus(s)

        // Stop polling if in terminal state
        if (['done', 'error', 'canceled'].includes(s.state)) {
          console.info(`[useJobPoller] Job ${jobId} reached terminal state: ${s.state}`)
          return
        }

        // Not found state also stops polling
        if (s.error?.includes('not found')) {
          console.warn(`[useJobPoller] Job ${jobId} not found`)
          return
        }

      } catch (error) {
        console.error('[useJobPoller] Error fetching status:', error)
      }

      // Schedule next tick with exponential backoff (max 10s)
      if (!stopped) {
        const nextInterval = Math.min(interval * 1.5, 10000)
        setTimeout(tick, nextInterval)
        interval = nextInterval
      }
    }

    // Start polling immediately
    tick()

    // Cleanup on unmount or jobId change
    return () => {
      stopped = true
    }
  }, [jobId])

  return status
}
