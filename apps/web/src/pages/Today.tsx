import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Mail, ExternalLink, PanelRightOpen } from 'lucide-react';
import { apiUrl } from '@/lib/apiUrl';
import { cn } from '@/lib/utils';
import type { MailThreadSummary } from '@/lib/mailThreads';

// Intent display metadata
const INTENT_META = {
  followups: {
    title: 'Follow-ups',
    icon: '🔄',
    description: 'Threads that need your response',
    color: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
  },
  bills: {
    title: 'Bills & Invoices',
    icon: '💳',
    description: 'Payment due dates and receipts',
    color: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
  },
  interviews: {
    title: 'Interviews',
    icon: '📅',
    description: 'Interview invites and scheduling',
    color: 'bg-purple-500/10 border-purple-500/20 text-purple-400',
  },
  unsubscribe: {
    title: 'Unsubscribe',
    icon: '🚫',
    description: 'Promotional emails to clean up',
    color: 'bg-orange-500/10 border-orange-500/20 text-orange-400',
  },
  clean_promos: {
    title: 'Clean Promos',
    icon: '🧹',
    description: 'Marketing emails to archive',
    color: 'bg-pink-500/10 border-pink-500/20 text-pink-400',
  },
  suspicious: {
    title: 'Suspicious',
    icon: '⚠️',
    description: 'Potential phishing or spam',
    color: 'bg-red-500/10 border-red-500/20 text-red-400',
  },
} as const;

type IntentName = keyof typeof INTENT_META;

interface IntentSummary {
  count: number;
  time_window_days: number;
}

interface IntentData {
  intent: IntentName;
  summary: IntentSummary;
  threads: MailThreadSummary[];
}

interface FollowupSummary {
  total: number;
  done_count: number;
  remaining_count: number;
  time_window_days: number;
}

interface OpportunitiesSummary {
  total: number;
  perfect: number;
  strong: number;
  possible: number;
  skip?: number | null;
}

interface TodayResponse {
  status: string;
  intents: IntentData[];
  followups?: FollowupSummary;
  opportunities?: OpportunitiesSummary | null;
}

export default function Today() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TodayResponse | null>(null);
  const loadingIntervalRef = useRef<number | null>(null);

  useEffect(() => {
    const fetchToday = async () => {
      setStatus('loading');
      setProgress(0);
      setError(null);

      // Fake-but-smooth progress while backend works
      if (loadingIntervalRef.current !== null) {
        window.clearInterval(loadingIntervalRef.current);
      }
      loadingIntervalRef.current = window.setInterval(() => {
        setProgress((prev) => {
          // Creep up to 90% max, we'll jump to 100% on success
          if (prev >= 90) return prev;
          return prev + 3;
        });
      }, 300);

      try {
        const response = await fetch(apiUrl('/api/v2/agent/today'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ time_window_days: 90 }),
        });

        if (!response.ok) {
          if (response.status === 401) {
            throw new Error('Not authenticated. Please log in.');
          }
          throw new Error(`Failed to fetch today's triage: ${response.statusText}`);
        }

        const result: TodayResponse = await response.json();
        setData(result);
        setStatus('success');
        setProgress(100);
      } catch (err) {
        console.error('Error fetching today triage:', err);
        setError(err instanceof Error ? err.message : 'Failed to load today\'s triage');
        setStatus('error');
        setProgress(100);
      } finally {
        if (loadingIntervalRef.current !== null) {
          window.clearInterval(loadingIntervalRef.current);
          loadingIntervalRef.current = null;
        }
      }
    };

    fetchToday();

    // Clean up interval on unmount
    return () => {
      if (loadingIntervalRef.current !== null) {
        window.clearInterval(loadingIntervalRef.current);
      }
    };
  }, []);

  // Handler: Open thread in Gmail
  const handleOpenInGmail = (threadId: string) => {
    const gmailUrl = `https://mail.google.com/mail/u/0/#inbox/${threadId}`;
    window.open(gmailUrl, '_blank');
  };

  // Handler: Open in Thread Viewer (Inbox page with deep-link)
  const handleOpenInThreadViewer = (threadId: string) => {
    // TODO: Update this to the correct route once Thread Viewer deep-linking is implemented
    navigate(`/inbox?open=${threadId}`);
  };

  // Handler: Open application in Tracker
  const handleOpenInTracker = (applicationId: number) => {
    navigate(`/applications?highlight=${applicationId}`);
  };

  // Render loading state with progress indicator
  if (status === 'loading') {
    return (
      <div className="container mx-auto p-6 max-w-7xl">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Today</h1>
          <p className="text-muted-foreground">
            What should you do with your inbox today?
          </p>
        </div>

        {/* Progress indicator */}
        <div className="flex flex-col gap-4 items-center justify-center py-16">
          <div className="flex items-center gap-2 text-sm text-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Preparing today&apos;s triage… {progress}%</span>
          </div>
          <div className="w-full max-w-md">
            <Progress value={progress} className="h-1.5" />
          </div>
          <p className="text-xs text-muted-foreground text-center max-w-md">
            Scanning follow-ups, bills, newsletters, promos and risk in the background.
          </p>
        </div>

        {/* Skeleton grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {['followups', 'bills', 'interviews', 'unsubscribe', 'clean_promos', 'suspicious'].map((intent) => (
            <Card key={intent} className="animate-pulse">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <div className="h-5 w-28 rounded-full bg-muted" />
                    <div className="h-3 w-40 rounded-full bg-muted/60" />
                  </div>
                  <div className="h-6 w-12 rounded-full bg-muted" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-20 w-full rounded-md bg-muted/60" />
                  <div className="h-20 w-full rounded-md bg-muted/40" />
                  <div className="h-20 w-full rounded-md bg-muted/20" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6 max-w-6xl">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!data || data.intents.length === 0) {
    return (
      <div className="container mx-auto p-6 max-w-6xl">
        <Alert>
          <AlertDescription>No triage data available for today.</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Today</h1>
        <p className="text-muted-foreground">
          What should you do with your inbox today?
        </p>
      </div>

      {/* Follow-ups Summary Card */}
      {data.followups && (
        <Card
          className="mb-6 border-blue-500/20 bg-blue-500/5"
          data-testid="today-followups-card"
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <span className="text-2xl">🔄</span>
                  <span>Follow-ups</span>
                </CardTitle>
                <p className="text-xs text-muted-foreground mt-1">
                  {data.followups.remaining_count} remaining · last {data.followups.time_window_days} days
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="text-xs"
                onClick={() => navigate('/followups')}
                data-testid="today-followups-open-queue"
              >
                Open queue
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <span className="text-sm text-foreground">
                {data.followups.done_count} / {data.followups.total} done
              </span>
              <div className="h-2 flex-1 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all duration-300"
                  style={{
                    width: `${
                      data.followups.total === 0
                        ? 0
                        : Math.round((data.followups.done_count / data.followups.total) * 100)
                    }%`,
                  }}
                />
              </div>
              <span className="text-xs text-muted-foreground">
                {data.followups.total === 0
                  ? '0%'
                  : `${Math.round((data.followups.done_count / data.followups.total) * 100)}%`}
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Opportunities Summary Card */}
      {data.opportunities && (
        <Card
          className="mb-6 border-amber-500/20 bg-amber-500/5"
          data-testid="today-opportunities-card"
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <span className="text-2xl">💼</span>
                  <span>Opportunities</span>
                </CardTitle>
                <p className="text-xs text-muted-foreground mt-1">
                  {data.opportunities.total} found · {data.opportunities.perfect} perfect ·{' '}
                  {data.opportunities.strong} strong · {data.opportunities.possible} possible
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="text-xs border-amber-400/60 bg-amber-500/10 hover:bg-amber-500/20"
                onClick={() => navigate('/opportunities')}
                data-testid="today-opportunities-cta"
              >
                Review
              </Button>
            </div>
          </CardHeader>
        </Card>
      )}

      {/* Intent Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {data.intents.map((intentData) => {
          const meta = INTENT_META[intentData.intent];
          const hasThreads = intentData.threads.length > 0;

          return (
            <Card
              key={intentData.intent}
              className={cn(
                'transition-all hover:shadow-lg',
                meta.color
              )}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg font-semibold flex items-center gap-2">
                    <span className="text-2xl">{meta.icon}</span>
                    <span>{meta.title}</span>
                  </CardTitle>
                  <Badge variant="secondary" className="text-xs">
                    {intentData.summary.count}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {meta.description}
                </p>
              </CardHeader>

              <CardContent>
                {!hasThreads ? (
                  // Empty state
                  <div className="flex flex-col gap-2 rounded-xl border border-dashed border-border bg-muted/30 px-3 py-6 text-center">
                    {intentData.intent === 'followups' && (
                      <>
                        <p className="text-sm font-medium text-emerald-400">
                          You&apos;re all caught up 🎉
                        </p>
                        <p className="text-xs text-muted-foreground">
                          No follow-ups needed from the last {intentData.summary.time_window_days} days.
                        </p>
                      </>
                    )}
                    {intentData.intent === 'bills' && (
                      <>
                        <p className="text-sm font-medium text-foreground">
                          No bills pending ✨
                        </p>
                        <p className="text-xs text-muted-foreground">
                          No invoices or receipts in the last {intentData.summary.time_window_days} days.
                        </p>
                      </>
                    )}
                    {intentData.intent === 'interviews' && (
                      <>
                        <p className="text-sm font-medium text-foreground">
                          No interviews scheduled 📅
                        </p>
                        <p className="text-xs text-muted-foreground">
                          No interview invites in the last {intentData.summary.time_window_days} days.
                        </p>
                      </>
                    )}
                    {intentData.intent === 'unsubscribe' && (
                      <>
                        <p className="text-sm font-medium text-foreground">
                          Clean inbox 🚫
                        </p>
                        <p className="text-xs text-muted-foreground">
                          No unwanted newsletters in the last {intentData.summary.time_window_days} days.
                        </p>
                      </>
                    )}
                    {intentData.intent === 'clean_promos' && (
                      <>
                        <p className="text-sm font-medium text-foreground">
                          Inbox is promo-light ✨
                        </p>
                        <p className="text-xs text-muted-foreground">
                          No marketing threads flagged in the last {intentData.summary.time_window_days} days.
                        </p>
                      </>
                    )}
                    {intentData.intent === 'suspicious' && (
                      <>
                        <p className="text-sm font-medium text-emerald-400">
                          All clear! 🛡️
                        </p>
                        <p className="text-xs text-muted-foreground">
                          No suspicious emails in the last {intentData.summary.time_window_days} days.
                        </p>
                      </>
                    )}
                    <p className="mt-2 text-[11px] text-muted-foreground/70">
                      This panel updates automatically as new mail comes in.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {intentData.threads.slice(0, 5).map((thread) => (
                      <div
                        key={thread.threadId}
                        className="rounded-md border border-border/50 hover:border-border transition-colors overflow-hidden"
                      >
                        {/* Thread content */}
                        <div
                          className="p-3 cursor-pointer hover:bg-accent/30 transition-colors"
                          onClick={() => handleOpenInGmail(thread.threadId)}
                        >
                          <div className="flex items-start gap-2">
                            <Mail className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">
                                {thread.subject || '(No subject)'}
                              </p>
                              <p className="text-xs text-muted-foreground truncate">
                                {thread.from}
                              </p>
                              {thread.snippet && (
                                <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                                  {thread.snippet}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Action buttons footer */}
                        <div className="flex items-center gap-2 px-3 py-2 border-t border-border/50 bg-muted/20">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenInThreadViewer(thread.threadId);
                            }}
                            className="h-7 rounded-full px-3 text-xs bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 hover:text-blue-300 border border-blue-500/20"
                            data-testid="open-thread-viewer"
                          >
                            <PanelRightOpen className="h-3 w-3 mr-1" />
                            Thread Viewer
                          </Button>

                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenInGmail(thread.threadId);
                            }}
                            className="h-7 rounded-full px-3 text-xs bg-zinc-500/10 hover:bg-zinc-500/20 text-zinc-400 hover:text-zinc-300 border border-zinc-500/20"
                            data-testid="open-gmail"
                          >
                            <Mail className="h-3 w-3 mr-1" />
                            Gmail
                          </Button>

                          {thread.applicationId && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenInTracker(thread.applicationId!);
                              }}
                              className="h-7 rounded-full px-3 text-xs bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 hover:text-purple-300 border border-purple-500/20"
                              data-testid="open-tracker"
                            >
                              <ExternalLink className="h-3 w-3 mr-1" />
                              Tracker
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}

                    {intentData.summary.count > 5 && (
                      <p className="text-xs text-muted-foreground text-center pt-2">
                        +{intentData.summary.count - 5} more
                      </p>
                    )}
                  </div>
                )}

                {/* Time window footer */}
                <div className="mt-4 pt-3 border-t border-border/50">
                  <p className="text-xs text-muted-foreground">
                    Last {intentData.summary.time_window_days} days
                  </p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
