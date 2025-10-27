import { useState, useCallback } from 'react';

/**
 * Hook for managing thread viewer state across pages
 * Provides consistent selection and open/close behavior
 */
export function useThreadViewer() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const showThread = useCallback((id: string) => {
    setSelectedId(id);
    setIsOpen(true);
  }, []);

  const closeThread = useCallback(() => {
    setIsOpen(false);
    // Don't clear selectedId immediately to allow exit animation
  }, []);

  const clearThread = useCallback(() => {
    setSelectedId(null);
  }, []);

  return {
    selectedId,
    isOpen,
    showThread,
    closeThread,
    clearThread,
  };
}
