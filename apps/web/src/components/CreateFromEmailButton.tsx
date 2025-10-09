import { useState } from 'react'

interface CreateFromEmailButtonProps {
  threadId: string;
  company?: string;
  role?: string;
  snippet?: string;
  sender?: string;
  subject?: string;
  bodyText?: string;
  headers?: Record<string, string>;
  source?: string;
  onPrefill?: (prefill: { company?: string; role?: string; source?: string }) => void;
  onCreated?: () => void;
  showToast?: (message: string, variant?: 'default' | 'success' | 'warning' | 'error' | 'info') => void;
}

export default function CreateFromEmailButton({
  threadId,
  company,
  role,
  snippet: _snippet, // Reserved for future use
  sender,
  subject,
  bodyText,
  headers,
  source,
  onPrefill,
  onCreated,
  showToast,
}: CreateFromEmailButtonProps) {
  const [extracting, setExtracting] = useState(false)
  const [creating, setCreating] = useState(false)

  // Extract suggested fields from email content
  async function extract() {
    setExtracting(true)
    try {
      const payload: any = {
        gmail_thread_id: threadId, // Backend will fetch from Gmail if configured
      };
      
      // Include email content as fallback if Gmail not configured
      if (subject) payload.subject = subject;
      if (sender) payload.from = sender;
      if (headers) payload.headers = headers;
      if (bodyText) payload.text = bodyText;
      
      const r = await fetch("/api/applications/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (r.ok) {
        const extracted = await r.json();
        return extracted;
      } else {
        console.error('Failed to extract:', r.status, await r.text())
        showToast?.('Could not extract application details from email', 'error')
        return null;
      }
    } catch (error) {
      console.error('Failed to extract:', error)
      showToast?.('Could not extract application details from email', 'error')
      return null;
    } finally {
      setExtracting(false)
    }
  }

  // Backfill application using extracted data
  async function backfill() {
    setCreating(true)
    try {
      const payload: any = {
        gmail_thread_id: threadId, // Backend will fetch from Gmail if configured
        thread_id: threadId, // Legacy field for non-Gmail usage
      };
      
      // Include email content as fallback if Gmail not configured
      if (subject) payload.subject = subject;
      if (sender) payload.from = sender;
      if (headers) payload.headers = headers;
      if (bodyText) payload.text = bodyText;
      
      const r = await fetch("/api/applications/backfill-from-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (r.ok) {
        const result = await r.json();
        showToast?.(`Application created: ${result.saved.company || 'Unknown'} - ${result.saved.role || 'Unknown'}`, 'success')
        onCreated?.();
      } else {
        console.error('Failed to backfill:', r.status, await r.text())
        showToast?.('Could not create application from email', 'error')
      }
    } catch (error) {
      console.error('Failed to backfill:', error)
      showToast?.('Could not create application from email', 'error')
    } finally {
      setCreating(false)
    }
  }

  // Prefill only - extract and pass to dialog
  async function handlePrefill() {
    const extracted = await extract();
    if (extracted && onPrefill) {
      onPrefill({
        company: extracted.company || company,
        role: extracted.role || role,
        source: extracted.source || source,
      });
      showToast?.(`Extracted: ${extracted.company || '?'} - ${extracted.role || '?'}`, 'success')
    }
  }

  return (
    <div className="flex gap-2">
      <button
        onClick={backfill}
        disabled={creating || extracting}
        className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
      >
        {creating ? 'Creating...' : 'Create from Email'}
      </button>
      {onPrefill && (
        <button
          onClick={handlePrefill}
          disabled={creating || extracting}
          className="px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50 text-sm"
        >
          {extracting ? 'Extracting...' : 'Prefill Only'}
        </button>
      )}
    </div>
  );
}
