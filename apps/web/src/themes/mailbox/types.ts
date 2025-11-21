export type MailboxThemeId = "classic" | "bananaPro" | "deepSpace";

export interface MailboxTheme {
  id: MailboxThemeId;
  label: string;
  description: string;

  // core design tokens
  colors: {
    // backgrounds
    bgCanvas: string;
    bgSurfaceElevated: string;
    bgSurfaceInteractive: string;

    // accents
    accentPrimary: string;
    accentGlow: string;
    accentSubtle: string;

    // functional intents
    intentDanger: string;
    intentInfo: string;
    intentSuccess: string;

    // text
    textPrimary: string;
    textMuted: string;
    textOnAccent: string;

    // borders/focus
    borderSubtle: string;
    focusRing: string;
  };

  radii: {
    pill: number;        // px
    xl: number;          // px
  };

  shadows: {
    ambientGlow: string; // big soft shadow token
    activeGlow: string;  // tighter glow for active pills/buttons
  };

  layout: {
    heroHeight: "compact" | "tall";
    shellMaxWidth: number;       // px
    shellPinnedHeader: boolean;  // header + tools pinned
    inputDock: "shell-bottom" | "page-bottom";
    showNebulaBackground: boolean;
    showHeaderGlow: boolean;
  };

  // chat + cards behaviour knobs (for MailChat)
  chat: {
    userBubbleOnRight: boolean;
    assistantBubbleBorderGlows: boolean;
    showThinkingDots: boolean;
  };

  cards: {
    leftIntentStrip: boolean;
    headerMetricsPill: boolean;
    hoverHighlightUsesIntentColor: boolean;
  };
}
