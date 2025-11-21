# Mailbox Theme System – Design Document

## 0. What we're building

**Goal**: A "Layout & Theme" system where a user can go to **Settings → Appearance** and choose:

1. **Classic** (current design)
2. **Banana Pro** (Prompt 1 – warm banana SaaS)
3. **Deep Space Cockpit** (Prompt 2 – nebula / cockpit)

The choice should:

- Change colors, radii, shadows, and icon styling (theme)
- Slightly adjust layout for the Mailbox Assistant header + chat shell (layout)
- Persist per user (and fall back to Classic if anything breaks)

---

## 1. Define the concept: Theme vs Layout Variant

Internally, keep two concepts:

- **Theme** – token set (colors, radii, typography, glow level)
- **Layout variant** – structural tweaks for the `/chat` page (e.g., hero height, card grouping, where status text sits)

### Plan

```typescript
ThemeId = "classic" | "bananaPro" | "deepSpace"
MailboxLayoutId = "classic" | "bananaPro" | "deepSpace"
```

In v1 you can keep them 1:1 (theme and layout share the same id). Later you can mix them.

---

## 2. Create a "theme packet" format

Make a small TypeScript interface that can live in one place (e.g. `apps/web/src/themes/mailbox/types.ts`):

```typescript
type MailboxThemeId = "classic" | "bananaPro" | "deepSpace";

interface MailboxTheme {
  id: MailboxThemeId;
  displayName: string;        // "Banana Pro", "Deep Space Cockpit"
  description: string;        // Short explainer for Settings

  // design tokens
  colors: {
    pageBg: string;
    shellBg: string;
    shellBorder: string;
    toolDefaultBg: string;
    toolActiveBg: string;
    toolActiveBorder: string;
    chatBubbleUserBg: string;
    chatBubbleAssistantBg: string;
    cardBg: string;
    cardAccentSuspicious: string;
    cardAccentBills: string;
    cardAccentFollowups: string;
    primaryText: string;
    mutedText: string;
    warning: string;
    success: string;
  };

  radii: {
    shell: "md" | "lg" | "xl";
    pill: "full" | "xl";
    card: "lg" | "xl";
  };

  shadows: {
    shell: "subtle" | "glow";
    toolActive: "glow" | "none";
    primaryButton: "glow" | "raised";
  };

  // layout tuning knobs
  layout: {
    headerHeight: "compact" | "tall";
    shellMaxWidth: number;     // e.g. 1040
    showNebulaBg: boolean;
    showHeaderGlow: boolean;
    inputDockStyle: "inline" | "floating";
  };
}
```

### File structure

Create one file per theme:

- `apps/web/src/themes/mailbox/classic.ts`
- `apps/web/src/themes/mailbox/bananaPro.ts`
- `apps/web/src/themes/mailbox/deepSpace.ts`

Each file exports a `MailboxTheme` object that you fill from the Gemini spec.

---

## 3. Map the Gemini specs → tokens

Once you paste the specs from Prompt 1 and Prompt 2, we'll:

1. Extract palette + radii + shadows → fill `colors`, `radii`, `shadows`
2. Translate layout notes (hero height, nebula background, glows) → `layout` fields

### Plan

- Paste **Prompt-1 Gemini spec** → map to `bananaPro` tokens
- Paste **Prompt-2 Gemini spec** → map to `deepSpace` tokens

This keeps the fun descriptive spec in Gemini and a concrete token packet in your code.

---

## 4. Theme registry + hook

Create a simple registry:

```typescript
const MAILBOX_THEMES: Record<MailboxThemeId, MailboxTheme> = {
  classic,
  bananaPro,
  deepSpace,
};
```

Expose a hook/context:

```typescript
useMailboxTheme() → returns the currently selected MailboxTheme
```

It looks up the current theme id from a `SettingsContext` or Zustand store.

### Storage plan

- **For logged-in users**: save preference in your backend profile (you already have `/api/profile/me` for the Companion; you can piggyback or add a simple `/settings` field later)
- **For now, v1**: just use `localStorage` under `applylens:mailboxTheme`

---

## 5. Apply theme to the Mailbox Assistant UI

You don't have to refactor the whole app; focus on `/chat` first.

### 5.1. MailChat shell

In `MailChat.tsx`:

Instead of hard-coded Tailwind colors, pull from the theme:

- Shell background → `theme.colors.shellBg`
- Shell border → `theme.colors.shellBorder`
- Max width → `theme.layout.shellMaxWidth`

**Implementation detail** (later): you can do this via:

- Data attributes + CSS variables (`data-theme="bananaPro"`) or
- Mapping tokens → Tailwind class names (`bg-slate-950` vs `bg-[#050816]`, etc.)

**Plan-wise**, the important part is: all visual choices for MailChat should go through the theme object, not inline literals.

### 5.2. Tool pills (Summarize, Bills, …)

For each tool:

**Default state**:
- Background: `theme.colors.toolDefaultBg`
- Border: transparent or `shellBorder`

**Active state**:
- Background: `theme.colors.toolActiveBg`
- Border + glow: `theme.colors.toolActiveBorder`, `shadows.toolActive`
- Icon color: derived from `primaryText` or per-tool accent (`Suspicious` uses `cardAccentSuspicious` etc.)

"Banana Pro" would use warm banana gradient; "Deep Space" uses electric cyan with subtle glow.

### 5.3. Chat bubbles

**User bubble**:
- Background: `theme.colors.chatBubbleUserBg`
- Text: `primaryText`
- Radii: `theme.radii.pill`

**Assistant bubble**:
- Background: `theme.colors.chatBubbleAssistantBg`
- With an optional outline glow if `layout.showHeaderGlow` is true

### 5.4. Agent Cards

For each card type:

- Background: `theme.colors.cardBg`
- Left border or top strip:
  - Suspicious → `cardAccentSuspicious`
  - Bills → `cardAccentBills`
  - Follow-ups → `cardAccentFollowups`
- Shadow: `shadows.shell` or `shadows.primaryButton` depending on theme

This is where Prompt 1 and 2 differ most:

- **Banana Pro** → warm accent strip + soft glow around Suspicious box
- **Deep Space** → more neon / cockpit accent; maybe more cyan with red for Suspicious

---

## 6. Settings → Appearance UI

Add a small panel:

**Settings → Appearance → Mailbox theme**

### Plan

Show 3 theme cards:

- **Thumbnail** (small image or gradient mimic of each theme)
- **Name + microcopy**:
  - **Classic** – "Neutral dark theme"
  - **Banana Pro** – "Warm banana SaaS"
  - **Deep Space** – "Job-search cockpit in deep space"

**Selecting one**:
- Updates the theme id via context/store
- Writes to localStorage + (later) user profile

This is also where you can show a little "Preview" of the Mailbox Assistant card using static content.

---

## 7. Progressive rollout plan

You don't have to do everything at once. Suggested phases:

### Phase 1 – Tokenize & Classic

1. Introduce `MailboxTheme` + registry
2. Implement `classic` tokens from your current design
3. Wire `MailChat` to use the tokens, but expose only **Classic** in Settings

### Phase 2 – Banana Pro & Deep Space

1. Map Gemini Prompt 1 → `bananaPro` tokens
2. Map Gemini Prompt 2 → `deepSpace` tokens
3. Add theme selector in Settings; behind a simple feature flag if you want

### Phase 3 – Polish + Globalization

1. Extend the theme to other job-related views if you like (Inbox highlights, Tracker banners)
2. Add Playwright tests:
   - One run per theme verifying the chat shell renders and basic cards are visible
3. Add a "Reset to default" button

---

## Implementation checklist

- [ ] Create `apps/web/src/themes/mailbox/types.ts` with `MailboxTheme` interface
- [ ] Create `apps/web/src/themes/mailbox/classic.ts` with current design tokens
- [ ] Create `apps/web/src/themes/mailbox/bananaPro.ts` (from Gemini Prompt 1)
- [ ] Create `apps/web/src/themes/mailbox/deepSpace.ts` (from Gemini Prompt 2)
- [ ] Create theme registry `MAILBOX_THEMES`
- [ ] Create `useMailboxTheme()` hook with localStorage persistence
- [ ] Refactor `MailChat.tsx` to use theme tokens
- [ ] Refactor tool pills to use theme tokens
- [ ] Refactor chat bubbles to use theme tokens
- [ ] Refactor `AgentCardList.tsx` to use theme tokens
- [ ] Add Settings → Appearance → Mailbox theme UI
- [ ] Add theme preview thumbnails
- [ ] Add backend persistence (optional, later)
- [ ] Add Playwright tests per theme
- [ ] Add "Reset to default" button

---

## Notes

- Keep themes **scoped to Mailbox Assistant** initially
- Theme tokens should be **design-agnostic** (e.g., `toolActiveBg` not `bananaYellow`)
- Layout variants can share themes but adjust structural elements
- Feature flag the theme selector if you want staged rollout
- Consider adding theme export/import for power users later
