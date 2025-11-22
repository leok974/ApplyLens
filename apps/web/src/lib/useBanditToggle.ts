// apps/web/src/lib/useBanditToggle.ts
import { useEffect, useState } from "react";
import {
  initBanditFlagFromStorage,
  writeBanditEnabled,
} from "./banditToggle";

export function useBanditToggle() {
  const [enabled, setEnabled] = useState<boolean>(() => {
    // Initialize window flag + read storage on first render (client)
    if (typeof window === "undefined") return true;
    return initBanditFlagFromStorage();
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    writeBanditEnabled(enabled);
  }, [enabled]);

  return {
    enabled,
    setEnabled,
  };
}
