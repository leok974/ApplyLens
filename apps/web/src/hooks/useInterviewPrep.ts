/**
 * useInterviewPrep hook
 *
 * Manages state for loading interview preparation materials.
 */

import { useState, useCallback } from 'react';
import { getInterviewPrep, type InterviewPrepResponse } from '@/api/agent';

export function useInterviewPrep() {
  const [data, setData] = useState<InterviewPrepResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadPrep = useCallback(
    async (applicationId: number, threadId?: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await getInterviewPrep({ applicationId, threadId });
        setData(res);
      } catch (e: unknown) {
        setError(e instanceof Error ? e : new Error(String(e)));
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return { data, isLoading, error, loadPrep, reset };
}
