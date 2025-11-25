import { useState, useCallback } from 'react';
import { generateFollowupDraft } from '../lib/api';
import { toast } from 'sonner';
import { track } from '../lib/analytics';

export interface FollowupDraft {
  subject: string;
  body: string;
}

export interface FollowupDraftOptions {
  threadId: string;
  applicationId?: number;
}

/**
 * Hook for generating follow-up email drafts using Agent V2
 *
 * Usage:
 * ```tsx
 * const { draft, isGenerating, generateDraft, clearDraft } = useFollowupDraft();
 *
 * // Generate draft
 * await generateDraft({ threadId: 'abc123', applicationId: 42 });
 *
 * // Copy to clipboard
 * if (draft) {
 *   await navigator.clipboard.writeText(draft.body);
 * }
 * ```
 */
export function useFollowupDraft() {
  const [draft, setDraft] = useState<FollowupDraft | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateDraft = useCallback(async (options: FollowupDraftOptions) => {
    setIsGenerating(true);
    setError(null);

    try {
      const result = await generateFollowupDraft({
        thread_id: options.threadId,
        application_id: options.applicationId,
      });

      if (result.status === 'error') {
        const errorMsg = result.message || 'Failed to generate draft';
        setError(errorMsg);
        toast.error('Draft generation failed', {
          description: errorMsg,
        });
        track({ name: 'followup_draft_error', thread_id: options.threadId });
        return null;
      }

      if (!result.draft) {
        setError('No draft generated');
        toast.error('No draft generated');
        return null;
      }

      setDraft(result.draft);
      toast.success('✨ Draft generated', {
        description: 'Your follow-up email is ready',
      });

      track({
        name: 'followup_draft_generated',
        thread_id: options.threadId,
        has_application: !!options.applicationId,
      });

      return result.draft;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      toast.error('Draft generation failed', {
        description: errorMsg,
      });
      track({ name: 'followup_draft_error', thread_id: options.threadId, error: errorMsg });
      return null;
    } finally {
      setIsGenerating(false);
    }
  }, []);

  const clearDraft = useCallback(() => {
    setDraft(null);
    setError(null);
  }, []);

  const copyDraftToClipboard = useCallback(async () => {
    if (!draft) return false;

    try {
      const fullText = `Subject: ${draft.subject}\n\n${draft.body}`;
      await navigator.clipboard.writeText(fullText);
      toast.success('📋 Copied to clipboard');
      track({ name: 'followup_draft_copied' });
      return true;
    } catch (err) {
      toast.error('Failed to copy to clipboard');
      return false;
    }
  }, [draft]);

  const copyBodyToClipboard = useCallback(async () => {
    if (!draft) return false;

    try {
      await navigator.clipboard.writeText(draft.body);
      toast.success('📋 Body copied to clipboard');
      track({ name: 'followup_draft_body_copied' });
      return true;
    } catch (err) {
      toast.error('Failed to copy to clipboard');
      return false;
    }
  }, [draft]);

  return {
    draft,
    isGenerating,
    error,
    generateDraft,
    clearDraft,
    copyDraftToClipboard,
    copyBodyToClipboard,
  };
}
