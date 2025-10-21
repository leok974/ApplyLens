// apps/web/src/components/SummaryCard.tsx
/**
 * Phase 4 AI Feature: Email Thread Summarizer
 * Displays 5-bullet summary with citations
 */
import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  Chip,
  Box,
  CircularProgress,
  Alert,
  IconButton,
  Collapse,
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
} from '@mui/icons-material';

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
    <Card
      sx={{
        mb: 2,
        border: '1px solid',
        borderColor: 'primary.main',
        bgcolor: 'background.paper',
      }}
    >
      <CardContent>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
          }}
          onClick={handleToggle}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AIIcon color="primary" />
            <Typography variant="h6">AI Summary</Typography>
            {summary && (
              <Chip
                label="5 key points"
                size="small"
                color="primary"
                variant="outlined"
              />
            )}
          </Box>
          <IconButton size="small">
            {expanded ? <CollapseIcon /> : <ExpandIcon />}
          </IconButton>
        </Box>

        <Collapse in={expanded}>
          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
              <CircularProgress size={32} />
            </Box>
          )}

          {error && (
            <Alert severity="info" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}

          {summary && (
            <Box sx={{ mt: 2 }}>
              {/* 5 bullet points */}
              <List dense>
                {summary.bullets.map((bullet, idx) => (
                  <ListItem key={idx} sx={{ pl: 0 }}>
                    <ListItemText
                      primary={bullet}
                      primaryTypographyProps={{
                        variant: 'body2',
                        color: 'text.primary',
                      }}
                    />
                  </ListItem>
                ))}
              </List>

              {/* Citations */}
              {summary.citations.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    gutterBottom
                  >
                    Sources:
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                    {summary.citations.map((citation, idx) => (
                      <Chip
                        key={idx}
                        label={`"${citation.snippet.substring(0, 30)}..."`}
                        size="small"
                        variant="outlined"
                        onClick={() => onCitationClick?.(citation.message_id)}
                        sx={{
                          cursor: onCitationClick ? 'pointer' : 'default',
                          maxWidth: 200,
                        }}
                      />
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
};
