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

  // Enhanced tokens for Banana Pro visual polish
  frame?: {
    canvas: string;       // Page background
    backdrop: string;     // Optional gradient overlay (very subtle)
    container?: string;   // Tailwind classes for frame container
    glow?: string;        // Box shadow for frame (should be "shadow-none" for Banana Pro)
  };

  hero?: {
    container: string;    // Tailwind classes for hero card
    glow: string;         // Box shadow for hero card (localized)
    iconRing: string;     // Outline color for assistant icon
    iconGlow: string;     // Shadow for assistant icon
    badgeBg: string;      // Background gradient for "Agent V2" badge
    badgeText: string;    // Text color for badge
    badgeGlow: string;    // Shadow for badge
  };

  shell?: {
    container: string;    // Tailwind classes for chat shell
    glow: string;         // Box shadow for shell (localized)
  };

  chatShell?: {
    borderTop: string;    // Top border color (deprecated, use shell.container instead)
  };

  tool?: {
    default: {
      bg: string;
      border: string;
      text: string;
    };
    hover: {
      bg: string;
      border: string;
      text: string;
      scale?: string;     // Transform scale on hover
    };
    active: {
      bg: string;
      text: string;
      glow: string;
    };
  };

  inputBar?: {
    bg: string;
    border: string;
    glow: string;
    placeholderText: string;
    caretColor: string;
    toggleTrackActive: string;
    toggleThumb: string;
    toggleGlow: string;
  };

  primaryButton?: {
    bg: string;
    glow: string;
    hoverGlow: string;
  };

  card?: {
    intent: {
      suspicious: {
        stripColor: string;
        stripGlow: string;
        hoverBg?: string;
      };
      bills: {
        stripColor: string;
        stripGlow: string;
        hoverBg?: string;
      };
      followups: {
        stripColor: string;
        stripGlow: string;
        hoverBg?: string;
      };
    };
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
