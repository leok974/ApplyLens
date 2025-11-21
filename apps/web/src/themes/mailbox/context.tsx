import {
  createContext,
  useContext,
  useEffect,
  useState,
  useMemo,
  type ReactNode,
} from "react";
import { MAILBOX_THEMES } from "@/themes/mailbox";
import type { MailboxTheme, MailboxThemeId } from "@/themes/mailbox/types";

type MailboxThemeContextValue = {
  themeId: MailboxThemeId;
  theme: MailboxTheme;
  setThemeId: (id: MailboxThemeId) => void;
  availableThemes: MailboxTheme[];
};

const STORAGE_KEY = "applylens:mailbox-theme";
const DEFAULT_THEME_ID: MailboxThemeId = "classic";

// Default value only used before provider mounts
const MailboxThemeContext = createContext<MailboxThemeContextValue>({
  themeId: DEFAULT_THEME_ID,
  theme: MAILBOX_THEMES[DEFAULT_THEME_ID],
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  setThemeId: () => {},
  availableThemes: Object.values(MAILBOX_THEMES),
});

function getInitialThemeId(): MailboxThemeId {
  if (typeof window === "undefined") return DEFAULT_THEME_ID;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY) as MailboxThemeId | null;
    if (stored && MAILBOX_THEMES[stored]) {
      return stored;
    }
  } catch {
    // ignore
  }
  return DEFAULT_THEME_ID;
}

export function MailboxThemeProvider({ children }: { children: ReactNode }) {
  const [themeId, setThemeIdState] = useState<MailboxThemeId>(getInitialThemeId);

  // Sync to localStorage when themeId changes
  useEffect(() => {
    if (typeof window === "undefined") return;
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

  const availableThemes = useMemo(() => Object.values(MAILBOX_THEMES), []);

  const setThemeId = (id: MailboxThemeId) => {
    if (!MAILBOX_THEMES[id]) return;
    setThemeIdState(id);
  };

  const value = useMemo(
    () => ({ themeId, theme, setThemeId, availableThemes }),
    [themeId, theme, availableThemes],
  );

  return (
    <MailboxThemeContext.Provider value={value}>
      {children}
    </MailboxThemeContext.Provider>
  );
}

export function useMailboxThemeContext(): MailboxThemeContextValue {
  return useContext(MailboxThemeContext);
}
