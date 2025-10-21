// apps/web/src/components/RagResults.tsx
/**
 * Phase 4 AI Feature: RAG-powered Search
 * Displays search results with highlighted snippets
 */
import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Search, Sparkles, Loader2 } from 'lucide-react';

interface RagHit {
  thread_id: string;
  message_id: string;
  score: number;
  highlights: string[];
  sender: string;
  subject: string;
  date: string;
}

interface RagResultsData {
  hits: RagHit[];
  total: number;
}

interface RagResultsProps {
  onResultClick?: (threadId: string, messageId: string) => void;
}

export const RagResults: React.FC<RagResultsProps> = ({ onResultClick }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<RagResultsData | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/rag/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          q: query.trim(),
          k: 5,
        }),
      });

      if (!response.ok) {
        if (response.status === 503) {
          throw new Error('RAG search is disabled');
        }
        throw new Error(`Search failed (${response.status})`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error('RAG search error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  // Render highlights with HTML (sanitized by backend)
  const renderHighlights = (highlights: string[]) => {
    return highlights.map((highlight, idx) => (
      <p
        key={idx}
        className="text-sm text-muted-foreground mt-1"
        dangerouslySetInnerHTML={{ __html: highlight }}
      />
    ));
  };

  return (
    <div className="space-y-4">
      {/* Search Input */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Sparkles className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search emails with AI..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyPress}
            disabled={loading}
            className="pl-10"
          />
        </div>
        <Button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Search className="h-4 w-4 mr-2" />
          )}
          Search
        </Button>
      </div>

      {/* Error */}
      {error && (
        <Alert>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Found {results.total} result{results.total !== 1 ? 's' : ''}
          </p>

          {results.hits.length === 0 ? (
            <Alert>
              <AlertDescription>
                No results found for &quot;{query}&quot;
              </AlertDescription>
            </Alert>
          ) : (
            <div className="space-y-4">
              {results.hits.map((hit, idx) => (
                <div key={hit.message_id}>
                  {idx > 0 && <Separator className="my-4" />}
                  <div
                    className={
                      onResultClick
                        ? 'cursor-pointer rounded-lg p-3 hover:bg-accent transition-colors'
                        : 'p-3'
                    }
                    onClick={() =>
                      onResultClick?.(hit.thread_id, hit.message_id)
                    }
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="text-sm font-semibold">{hit.subject}</h4>
                      <Badge variant="outline">
                        Score: {hit.score.toFixed(2)}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">
                      From: {hit.sender} •{' '}
                      {new Date(hit.date).toLocaleDateString()}
                    </p>
                    <div className="space-y-1">
                      {renderHighlights(hit.highlights)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
