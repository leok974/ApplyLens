/**
 * Interview Prep Panel
 *
 * Displays structured interview preparation materials including:
 * - Company and role overview
 * - Timeline of application progress
 * - Interview details (date, format, status)
 * - Prep sections (what to review, questions to ask)
 * - Notes textarea for personal prep notes
 */

import { useState } from 'react';
import type { InterviewPrepResponse } from '@/api/agent';

interface InterviewPrepPanelProps {
  prep: InterviewPrepResponse;
  onClose: () => void;
}

export function InterviewPrepPanel({ prep, onClose }: InterviewPrepPanelProps) {
  const [notes, setNotes] = useState('');

  // Format interview date if present
  const interviewDateFormatted = prep.interview_date
    ? new Date(prep.interview_date).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
    : null;

  return (
    <div
      className="flex flex-col gap-3 rounded-xl border bg-card p-4 h-full overflow-y-auto"
      data-testid="interview-prep-panel"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">
            Interview prep · {prep.company}
          </h2>
          <p className="text-xs text-muted-foreground">
            {prep.role}
            {interviewDateFormatted && ` · ${interviewDateFormatted}`}
            {prep.interview_format && ` · ${prep.interview_format}`}
          </p>
        </div>
        <button
          className="text-xs text-muted-foreground hover:underline"
          onClick={onClose}
          data-testid="interview-prep-close"
        >
          Close
        </button>
      </div>

      {/* Interview Status Badge */}
      {prep.interview_status && (
        <div className="inline-flex items-center gap-1.5 self-start rounded-md bg-blue-500/10 px-2 py-1">
          <div className="h-1.5 w-1.5 rounded-full bg-blue-500" />
          <span className="text-xs font-medium text-blue-700 dark:text-blue-400">
            {prep.interview_status}
          </span>
        </div>
      )}

      {/* Timeline */}
      {prep.timeline.length > 0 && (
        <div className="rounded-lg bg-muted/40 p-2" data-testid="interview-prep-timeline">
          <p className="text-xs font-medium mb-1">Timeline</p>
          <ul className="space-y-0.5">
            {prep.timeline.map((step, idx) => (
              <li key={idx} className="text-xs text-muted-foreground">
                • {step}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Preparation Sections */}
      <div className="grid gap-2 md:grid-cols-2" data-testid="interview-prep-sections">
        {prep.sections.map((section, idx) => (
          <div
            key={idx}
            className="rounded-lg border bg-background/40 p-2"
            data-testid={`interview-prep-section-${idx}`}
          >
            <p className="text-xs font-semibold mb-1">{section.title}</p>
            <ul className="space-y-0.5">
              {section.bullets.map((bullet, j) => (
                <li key={j} className="text-xs text-muted-foreground">
                  • {bullet}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Notes Textarea */}
      <div className="mt-auto" data-testid="interview-prep-notes-container">
        <p className="text-xs font-medium mb-1">Your notes</p>
        <textarea
          className="w-full rounded-md border bg-background/80 p-2 text-xs resize-none focus:outline-none focus:ring-2 focus:ring-ring"
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Jot down company research, stories you want to tell, questions you really want to ask..."
          data-testid="interview-prep-notes"
        />
      </div>
    </div>
  );
}
