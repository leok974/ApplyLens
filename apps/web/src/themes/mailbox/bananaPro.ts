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
    // No full-page ambient glow - keep it clean
    ambientGlow: "none",
    // tighter, hotter glow for active pills/buttons
    activeGlow: "0 0 20px rgba(250,204,21,0.55)",
  },

  // Page frame - clean canvas with no muddy overlays
  frame: {
    canvas: "bg-slate-950",
    backdrop: "bg-slate-950", // solid, no gradient overlays
  },

  // Hero header - tighter localized glow
  hero: {
    container: "bg-slate-950/80 border border-yellow-400/15 rounded-3xl",
    glow: "0 0 60px rgba(250,204,21,0.30)", // tighter hero glow, not full-page
    iconRing: "rgba(250,204,21,0.7)",
    iconGlow: "0 0 40px rgba(250,204,21,0.6)",
    badgeBg: "linear-gradient(to right, rgba(250,204,21,0.9), rgb(251,191,36))",
    badgeText: "#0f172a",
    badgeGlow: "0 0 18px rgba(250,204,21,0.7)",
  },

  // Chat shell - subtle glow, not full-page
  shell: {
    container: "bg-slate-950/80 border border-yellow-400/10 rounded-3xl overflow-hidden",
    glow: "0 0 80px rgba(250,204,21,0.28)", // subtle shell glow
  },

  // Chat shell border (deprecated, kept for compatibility)
  chatShell: {
    borderTop: "rgba(250,204,21,0.6)",
  },

  // Tool pill styling - minimal glows
  tool: {
    default: {
      bg: "transparent",
      border: "rgba(253,224,71,0.1)",
      text: "rgb(226,232,240)",
    },
    hover: {
      bg: "rgba(250,204,21,0.05)", // lighter hover tint
      border: "rgba(253,224,71,0.3)",
      text: "rgb(241,245,249)",
      scale: "1.02",
    },
    active: {
      bg: "linear-gradient(to bottom right, rgb(250,204,21), rgb(252,211,77))",
      text: "rgb(15,23,42)",
      glow: "0 0 20px rgba(250,204,21,0.5)", // smaller active glow
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

  // Primary button (send button) - strongest glow element
  primaryButton: {
    bg: "linear-gradient(to bottom right, rgb(250,204,21), rgb(251,191,36))",
    glow: "0 0 30px rgba(250,204,21,0.7)", // tighter, stronger glow
    hoverGlow: "0 0 40px rgba(250,204,21,0.9)",
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
