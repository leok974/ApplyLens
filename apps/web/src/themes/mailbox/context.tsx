import {
  createContext,
  useContext,
  type ReactNode,
} from "react";
import type { MailboxTheme } from "./types";
import { MAILBOX_THEMES } from "./index";
import { useMailboxTheme } from "@/hooks/useMailboxTheme";

const MailboxThemeContext = createContext<MailboxTheme>(
  MAILBOX_THEMES.classic,
);

export function MailboxThemeProvider({ children }: { children: ReactNode }) {
  const { theme } = useMailboxTheme();
  return (
    <MailboxThemeContext.Provider value={theme}>
      {children}
    </MailboxThemeContext.Provider>
  );
}

export function useMailboxThemeContext() {
  return useContext(MailboxThemeContext);
}
