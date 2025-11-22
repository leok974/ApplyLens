import { MailboxTheme } from "./types";

export const deepSpaceTheme: MailboxTheme = {
  id: "deepSpace",
  label: "Deep Space Cockpit",
  description:
    "Nebula-backed cockpit with electric cyan controls and banana-yellow AI highlights.",

  colors: {
    // the void
    bgCanvas: "#020617",                // near-black navy
    bgSurfaceElevated: "#020617",       // main shell sits here with border/glow
    bgSurfaceInteractive: "rgba(15,23,42,0.96)", // for inputs / inner panels

    // accents
    accentPrimary: "#22d3ee",           // electric cyan for actions/tools
    accentGlow: "rgba(34,211,238,0.8)",
    accentSubtle: "rgba(34,211,238,0.08)",

    // functional / status
    intentDanger: "#f97316",            // warning orange-red for Suspicious
    intentInfo: "#22d3ee",              // cyan for Bills/Followups
    intentSuccess: "#2dd4bf",           // cyan-green for Interviews/opportunities

    // typography
    textPrimary: "#e5e7eb",             // off-white
    textMuted: "#9ca3af",               // cool grey
    textOnAccent: "#020617",            // dark on bright cyan/yellow where needed

    // borders/dividers
    borderSubtle: "rgba(148,163,184,0.28)", // faint cyan-slate
    focusRing: "#22d3ee",               // sharp cyan focus ring
  },

  radii: {
    pill: 999,
    xl: 20,                             // slightly tighter than Banana Pro
  },

  shadows: {
    ambientGlow:
      "0 0 100px rgba(34,211,238,0.22), 0 0 160px rgba(15,23,42,0.9)",
    activeGlow: "0 0 24px rgba(34,211,238,0.8)",
  },

  layout: {
    heroHeight: "compact",              // slimmer header strip
    shellMaxWidth: 1200,
    shellPinnedHeader: true,            // canopy + header + tools pinned
    inputDock: "shell-bottom",
    showNebulaBackground: true,         // starfield / nebula backdrop
    showHeaderGlow: true,               // warm yellow AI strip under header
  },

  chat: {
    userBubbleOnRight: true,
    assistantBubbleBorderGlows: true,   // warm yellow rim light on AI bubbles
    showThinkingDots: true,             // banana-yellow "analyzing" pulse
  },

  cards: {
    leftIntentStrip: false,             // Deep Space uses full-card accent glow
    headerMetricsPill: true,            // monospaced counts in header
    hoverHighlightUsesIntentColor: true // row highlight w/ cyan/orange glow
  },
};
