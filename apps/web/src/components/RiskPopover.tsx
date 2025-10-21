// apps/web/src/components/RiskPopover.tsx
/**
 * Phase 4 AI Feature: Smart Risk Badge
 * Displays top 3 risk signals with explanations
 */
import React, { useState, useEffect } from 'react';
import {
  Popover,
  Box,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  Alert,
  Chip,
  Divider,
} from '@mui/material';
import {
  Warning as WarningIcon,
  CheckCircle as SafeIcon,
  Error as DangerIcon,
} from '@mui/icons-material';

interface RiskSignal {
  id: string;
  label: string;
  explain: string;
}

interface RiskData {
  score: number;
  signals: RiskSignal[];
}

interface RiskPopoverProps {
  messageId: string;
  anchorEl: HTMLElement | null;
  open: boolean;
  onClose: () => void;
}

export const RiskPopover: React.FC<RiskPopoverProps> = ({
  messageId,
  anchorEl,
  open,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [riskData, setRiskData] = useState<RiskData | null>(null);

  useEffect(() => {
    if (open && messageId) {
      fetchRiskData();
    }
  }, [open, messageId]);

  const fetchRiskData = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/security/risk-top3?message_id=${encodeURIComponent(messageId)}`
      );

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Message not found');
        }
        throw new Error(`Failed to fetch risk data (${response.status})`);
      }

      const data = await response.json();
      setRiskData(data);
    } catch (err) {
      console.error('Risk data fetch error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (score: number): 'success' | 'warning' | 'error' => {
    if (score < 30) return 'success';
    if (score < 70) return 'warning';
    return 'error';
  };

  const getRiskIcon = (score: number) => {
    if (score < 30) return <SafeIcon color="success" />;
    if (score < 70) return <WarningIcon color="warning" />;
    return <DangerIcon color="error" />;
  };

  const getRiskLabel = (score: number): string => {
    if (score < 30) return 'Low Risk';
    if (score < 70) return 'Medium Risk';
    return 'High Risk';
  };

  return (
    <Popover
      open={open}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{
        vertical: 'bottom',
        horizontal: 'left',
      }}
      transformOrigin={{
        vertical: 'top',
        horizontal: 'left',
      }}
      PaperProps={{
        sx: { maxWidth: 400, p: 2 },
      }}
    >
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
          <CircularProgress size={32} />
        </Box>
      )}

      {error && (
        <Alert severity="info" sx={{ m: 0 }}>
          {error}
        </Alert>
      )}

      {riskData && (
        <Box>
          {/* Risk Score Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            {getRiskIcon(riskData.score)}
            <Typography variant="h6">
              {getRiskLabel(riskData.score)}
            </Typography>
            <Chip
              label={`Score: ${riskData.score}`}
              size="small"
              color={getRiskColor(riskData.score)}
            />
          </Box>

          <Divider sx={{ mb: 2 }} />

          {/* Top 3 Signals */}
          {riskData.signals.length > 0 ? (
            <>
              <Typography variant="caption" color="text.secondary" gutterBottom>
                Top Risk Signals:
              </Typography>
              <List dense>
                {riskData.signals.map((signal, idx) => (
                  <ListItem key={idx} sx={{ pl: 0, alignItems: 'flex-start' }}>
                    <ListItemIcon sx={{ minWidth: 36, mt: 0.5 }}>
                      <Typography
                        variant="body2"
                        color="primary"
                        fontWeight="bold"
                      >
                        #{idx + 1}
                      </Typography>
                    </ListItemIcon>
                    <ListItemText
                      primary={signal.label}
                      secondary={signal.explain}
                      primaryTypographyProps={{
                        variant: 'body2',
                        fontWeight: 'medium',
                      }}
                      secondaryTypographyProps={{
                        variant: 'caption',
                        color: 'text.secondary',
                      }}
                    />
                  </ListItem>
                ))}
              </List>
            </>
          ) : (
            <Alert severity="success" sx={{ m: 0 }}>
              No risk signals detected
            </Alert>
          )}
        </Box>
      )}
    </Popover>
  );
};
