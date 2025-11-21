import { MailboxTheme } from "./types";

export const bananaProTheme: MailboxTheme = {
  id: "bananaPro",
  label: "Banana Pro",
  description:
    "Dark SaaS cockpit with glowing banana-yellow energy and soft, elevated cards.",

  colors: {
    // deep, slightly cool slate/navy
    bgCanvas: "#020617",              // very dark navy
    bgSurfaceElevated: "rgba(15,23,42,0.96)",  // deep slate w/ slight translucency
    bgSurfaceInteractive: "#020617",  // medium-dark slate for hover / inputs

    // banana accents
    accentPrimary: "#facc15",         // vibrant yellow-gold
    accentGlow: "#f59e0b",            // richer gold for glows
    accentSubtle: "rgba(250,204,21,0.08)",

    // functional intents (lit by banana)
    intentDanger: "#fb923c",          // orange-red for Suspicious
    intentInfo: "#22d3ee",            // cyan/teal for Bills
    intentSuccess: "#22c55e",         // emerald for Interviews

    // typography
    textPrimary: "#e5e7eb",           // near-white
    textMuted: "#9ca3af",             // cool grey
    textOnAccent: "#020617",          // dark slate on yellow

    // borders & focus
    borderSubtle: "rgba(148,163,184,0.35)",
    focusRing: "#facc15",
  },

  radii: {
    pill: 999,   // fully rounded
    xl: 24,      // for chat shell & cards
  },

  shadows: {
    // faint blue-purple ambient with a hint of yellow
    ambientGlow:
      "0 0 80px rgba(59,130,246,0.18), 0 0 140px rgba(250,204,21,0.12)",
    // tighter, hotter glow for active pills/buttons
    activeGlow: "0 0 20px rgba(250,204,21,0.55)",
  },

  layout: {
    heroHeight: "tall",
    shellMaxWidth: 1100,
    shellPinnedHeader: true,      // hero + tool strip stay pinned
    inputDock: "shell-bottom",    // input attached to chat shell
    showNebulaBackground: false,  // Banana Pro is more SaaS than nebula
    showHeaderGlow: true,         // warm yellow glow under hero bar
  },

  chat: {
    userBubbleOnRight: true,
    assistantBubbleBorderGlows: true,  // thin yellow ring around assistant bubble
    showThinkingDots: true,            // pulsing 3-dot loader in banana-yellow
  },

  cards: {
    leftIntentStrip: true,              // 6px glowing strip on the left
    headerMetricsPill: true,            // "3 items · last 30 days" pill
    hoverHighlightUsesIntentColor: true // row highlight tinted by intent
  },
};
