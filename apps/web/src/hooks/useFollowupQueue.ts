import { useState, useEffect, useCallback } from 'react';
import { getFollowupQueue, QueueItem, QueueMeta } from '@/lib/api';

interface UseFollowupQueueReturn {
  items: QueueItem[];
  queueMeta: QueueMeta | null;
  isLoading: boolean;
  error: string | null;
  selectedItem: QueueItem | null;
  setSelectedItem: (item: QueueItem | null) => void;
  markDone: (item: QueueItem) => void;
  refresh: () => Promise<void>;
}

export function useFollowupQueue(): UseFollowupQueueReturn {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [queueMeta, setQueueMeta] = useState<QueueMeta | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<QueueItem | null>(null);

  const loadQueue = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await getFollowupQueue({ time_window_days: 30 });

      if (response.status === 'error') {
        setError(response.message || 'Failed to load follow-up queue');
        setItems([]);
        setQueueMeta(null);
        return;
      }

      setItems(response.items || []);
      setQueueMeta(response.queue_meta || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setItems([]);
      setQueueMeta(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const markDone = useCallback((item: QueueItem) => {
    // Update local state - no backend persistence yet
    setItems((prevItems) =>
      prevItems.map((i) =>
        i.thread_id === item.thread_id
          ? { ...i, is_done: !i.is_done }
          : i
      )
    );

    // If marking done the selected item, deselect it
    if (selectedItem?.thread_id === item.thread_id && !item.is_done) {
      setSelectedItem(null);
    }
  }, [selectedItem]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  return {
    items,
    queueMeta,
    isLoading,
    error,
    selectedItem,
    setSelectedItem,
    markDone,
    refresh: loadQueue,
  };
}
