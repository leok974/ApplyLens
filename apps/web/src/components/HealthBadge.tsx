import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, AlertCircle, PauseCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

type HealthStatus = 'ok' | 'degraded' | 'paused' | 'loading';

interface DivergenceData {
  es_count: number;
  bq_count: number;
  divergence_pct: number | null;
  status: 'ok' | 'degraded' | 'paused';
  message: string;
}

export function HealthBadge() {
  const [status, setStatus] = useState<HealthStatus>('loading');
  const [divergenceData, setDivergenceData] = useState<DivergenceData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isDemoMode = import.meta.env.VITE_DEMO_MODE === '1';

  useEffect(() => {
    let mounted = true;
    let pollTimeout: NodeJS.Timeout | null = null;
    let errorAttempt = 0;

    const checkHealth = async () => {
      if (!mounted) return;

      try {
        const res = await fetch('/api/metrics/divergence-bq');

        if (!mounted) return;

        if (res.status === 412) {
          // Warehouse disabled (feature flag off)
          setStatus('paused');
          setError('Warehouse disabled');
          errorAttempt = 0; // Not an error, expected state
          scheduleNext(60_000);
          return;
        }

        // 5xx errors: backend degraded, show paused with exponential backoff
        if (res.status >= 500 && res.status < 600) {
          console.warn(`[HealthBadge] Backend returned ${res.status}, treating as degraded`);
          setStatus('paused');
          setError(`Backend unavailable (HTTP ${res.status})`);

          // Exponential backoff: 2s, 4s, 8s, 16s, 32s, max 60s
          const delay = Math.min(60000, 2000 * Math.pow(2, errorAttempt++));
          scheduleNext(delay);
          return;
        }

        // 4xx errors (other than 412): unexpected, treat as paused
        if (!res.ok) {
          console.warn(`[HealthBadge] Unexpected status ${res.status}`);
          setStatus('paused');
          setError(`HTTP ${res.status}`);

          const delay = Math.min(60000, 2000 * Math.pow(2, errorAttempt++));
          scheduleNext(delay);
          return;
        }

        const data: DivergenceData = await res.json();
        setDivergenceData(data);
        setError(null);
        errorAttempt = 0; // Reset backoff on success

        // Use status from API response with validation
        if (data.status && ['ok', 'degraded', 'paused'].includes(data.status)) {
          setStatus(data.status);
        } else {
          console.warn(`[HealthBadge] Invalid status from API: ${data.status}, defaulting to 'paused'`);
          setStatus('paused');
        }

        // Poll every 60s when healthy
        scheduleNext(60_000);

      } catch (err) {
        // Network unreachable or other error - DO NOT reload
        if (!mounted) return;

        console.warn(`[HealthBadge] Network error: ${err}`);
        setStatus('paused');
        setError(err instanceof Error ? err.message : 'Unreachable');

        // Exponential backoff on network errors
        const delay = Math.min(60000, 2000 * Math.pow(2, errorAttempt++));
        scheduleNext(delay);
      }
    };

    const scheduleNext = (delay: number) => {
      if (pollTimeout) clearTimeout(pollTimeout);
      pollTimeout = setTimeout(checkHealth, delay);
    };

    // Initial check
    checkHealth();

    return () => {
      mounted = false;
      if (pollTimeout) clearTimeout(pollTimeout);
    };
  }, []);

  const statusConfig = {
    ok: {
      icon: CheckCircle2,
      label: 'Warehouse OK',
      variant: 'default' as const,
      className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 border-green-300',
    },
    degraded: {
      icon: AlertCircle,
      label: 'Degraded',
      variant: 'outline' as const,
      className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 border-yellow-300',
    },
    paused: {
      icon: PauseCircle,
      label: 'Paused',
      variant: 'secondary' as const,
      className: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 border-gray-300',
    },
    loading: {
      icon: Loader2,
      label: 'Checking...',
      variant: 'outline' as const,
      className: 'bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-300 border-blue-200',
    },
  };

  // Safety check: fallback to 'paused' if status is invalid
  const config = statusConfig[status] || statusConfig.paused;
  const Icon = config.icon;

  // Tooltip details
  const getTooltipContent = () => {
    if (status === 'loading') return 'Checking warehouse health...';
    if (status === 'paused' && error) return `Warehouse offline: ${error}`;
    if (status === 'paused') return 'Warehouse paused';

    if (divergenceData) {
      const pctDisplay = divergenceData.divergence_pct !== null
        ? `${divergenceData.divergence_pct.toFixed(2)}%`
        : 'N/A';

      const demoSuffix = isDemoMode ? ' (Demo data)' : '';

      if (status === 'degraded') {
        return `ES/BQ divergence: ${pctDisplay}${demoSuffix}`;
      }
      if (status === 'ok') {
        return `Healthy: ${pctDisplay} divergence${demoSuffix}`;
      }
    }

    return config.label;
  };

  return (
    <Badge
      data-testid="health-badge"
      variant={config.variant}
      className={cn(
        'flex items-center gap-1.5 px-2.5 py-1 font-medium transition-all',
        config.className,
        status === 'loading' && 'animate-pulse'
      )}
      title={getTooltipContent()}
    >
      <Icon
        className={cn(
          'h-3.5 w-3.5',
          status === 'loading' && 'animate-spin'
        )}
      />
      <span className="text-xs">{config.label}</span>
      {divergenceData && status !== 'paused' && divergenceData.divergence_pct !== null && (
        <span className="text-[10px] opacity-75 ml-0.5">
          ({divergenceData.divergence_pct.toFixed(1)}%)
        </span>
      )}
    </Badge>
  );
}
