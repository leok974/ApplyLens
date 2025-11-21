import { MailboxTheme } from "./types";
import { classicTheme } from "./classic";
import { bananaProTheme } from "./bananaPro";
import { deepSpaceTheme } from "./deepSpace";

export const MAILBOX_THEMES: Record<MailboxTheme["id"], MailboxTheme> = {
  classic: classicTheme,
  bananaPro: bananaProTheme,
  deepSpace: deepSpaceTheme,
};

// Re-export types and themes for convenience
export * from "./types";
export { classicTheme, bananaProTheme, deepSpaceTheme };
