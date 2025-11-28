import { useState, useEffect, useCallback } from 'react';
import { getFollowupQueue, updateFollowupState, QueueItem, QueueMeta } from '@/lib/api';
import { toast } from 'sonner';

interface UseFollowupQueueReturn {
  items: QueueItem[];
  queueMeta: QueueMeta | null;
  isLoading: boolean;
  error: string | null;
  selectedItem: QueueItem | null;
  setSelectedItem: (item: QueueItem | null) => void;
  markDone: (item: QueueItem, isDone: boolean) => Promise<void>;
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
      const response = await getFollowupQueue();

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

  const markDone = useCallback(async (item: QueueItem, isDone: boolean) => {
    // Optimistically update local state
    const previousItems = items;
    const previousMeta = queueMeta;

    setItems((prevItems) =>
      prevItems.map((i) =>
        i.thread_id === item.thread_id
          ? { ...i, is_done: isDone }
          : i
      )
    );

    // Update meta counts
    if (queueMeta) {
      const deltaDone = isDone ? 1 : -1;
      setQueueMeta({
        ...queueMeta,
        done_count: queueMeta.done_count + deltaDone,
        remaining_count: queueMeta.remaining_count - deltaDone,
      });
    }

    try {
      await updateFollowupState({
        thread_id: item.thread_id,
        application_id: item.application_id,
        is_done: isDone,
      });

      toast.success(isDone ? 'Marked as done' : 'Marked as not done');

      // If marking done the selected item, deselect it
      if (selectedItem?.thread_id === item.thread_id && isDone) {
        setSelectedItem(null);
      }
    } catch (err) {
      // Rollback on error
      setItems(previousItems);
      setQueueMeta(previousMeta);
      toast.error(
        err instanceof Error ? err.message : 'Failed to update follow-up state'
      );
    }
  }, [items, queueMeta, selectedItem]);

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
