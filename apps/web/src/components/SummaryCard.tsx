// apps/web/src/components/SummaryCard.tsx
/**
 * Phase 4 AI Feature: Email Thread Summarizer
 * Displays 5-bullet summary with citations
 */
import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Sparkles, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface Citation {
  snippet: string;
  message_id: string;
  offset: number;
}

interface SummaryData {
  bullets: string[];
  citations: Citation[];
}

interface SummaryCardProps {
  threadId: string;
  maxCitations?: number;
  onCitationClick?: (messageId: string) => void;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({
  threadId,
  maxCitations = 3,
  onCitationClick,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [expanded, setExpanded] = useState(false);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/ai/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: threadId,
          max_citations: maxCitations,
        }),
      });

      if (!response.ok) {
        if (response.status === 503) {
          throw new Error('AI service unavailable');
        }
        if (response.status === 504) {
          throw new Error('Request timeout - thread too long');
        }
        throw new Error(`Failed to generate summary (${response.status})`);
      }

      const data = await response.json();
      setSummary(data);
      setExpanded(true);
    } catch (err) {
      console.error('Summary fetch error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = () => {
    if (!summary && !loading) {
      fetchSummary();
    } else {
      setExpanded(!expanded);
    }
  };

  return (
    <Card className="mb-4 border-primary">
      <CardContent className="p-4">
        <div
          className="flex items-center justify-between cursor-pointer"
          onClick={handleToggle}
        >
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-semibold">AI Summary</h3>
            {summary && (
              <Badge variant="outline" className="border-primary text-primary">
                5 key points
              </Badge>
            )}
          </div>
          <Button variant="ghost" size="icon">
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </div>

        {expanded && (
          <div className="mt-4">
            {loading && (
              <div className="flex justify-center py-6">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            )}

            {error && (
              <Alert className="mt-2">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {summary && (
              <div className="mt-2 space-y-3">
                {/* 5 bullet points */}
                <ul className="space-y-2 list-disc list-inside">
                  {summary.bullets.map((bullet, idx) => (
                    <li key={idx} className="text-sm text-foreground">
                      {bullet}
                    </li>
                  ))}
                </ul>

                {/* Citations */}
                {summary.citations.length > 0 && (
                  <div className="mt-4">
                    <p className="text-xs text-muted-foreground mb-2">
                      Sources:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {summary.citations.map((citation, idx) => (
                        <Badge
                          key={idx}
                          variant="outline"
                          className={
                            onCitationClick
                              ? 'cursor-pointer hover:bg-accent max-w-[200px] truncate'
                              : 'max-w-[200px] truncate'
                          }
                          onClick={() => onCitationClick?.(citation.message_id)}
                        >
                          &quot;{citation.snippet.substring(0, 30)}...&quot;
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
