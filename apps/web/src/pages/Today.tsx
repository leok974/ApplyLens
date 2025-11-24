import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Mail, ExternalLink, Inbox } from 'lucide-react';
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

interface TodayResponse {
  status: string;
  intents: IntentData[];
}

export default function Today() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TodayResponse | null>(null);

  useEffect(() => {
    const fetchToday = async () => {
      try {
        setLoading(true);
        setError(null);

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
      } catch (err) {
        console.error('Error fetching today triage:', err);
        setError(err instanceof Error ? err.message : 'Failed to load today\'s triage');
      } finally {
        setLoading(false);
      }
    };

    fetchToday();
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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading today's triage...</p>
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
                  <p className="text-sm text-muted-foreground italic">
                    All clear! 🎉
                  </p>
                ) : (
                  <div className="space-y-2">
                    {intentData.threads.slice(0, 5).map((thread) => (
                      <div
                        key={thread.threadId}
                        className="group p-2 rounded-md hover:bg-accent/50 transition-colors cursor-pointer"
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

                            {/* Action buttons */}
                            <div className="flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOpenInThreadViewer(thread.threadId);
                                }}
                                className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                              >
                                <Inbox className="h-3 w-3" />
                                Thread Viewer
                              </button>

                              {thread.applicationId && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleOpenInTracker(thread.applicationId!);
                                  }}
                                  className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
                                >
                                  <ExternalLink className="h-3 w-3" />
                                  Tracker
                                </button>
                              )}

                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOpenInGmail(thread.threadId);
                                }}
                                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                              >
                                <ExternalLink className="h-3 w-3" />
                                Gmail
                              </button>
                            </div>
                          </div>
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
