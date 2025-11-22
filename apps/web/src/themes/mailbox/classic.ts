import { MailboxTheme } from "./types";

export const classicTheme: MailboxTheme = {
  id: "classic",
  label: "Classic",
  description:
    "Neutral dark theme with slate tones and subtle sky-blue accents.",

  colors: {
    // backgrounds
    bgCanvas: "#020617",                // slate-950
    bgSurfaceElevated: "rgba(15,23,42,0.8)",  // slate-900/80
    bgSurfaceInteractive: "rgba(30,41,59,0.9)", // slate-800/90

    // accents
    accentPrimary: "#0ea5e9",           // sky-500
    accentGlow: "rgba(14,165,233,0.6)",
    accentSubtle: "rgba(14,165,233,0.1)",

    // functional intents
    intentDanger: "#ef4444",            // red-500 for Suspicious
    intentInfo: "#0ea5e9",              // sky-500 for Bills
    intentSuccess: "#10b981",           // emerald-500 for Interviews

    // typography
    textPrimary: "#f8fafc",             // slate-50
    textMuted: "#94a3b8",               // slate-400
    textOnAccent: "#020617",            // dark slate on bright colors

    // borders/focus
    borderSubtle: "rgba(148,163,184,0.3)", // slate-400/30
    focusRing: "#0ea5e9",               // sky-500
  },

  radii: {
    pill: 999,   // fully rounded
    xl: 16,      // for chat shell & cards
  },

  shadows: {
    ambientGlow: "0 0 60px rgba(15,23,42,0.5)",
    activeGlow: "0 0 16px rgba(14,165,233,0.4)",
  },

  layout: {
    heroHeight: "tall",
    shellMaxWidth: 1040,
    shellPinnedHeader: false,     // classic scrolls naturally
    inputDock: "shell-bottom",
    showNebulaBackground: false,
    showHeaderGlow: false,        // no special header glow in classic
  },

  chat: {
    userBubbleOnRight: true,
    assistantBubbleBorderGlows: false,  // no special glow in classic
    showThinkingDots: true,
  },

  cards: {
    leftIntentStrip: true,              // colored left border
    headerMetricsPill: true,
    hoverHighlightUsesIntentColor: false // neutral hover in classic
  },
};
