import { useEffect, useMemo, useState } from "react";
import {
  MAILBOX_THEMES,
  type MailboxTheme,
  type MailboxThemeId,
} from "@/themes/mailbox";

const STORAGE_KEY = "applylens:mailbox-theme";

const DEFAULT_THEME_ID: MailboxThemeId = "classic";

export function useMailboxTheme() {
  const [themeId, setThemeId] = useState<MailboxThemeId>(DEFAULT_THEME_ID);

  // initial load from localStorage
  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY) as
        | MailboxThemeId
        | null;
      if (stored && MAILBOX_THEMES[stored]) {
        setThemeId(stored);
      }
    } catch {
      // ignore
    }
  }, []);

  // persist on change
  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, themeId);
    } catch {
      // ignore
    }
  }, [themeId]);

  const theme: MailboxTheme = useMemo(
    () => MAILBOX_THEMES[themeId] ?? MAILBOX_THEMES[DEFAULT_THEME_ID],
    [themeId],
  );

  const availableThemes = useMemo(
    () => Object.values(MAILBOX_THEMES),
    [],
  );

  return {
    themeId,
    theme,
    setThemeId, // accepts MailboxThemeId
    availableThemes,
  };
}
