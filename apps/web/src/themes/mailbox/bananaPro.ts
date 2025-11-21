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

  // Hero header styling
  hero: {
    bg: "linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.92) 50%, rgba(15,23,42,0.95) 100%)",
    glow: "0 8px 40px rgba(250,204,21,0.25), 0 0 80px rgba(59,130,246,0.15)",
    iconRing: "rgba(250,204,21,0.7)",
    iconGlow: "0 0 40px rgba(250,204,21,0.6)",
    badgeBg: "linear-gradient(to right, rgba(250,204,21,0.9), rgb(251,191,36))",
    badgeText: "#0f172a",
    badgeGlow: "0 0 18px rgba(250,204,21,0.7)",
  },

  // Chat shell styling
  chatShell: {
    bg: "rgba(15,23,42,0.85)",
    borderTop: "rgba(250,204,21,0.6)",
    glowTop: "0 -8px 40px rgba(250,204,21,0.35)",
  },

  // Tool pill styling
  tool: {
    default: {
      bg: "transparent",
      border: "rgba(253,224,71,0.1)",
      text: "rgb(226,232,240)",
    },
    hover: {
      bg: "rgba(250,204,21,0.1)",
      border: "rgba(253,224,71,0.4)",
      text: "rgb(241,245,249)",
      scale: "1.02",
    },
    active: {
      bg: "linear-gradient(to right, rgb(250,204,21), rgb(252,211,77))",
      text: "rgb(15,23,42)",
      glow: "0 0 24px rgba(250,204,21,0.6)",
    },
  },

  // Input bar styling
  inputBar: {
    bg: "rgba(2,6,23,0.9)",
    border: "rgba(253,224,71,0.2)",
    glow: "0 0 32px rgba(15,23,42,0.9)",
    placeholderText: "rgb(100,116,139)",
    caretColor: "rgb(250,204,21)",
    toggleTrackActive: "rgba(250,204,21,0.6)",
    toggleThumb: "rgb(2,6,23)",
    toggleGlow: "0 0 12px rgba(250,204,21,0.7)",
  },

  // Primary button (send button)
  primaryButton: {
    bg: "linear-gradient(to bottom right, rgb(250,204,21), rgb(251,191,36))",
    glow: "0 0 24px rgba(250,204,21,0.8)",
    hoverGlow: "0 0 36px rgba(250,204,21,1)",
  },

  // Card intent strips
  card: {
    intent: {
      suspicious: {
        stripColor: "rgb(251,146,60)",
        stripGlow: "0 0 24px rgba(251,146,60,0.7)",
        hoverBg: "rgba(251,146,60,0.05)",
      },
      bills: {
        stripColor: "rgb(34,211,238)",
        stripGlow: "0 0 24px rgba(34,211,238,0.7)",
        hoverBg: "rgba(34,211,238,0.05)",
      },
      followups: {
        stripColor: "rgb(52,211,153)",
        stripGlow: "0 0 24px rgba(52,211,153,0.7)",
        hoverBg: "rgba(52,211,153,0.05)",
      },
    },
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
