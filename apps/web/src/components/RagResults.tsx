// apps/web/src/components/RagResults.tsx
/**
 * Phase 4 AI Feature: RAG-powered Search
 * Displays search results with highlighted snippets
 */
import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  ListItemText,
  Chip,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  AutoAwesome as AIIcon,
} from '@mui/icons-material';

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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  // Render highlights with HTML (sanitized by backend)
  const renderHighlights = (highlights: string[]) => {
    return highlights.map((highlight, idx) => (
      <Typography
        key={idx}
        variant="body2"
        color="text.secondary"
        sx={{ mt: 0.5 }}
        dangerouslySetInnerHTML={{ __html: highlight }}
      />
    ));
  };

  return (
    <Box>
      {/* Search Input */}
      <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
        <TextField
          fullWidth
          placeholder="Search emails with AI..."
          value={query}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={loading}
          InputProps={{
            startAdornment: <AIIcon sx={{ mr: 1, color: 'text.secondary' }} />,
          }}
        />
        <Button
          variant="contained"
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
        >
          Search
        </Button>
      </Box>

      {/* Error */}
      {error && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Results */}
      {results && (
        <Box>
          <Typography variant="caption" color="text.secondary" gutterBottom>
            Found {results.total} result{results.total !== 1 ? 's' : ''}
          </Typography>

          {results.hits.length === 0 ? (
            <Alert severity="info" sx={{ mt: 2 }}>
              No results found for "{query}"
            </Alert>
          ) : (
            <List sx={{ mt: 1 }}>
              {results.hits.map((hit, idx) => (
                <React.Fragment key={hit.message_id}>
                  {idx > 0 && <Divider sx={{ my: 2 }} />}
                  <ListItem
                    alignItems="flex-start"
                    sx={{
                      pl: 0,
                      cursor: onResultClick ? 'pointer' : 'default',
                      '&:hover': onResultClick
                        ? { bgcolor: 'action.hover' }
                        : {},
                    }}
                    onClick={() =>
                      onResultClick?.(hit.thread_id, hit.message_id)
                    }
                  >
                    <ListItemText
                      primary={
                        <Box
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1,
                            mb: 0.5,
                          }}
                        >
                          <Typography variant="subtitle2" fontWeight="bold">
                            {hit.subject}
                          </Typography>
                          <Chip
                            label={`Score: ${hit.score.toFixed(2)}`}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="caption" color="text.secondary">
                            From: {hit.sender} •{' '}
                            {new Date(hit.date).toLocaleDateString()}
                          </Typography>
                          <Box sx={{ mt: 1 }}>
                            {renderHighlights(hit.highlights)}
                          </Box>
                        </Box>
                      }
                    />
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          )}
        </Box>
      )}
    </Box>
  );
};
