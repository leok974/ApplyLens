import { useState, useCallback } from 'react';
import { bulkArchiveMessages, bulkMarkSafeMessages, bulkQuarantineMessages } from '../lib/api';
import { toast } from 'sonner';
import { track } from '../lib/analytics';

// Item type for progress tracking
export interface ThreadViewerItem {
  id: string;
  archived?: boolean;
  quarantined?: boolean;
}

/**
 * Hook for managing thread viewer state across pages
 * Provides consistent selection and open/close behavior
 * Now with keyboard navigation support (Phase 3)
 */
export function useThreadViewer(initialItems?: ThreadViewerItem[]) {
  const [items, setItems] = useState<ThreadViewerItem[]>(initialItems ?? []);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  // TODO(thread-viewer v1.4):
  // autoAdvance controls whether actions like Archive should
  // automatically step to the next thread. Defaults true.
  // Eventually persist this per-user (localStorage or server-side pref).
  const [autoAdvance, setAutoAdvance] = useState<boolean>(true);

  // TODO(thread-viewer v1.4):
  // selectedBulkIds represents the current multi-select "batch".
  // We'll drive checkboxes in the list rows from this.
  // After a bulk action we clear it.
  const [selectedBulkIds, setSelectedBulkIds] = useState<Set<string>>(new Set());

  const [isBulkMutating, setIsBulkMutating] = useState(false);

  const selectedId = selectedIndex != null ? items[selectedIndex]?.id ?? null : null;

  // open a given thread by id (e.g. row click)
  const showThread = useCallback(
    (id: string) => {
      const idx = items.findIndex(it => it.id === id);
      if (idx !== -1) {
        setSelectedIndex(idx);
      }
      setIsOpen(true);
    },
    [items]
  );

  // navigation helpers
  const goPrev = useCallback(() => {
    setSelectedIndex((prev) => {
      if (prev == null) return prev;
      const next = prev - 1;
      return next < 0 ? prev : next;
    });
    setIsOpen(true);
  }, []);

  const goNext = useCallback(() => {
    setSelectedIndex((prev) => {
      if (prev == null) return prev;
      const next = prev + 1;
      return next >= items.length ? prev : next;
    });
    setIsOpen(true);
  }, [items.length]);

  // TODO(thread-viewer v1.3):
  // advanceAfterAction() is intended for hotkeys like "D" (done/archive).
  // ThreadViewer will:
  //   - run handleArchive()
  //   - then call advanceAfterAction()
  // This gives us Superhuman-style triage flow.
  const advanceAfterAction = useCallback(() => {
    // jumps to next item if autoAdvance is on
    setSelectedIndex((prev) => {
      if (prev == null) return prev;
      if (!autoAdvance) return prev;
      const next = prev + 1;
      return next >= items.length ? prev : next;
    });
    setIsOpen(true);
  }, [items.length, autoAdvance]);

  const closeThread = useCallback(() => {
    setIsOpen(false);
    // Don't clear selectedId immediately to allow exit animation
  }, []);

  const clearThread = useCallback(() => {
    setSelectedIndex(null);
  }, []);

  const toggleBulkSelect = useCallback((id: string) => {
    setSelectedBulkIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const clearBulkSelect = useCallback(() => {
    setSelectedBulkIds(new Set());
  }, []);

  // TODO(thread-viewer v1.4.6):
  // We now provide user feedback + rollback.
  // Long term:
  //  - Push handledCount + item flags back into parent list source of truth

  const bulkArchive = useCallback(async () => {
    const ids = Array.from(selectedBulkIds);
    if (ids.length === 0) return;

    setIsBulkMutating(true);
    const before = items; // snapshot

    // optimistic
    setItems(prev =>
      prev.map(it =>
        ids.includes(it.id)
          ? { ...it, archived: true }
          : it
      )
    );

    try {
      const res = await bulkArchiveMessages(ids);

      // Handle partial success
      if (res.failed.length > 0) {
        // Surgical rollback: restore only the failed IDs
        setItems(prev =>
          prev.map(it =>
            res.failed.includes(it.id)
              ? { ...it, archived: before.find(b => b.id === it.id)?.archived || false }
              : it
          )
        );

        if (res.updated.length > 0) {
          // Partial success
          toast.warning(`🟡 Archived ${res.updated.length}/${ids.length} threads`, {
            description: `${res.failed.length} failed. Try again or contact support.`,
          });
        } else {
          // Complete failure
          toast.error("Archive failed", {
            description: "Those threads could not be archived.",
          });
        }
      } else {
        // Complete success - show undo action
        const successfulIds = res.updated;

        // Track successful bulk action
        track({ name: 'bulk_action', action: 'archive', count: successfulIds.length });

        toast.success(`📥 Archived ${ids.length} thread${ids.length === 1 ? "" : "s"}`, {
          action: {
            label: "Undo",
            onClick: () => {
              // Restore archived state for successful IDs
              setItems(prev =>
                prev.map(it =>
                  successfulIds.includes(it.id)
                    ? { ...it, archived: before.find(b => b.id === it.id)?.archived || false }
                    : it
                )
              );

              // Track undo action
              track({ name: 'bulk_action_undo', action: 'archive', count: successfulIds.length });

              toast.success("↩️ Undone");
            },
          },
        });
      }
    } catch (err) {
      // Network error - full rollback
      setItems(before);
      toast.error("Archive failed", {
        description: "Those threads could not be archived.",
      });
    } finally {
      clearBulkSelect();
      setIsBulkMutating(false);
    }
  }, [selectedBulkIds, items, clearBulkSelect]);

  const bulkMarkSafe = useCallback(async () => {
    const ids = Array.from(selectedBulkIds);
    if (ids.length === 0) return;

    setIsBulkMutating(true);
    const before = items;

    setItems(prev =>
      prev.map(it =>
        ids.includes(it.id)
          ? { ...it, quarantined: false }
          : it
      )
    );

    try {
      const res = await bulkMarkSafeMessages(ids);

      // Handle partial success
      if (res.failed.length > 0) {
        // Surgical rollback: restore only the failed IDs
        setItems(prev =>
          prev.map(it =>
            res.failed.includes(it.id)
              ? { ...it, quarantined: before.find(b => b.id === it.id)?.quarantined || false }
              : it
          )
        );

        if (res.updated.length > 0) {
          // Partial success
          toast.warning(`🟡 Marked ${res.updated.length}/${ids.length} safe`, {
            description: `${res.failed.length} failed. Try again or contact support.`,
          });
        } else {
          // Complete failure
          toast.error("Mark Safe failed", {
            description: "We couldn't update those threads.",
          });
        }
      } else {
        // Complete success - show undo action
        const successfulIds = res.updated;

        // Track successful bulk action
        track({ name: 'bulk_action', action: 'mark_safe', count: successfulIds.length });

        toast.success(`✅ Marked ${ids.length} safe`, {
          action: {
            label: "Undo",
            onClick: () => {
              // Restore quarantined state for successful IDs
              setItems(prev =>
                prev.map(it =>
                  successfulIds.includes(it.id)
                    ? { ...it, quarantined: before.find(b => b.id === it.id)?.quarantined || false }
                    : it
                )
              );

              // Track undo action
              track({ name: 'bulk_action_undo', action: 'mark_safe', count: successfulIds.length });

              toast.success("↩️ Undone");
            },
          },
        });
      }
    } catch (err) {
      // Network error - full rollback
      setItems(before);
      toast.error("Mark Safe failed", {
        description: "We couldn't update those threads.",
      });
    } finally {
      clearBulkSelect();
      setIsBulkMutating(false);
    }
  }, [selectedBulkIds, items, clearBulkSelect]);

  const bulkQuarantine = useCallback(async () => {
    const ids = Array.from(selectedBulkIds);
    if (ids.length === 0) return;

    setIsBulkMutating(true);
    const before = items;

    setItems(prev =>
      prev.map(it =>
        ids.includes(it.id)
          ? { ...it, quarantined: true }
          : it
      )
    );

    try {
      const res = await bulkQuarantineMessages(ids);

      // Handle partial success
      if (res.failed.length > 0) {
        // Surgical rollback: restore only the failed IDs
        setItems(prev =>
          prev.map(it =>
            res.failed.includes(it.id)
              ? { ...it, quarantined: before.find(b => b.id === it.id)?.quarantined || false }
              : it
          )
        );

        if (res.updated.length > 0) {
          // Partial success
          toast.warning(`� Quarantined ${res.updated.length}/${ids.length}`, {
            description: `${res.failed.length} failed. Try again or contact support.`,
          });
        } else {
          // Complete failure
          toast.error("Quarantine failed", {
            description: "We couldn't quarantine those threads.",
          });
        }
      } else {
        // Complete success - show undo action
        const successfulIds = res.updated;

        // Track successful bulk action
        track({ name: 'bulk_action', action: 'quarantine', count: successfulIds.length });

        toast.success(`🔒 Quarantined ${ids.length}`, {
          action: {
            label: "Undo",
            onClick: () => {
              // Restore quarantined state for successful IDs
              setItems(prev =>
                prev.map(it =>
                  successfulIds.includes(it.id)
                    ? { ...it, quarantined: before.find(b => b.id === it.id)?.quarantined || false }
                    : it
                )
              );

              // Track undo action
              track({ name: 'bulk_action_undo', action: 'quarantine', count: successfulIds.length });

              toast.success("↩️ Undone");
            },
          },
        });
      }
    } catch (err) {
      // Network error - full rollback
      setItems(before);
      toast.error("Quarantine failed", {
        description: "We couldn't quarantine those threads.",
      });
    } finally {
      clearBulkSelect();
      setIsBulkMutating(false);
    }
  }, [selectedBulkIds, items, clearBulkSelect]);

  // TODO(thread-viewer v1.3):
  // We'll expose a way for parent pages to update the `items` list
  // if the visible rows change due to filtering, search, etc.
  // For now, assume items is static for the page render.

  // TODO(thread-viewer v1.2):
  // We will extend this hook to accept an optional config:
  //
  //   useThreadViewer({
  //     onThreadMutate(updated) {
  //        // parent page (Inbox/Search/Actions) can update its list rows
  //        // e.g. mark archived/quarantined without re-fetch
  //     }
  //   })
  //
  // Then ThreadViewer can call that after optimistic updates.

  return {
    // state
    isOpen,
    selectedId,
    selectedIndex,
    items,

    // actions
    showThread,
    closeThread,
    clearThread,
    goPrev,
    goNext,
    advanceAfterAction,

    // NEW Phase 4
    autoAdvance,
    setAutoAdvance,

    selectedBulkIds,
    toggleBulkSelect,
    clearBulkSelect,
    bulkArchive,
    bulkMarkSafe,
    bulkQuarantine,
    isBulkMutating,
  };
}
