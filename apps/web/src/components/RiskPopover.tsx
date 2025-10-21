// apps/web/src/components/RiskPopover.tsx
/**
 * Phase 4 AI Feature: Smart Risk Badge
 * Displays top 3 risk signals with explanations
 */
import { useState, useEffect } from 'react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  AlertTriangle,
  CheckCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';

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
  children: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export const RiskPopover: React.FC<RiskPopoverProps> = ({
  messageId,
  children,
  open,
  onOpenChange,
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

  const getRiskColor = (score: number): 'default' | 'secondary' | 'destructive' => {
    if (score < 30) return 'default';
    if (score < 70) return 'secondary';
    return 'destructive';
  };

  const getRiskIcon = (score: number) => {
    if (score < 30) return <CheckCircle className="h-5 w-5 text-green-600" />;
    if (score < 70) return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
    return <AlertCircle className="h-5 w-5 text-red-600" />;
  };

  const getRiskLabel = (score: number): string => {
    if (score < 30) return 'Low Risk';
    if (score < 70) return 'Medium Risk';
    return 'High Risk';
  };

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        {children}
      </PopoverTrigger>
      <PopoverContent className="w-96 p-4">
        {loading && (
          <div className="flex justify-center py-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {error && (
          <Alert>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {riskData && (
          <div className="space-y-4">
            {/* Risk Score Header */}
            <div className="flex items-center gap-2">
              {getRiskIcon(riskData.score)}
              <h3 className="text-lg font-semibold">
                {getRiskLabel(riskData.score)}
              </h3>
              <Badge variant={getRiskColor(riskData.score)}>
                Score: {riskData.score}
              </Badge>
            </div>

            <Separator />

            {/* Top 3 Signals */}
            {riskData.signals.length > 0 ? (
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground">
                  Top Risk Signals:
                </p>
                <div className="space-y-3">
                  {riskData.signals.map((signal, idx) => (
                    <div key={idx} className="flex gap-3">
                      <div className="flex-shrink-0">
                        <span className="text-sm font-bold text-primary">
                          #{idx + 1}
                        </span>
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-medium">{signal.label}</p>
                        <p className="text-xs text-muted-foreground">
                          {signal.explain}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <Alert>
                <AlertDescription>No risk signals detected</AlertDescription>
              </Alert>
            )}
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
};
