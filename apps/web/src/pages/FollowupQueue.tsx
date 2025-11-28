import { useFollowupQueue } from '@/hooks/useFollowupQueue';
import { FollowupQueueList } from '@/components/followups/FollowupQueueList';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { AlertCircle, Inbox, ExternalLink } from 'lucide-react';
import { PriorityBadge } from '@/components/priority-badge';

export function FollowupQueue() {
  const {
    items,
    queueMeta,
    isLoading,
    error,
    selectedItem,
    setSelectedItem,
    markDone,
    refresh,
  } = useFollowupQueue();

  if (isLoading) {
    return (
      <div className="h-full flex gap-4 p-4" data-testid="followup-queue-page">
        {/* Left sidebar skeleton */}
        <div className="w-96 space-y-2">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>

        {/* Right viewer skeleton */}
        <div className="flex-1">
          <Skeleton className="h-full w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center p-4" data-testid="followup-queue-page">
        <Card className="p-6 max-w-md bg-zinc-900 border-zinc-800">
          <div className="flex items-center gap-3 text-red-400">
            <AlertCircle className="h-6 w-6 flex-shrink-0" />
            <div>
              <h3 className="font-semibold mb-1">Error loading follow-up queue</h3>
              <p className="text-sm text-zinc-400">{error}</p>
            </div>
          </div>
          <button
            onClick={refresh}
            className="mt-4 w-full px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded text-sm"
          >
            Retry
          </button>
        </Card>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="h-full flex items-center justify-center p-4" data-testid="followup-queue-page">
        <Card className="p-8 max-w-md bg-zinc-900 border-zinc-800 text-center">
          <Inbox className="h-12 w-12 mx-auto mb-4 text-zinc-600" />
          <h3 className="font-semibold text-lg mb-2 text-zinc-100">All caught up!</h3>
          <p className="text-sm text-zinc-400">
            No follow-ups needed right now. Check back later or adjust your time window.
          </p>
          {queueMeta && (
            <p className="text-xs text-zinc-500 mt-3">
              Searched {queueMeta.time_window_days} days of activity
            </p>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div className="h-full flex gap-4 p-4" data-testid="followup-queue-page">
      {/* Left sidebar: Queue list */}
      <div className="w-96 overflow-y-auto">
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-zinc-100 mb-1">Follow-up Queue</h2>
          {queueMeta && (
            <div className="space-y-2">
              <p className="text-sm text-zinc-400">
                {queueMeta.total} {queueMeta.total === 1 ? 'item' : 'items'} in the last {queueMeta.time_window_days} days
              </p>
              {/* Progress bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-zinc-500">
                  <span>{queueMeta.done_count} / {queueMeta.total} done</span>
                  <span>{Math.round((queueMeta.done_count / queueMeta.total) * 100)}%</span>
                </div>
                <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-600 transition-all duration-300"
                    style={{ width: `${(queueMeta.done_count / queueMeta.total) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        <FollowupQueueList
          items={items}
          selectedItem={selectedItem}
          onSelect={setSelectedItem}
          onToggleDone={markDone}
        />
      </div>

      {/* Right panel: Thread details */}
      <div className="flex-1 overflow-hidden">
        {selectedItem ? (
          <Card className="h-full flex flex-col bg-zinc-900 border-zinc-800">
            <div className="p-6 border-b border-zinc-800">
              <h3 className="text-lg font-semibold text-zinc-100 mb-2">
                {selectedItem.company && selectedItem.role
                  ? `${selectedItem.company} - ${selectedItem.role}`
                  : selectedItem.subject || 'Thread details'}
              </h3>

              {selectedItem.snippet && (
                <p className="text-sm text-zinc-400 mb-4">{selectedItem.snippet}</p>
              )}

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="bg-zinc-800 hover:bg-zinc-700 border-zinc-700"
                  onClick={() => window.open(selectedItem.gmail_url, '_blank')}
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Open in Gmail
                </Button>

                {selectedItem.application_id && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="bg-zinc-800 hover:bg-zinc-700 border-zinc-700"
                    onClick={() => window.open(`/tracker?appId=${selectedItem.application_id}`, '_blank')}
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Open in Tracker
                  </Button>
                )}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-zinc-300 mb-2">Details</h4>
                  <dl className="space-y-2 text-sm">
                    {selectedItem.company && (
                      <div className="flex">
                        <dt className="w-24 text-zinc-500">Company:</dt>
                        <dd className="text-zinc-200">{selectedItem.company}</dd>
                      </div>
                    )}
                    {selectedItem.role && (
                      <div className="flex">
                        <dt className="w-24 text-zinc-500">Role:</dt>
                        <dd className="text-zinc-200">{selectedItem.role}</dd>
                      </div>
                    )}
                    {selectedItem.status && (
                      <div className="flex">
                        <dt className="w-24 text-zinc-500">Status:</dt>
                        <dd className="text-zinc-200 capitalize">{selectedItem.status.replace('_', ' ')}</dd>
                      </div>
                    )}
                    {selectedItem.last_message_at && (
                      <div className="flex">
                        <dt className="w-24 text-zinc-500">Last update:</dt>
                        <dd className="text-zinc-200">
                          {new Date(selectedItem.last_message_at).toLocaleDateString()} at{' '}
                          {new Date(selectedItem.last_message_at).toLocaleTimeString()}
                        </dd>
                      </div>
                    )}
                    <div className="flex items-center">
                      <dt className="w-24 text-zinc-500">Priority:</dt>
                      <dd>
                        <PriorityBadge priority={selectedItem.priority} />
                      </dd>
                    </div>
                  </dl>
                </div>

                {selectedItem.reason_tags && selectedItem.reason_tags.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-zinc-300 mb-2">Reasons for follow-up</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedItem.reason_tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-1 text-xs rounded bg-zinc-800 text-zinc-300 border border-zinc-700"
                        >
                          {tag.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Card>
        ) : (
          <Card className="h-full flex items-center justify-center bg-zinc-900/50 border-zinc-800">
            <div className="text-center text-zinc-500">
              <p className="text-sm">Select a follow-up to view details</p>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
