import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, Mail, Users, PieChart } from 'lucide-react';

interface ActivityDay {
  day: string;
  messages_count: number;
  unique_senders: number;
  avg_size_kb: number;
  total_size_mb: number;
}

interface TopSender {
  from_email: string;
  messages_30d: number;
  total_size_mb: number;
}

interface Category {
  category: string;
  messages_30d: number;
  pct_of_total: number;
}

export function ProfileMetrics() {
  const [activityData, setActivityData] = useState<ActivityDay[]>([]);
  const [topSenders, setTopSenders] = useState<TopSender[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        
        // Fetch all metrics in parallel
        const [activityRes, sendersRes, categoriesRes] = await Promise.all([
          fetch('/api/warehouse/profile/activity-daily?days=14'),
          fetch('/api/warehouse/profile/top-senders?limit=5'),
          fetch('/api/warehouse/profile/categories-30d?limit=5'),
        ]);

        // Check for 412 Precondition Failed (warehouse disabled)
        if (activityRes.status === 412 || sendersRes.status === 412 || categoriesRes.status === 412) {
          setError('warehouse_disabled');
          setLoading(false);
          return;
        }

        if (!activityRes.ok || !sendersRes.ok || !categoriesRes.ok) {
          throw new Error('Failed to fetch warehouse metrics');
        }

        const [activity, senders, cats] = await Promise.all([
          activityRes.json(),
          sendersRes.json(),
          categoriesRes.json(),
        ]);

        setActivityData(activity);
        setTopSenders(senders);
        setCategories(cats);
        setError(null);
      } catch (err) {
        console.error('Warehouse metrics error:', err);
        setError(err instanceof Error ? err.message : 'Failed to load metrics');
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, []);

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="h-[200px] animate-pulse bg-muted" />
        <Card className="h-[200px] animate-pulse bg-muted" />
        <Card className="h-[200px] animate-pulse bg-muted" />
      </div>
    );
  }

  if (error) {
    // Graceful fallback: Show friendly message with mock data option
    if (error === 'warehouse_disabled') {
      return (
        <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20 dark:border-blue-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-blue-600" />
              <span>Warehouse Analytics (Demo Mode)</span>
              <Badge variant="outline" className="ml-auto text-xs">
                Offline
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              BigQuery warehouse is currently offline. Analytics will resume when the warehouse is re-enabled.
            </p>
            <p className="text-xs text-muted-foreground mt-2">
              💡 Set <code className="px-1 py-0.5 bg-muted rounded">USE_WAREHOUSE=1</code> to enable real-time metrics.
            </p>
          </CardContent>
        </Card>
      );
    }

    return (
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Warehouse Metrics Unavailable</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{error}</p>
          <p className="text-xs text-muted-foreground mt-2">
            Ensure USE_WAREHOUSE=1 is set on the backend and BigQuery is connected.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!activityData?.length && !topSenders?.length && !categories?.length) {
    return null;
  }

  // Calculate summary stats
  const totalMessages = activityData.reduce((sum, d) => sum + d.messages_count, 0);
  const avgMessagesPerDay = totalMessages / activityData.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-primary" />
        <h3 className="font-semibold text-lg">Inbox Analytics (Last 14 Days)</h3>
        <Badge variant="outline" className="ml-auto">
          Powered by BigQuery
        </Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {/* Activity Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              Inbox Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalMessages}</div>
            <p className="text-xs text-muted-foreground">
              ~{avgMessagesPerDay.toFixed(1)} emails/day
            </p>
            <div className="mt-4 space-y-1">
              {activityData.slice(-7).map((d) => (
                <div key={d.day} className="flex justify-between text-xs">
                  <span className="text-muted-foreground">{d.day}</span>
                  <span className="font-mono font-medium">{d.messages_count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Senders Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Users className="h-4 w-4 text-muted-foreground" />
              Top Senders (30d)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {topSenders.map((sender, idx) => (
                <div key={sender.from_email} className="flex items-start gap-2">
                  <Badge variant="outline" className="font-mono text-xs">
                    #{idx + 1}
                  </Badge>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" title={sender.from_email}>
                      {sender.from_email.split('@')[0]}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {sender.messages_30d} emails
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Categories Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <PieChart className="h-4 w-4 text-muted-foreground" />
              Categories (30d)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {categories.map((cat) => (
                <div key={cat.category} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="capitalize">{cat.category}</span>
                    <span className="font-mono font-medium">{cat.pct_of_total}%</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary"
                      style={{ width: `${cat.pct_of_total}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
