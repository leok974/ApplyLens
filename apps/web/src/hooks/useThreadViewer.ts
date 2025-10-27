import { useState, useCallback } from 'react';

/**
 * Hook for managing thread viewer state across pages
 * Provides consistent selection and open/close behavior
 * Now with keyboard navigation support (Phase 3)
 */
export function useThreadViewer(initialItems?: { id: string }[]) {
  const [items, setItems] = useState<{ id: string }[]>(initialItems ?? []);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [isOpen, setIsOpen] = useState(false);

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
    // jumps to next item, if possible
    setSelectedIndex((prev) => {
      if (prev == null) return prev;
      const next = prev + 1;
      return next >= items.length ? prev : next;
    });
    setIsOpen(true);
  }, [items.length]);

  const closeThread = useCallback(() => {
    setIsOpen(false);
    // Don't clear selectedId immediately to allow exit animation
  }, []);

  const clearThread = useCallback(() => {
    setSelectedIndex(null);
  }, []);

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
  };
}
