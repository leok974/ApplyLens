import type { MailboxThemeId, MailboxTheme } from "./types";
import { MAILBOX_THEMES } from "./index";

export type MailboxThemeClassSlots = {
  page: string;
  chatShell: string;
  chatShellBorder: string;
  toolPill: string;
  toolPillActive: string;
  toolPillIcon: string;
  agentCardBase: string;
  agentCardHeader: string;
  agentCardFooter: string;
  intentStripSuspicious: string;
  intentStripBills: string;
  intentStripFollowups: string;
};

export function getMailboxTheme(themeId: MailboxThemeId): MailboxTheme {
  return MAILBOX_THEMES[themeId] ?? MAILBOX_THEMES.classic;
}

export function getMailboxThemeClasses(themeId: MailboxThemeId): MailboxThemeClassSlots {
  const theme = getMailboxTheme(themeId);
  // NOTE: For now, hard-code Tailwind classes per theme.
  // You can later refine these using theme.tokens if you want.
  switch (theme.id) {
    case "bananaPro":
      return {
        page: "bg-[#050609] text-slate-50",
        chatShell:
          "bg-slate-900/70 backdrop-blur-xl rounded-3xl border border-yellow-500/40 shadow-[0_0_40px_rgba(234,179,8,0.25)]",
        chatShellBorder: "border-t-2 border-yellow-400/80",
        toolPill:
          "border border-slate-600/60 text-slate-300 hover:border-yellow-400 hover:bg-yellow-400/5 hover:text-slate-50",
        toolPillActive:
          "bg-gradient-to-r from-yellow-400 to-yellow-300 text-slate-900 shadow-[0_0_20px_rgba(250,204,21,0.55)]",
        toolPillIcon: "text-yellow-300",
        agentCardBase:
          "bg-slate-900/80 border border-slate-700/70 rounded-3xl shadow-[0_0_40px_rgba(15,23,42,0.8)]",
        agentCardHeader: "text-slate-50",
        agentCardFooter: "border-t border-slate-700/60 text-slate-400",
        intentStripSuspicious: "bg-orange-500 shadow-[0_0_24px_rgba(249,115,22,0.7)]",
        intentStripBills: "bg-cyan-400 shadow-[0_0_24px_rgba(34,211,238,0.7)]",
        intentStripFollowups:
          "bg-emerald-400 shadow-[0_0_24px_rgba(52,211,153,0.7)]",
      };
    case "deepSpace":
      return {
        page: "bg-[#020617] text-slate-50",
        chatShell:
          "bg-slate-900/80 backdrop-blur-2xl rounded-3xl border border-cyan-500/40 shadow-[0_0_50px_rgba(34,211,238,0.38)]",
        chatShellBorder: "border-t-2 border-cyan-400/80",
        toolPill:
          "border border-cyan-800/60 text-slate-300 hover:border-cyan-300 hover:bg-cyan-400/5 hover:text-slate-50",
        toolPillActive:
          "bg-cyan-500/80 text-slate-900 shadow-[0_0_24px_rgba(34,211,238,0.65)]",
        toolPillIcon: "text-cyan-300",
        agentCardBase:
          "bg-slate-900/80 border border-slate-800/80 rounded-3xl shadow-[0_0_40px_rgba(15,23,42,0.9)]",
        agentCardHeader: "text-slate-50",
        agentCardFooter: "border-t border-slate-800/80 text-slate-400",
        intentStripSuspicious: "bg-orange-500 shadow-[0_0_24px_rgba(248,113,113,0.7)]",
        intentStripBills: "bg-cyan-400 shadow-[0_0_24px_rgba(34,211,238,0.7)]",
        intentStripFollowups:
          "bg-emerald-400 shadow-[0_0_24px_rgba(52,211,153,0.7)]",
      };
    case "classic":
    default:
      return {
        page: "bg-slate-950 text-slate-50",
        chatShell:
          "bg-slate-900/80 rounded-2xl border border-slate-800 shadow-xl",
        chatShellBorder: "border-t border-slate-700",
        toolPill:
          "border border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-slate-50",
        toolPillActive: "bg-slate-100 text-slate-900",
        toolPillIcon: "text-slate-300",
        agentCardBase: "bg-slate-900 border border-slate-800 rounded-2xl",
        agentCardHeader: "text-slate-50",
        agentCardFooter: "border-t border-slate-800 text-slate-400",
        intentStripSuspicious: "bg-red-500",
        intentStripBills: "bg-sky-500",
        intentStripFollowups: "bg-emerald-500",
      };
  }
}
