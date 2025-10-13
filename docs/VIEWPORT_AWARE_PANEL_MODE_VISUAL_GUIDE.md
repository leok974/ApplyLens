# Viewport-Aware Panel Mode - Visual Guide

**Quick reference for how the panel behaves at different viewport sizes**

## Breakpoint Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    Viewport Width                            │
└─────────────────────────────────────────────────────────────┘
    0px              768px              1024px            1536px
    │                 │                   │                  │
    └─────────────────┴───────────────────┴──────────────────┘
      Mobile (sm)     Tablet (md)     Desktop (lg)     Wide (xl)
    ══════════════════════════════════╪═══════════════════════
      OVERLAY MODE                    │   SPLIT/OVERLAY
      (forced)                        │   (user choice)
                                      │
                                  DESKTOP_BP
                                   (1024px)
```text

## Layout at Different Sizes

### Small Mobile (<768px)

```text
╔════════════════════════════════╗
║  📱 Mobile Phone               ║
║  Viewport: 375px - 767px       ║
╠════════════════════════════════╣
║                                ║
║  ┌──────────────────────────┐ ║
║  │  Email List              │ ║
║  │  (full width)            │ ║
║  │                          │ ║
║  │  ✉ Email 1               │ ║
║  │  ✉ Email 2               │ ║
║  │  ✉ Email 3               │ ║
║  │                          │ ║
║  └──────────────────────────┘ ║
║                                ║
║  Toggle Button: HIDDEN         ║
║  Panel Mode: Overlay (forced)  ║
║                                ║
╚════════════════════════════════╝

When email clicked:
╔════════════════════════════════╗
║  📱 Mobile Phone               ║
╠════════════════════════════════╣
║                                ║
║  ╔══════════════════════════╗ ║
║  ║ [X] Email Details        ║ ║
║  ║ ─────────────────────────║ ║
║  ║ From: sender@email.com   ║ ║
║  ║ Subject: Hello World     ║ ║
║  ║ ─────────────────────────║ ║
║  ║ Email body content...    ║ ║
║  ║                          ║ ║
║  ║                          ║ ║
║  ╚══════════════════════════╝ ║
║   (Covers entire screen)       ║
╚════════════════════════════════╝
```text

### Tablet Portrait (768px - 1023px)

```text
╔═══════════════════════════════════════╗
║  📱 Tablet Portrait                   ║
║  Viewport: 768px - 1023px             ║
╠═══════════════════════════════════════╣
║  Filters  │  Email List               ║
║  ────────┼─────────────────────       ║
║          │                            ║
║  □ Promo │  ✉ Email 1                ║
║  □ Bills │  ✉ Email 2                ║
║  □ Safe  │  ✉ Email 3                ║
║          │  ✉ Email 4                ║
║          │  ✉ Email 5                ║
║          │                            ║
║          │  [Split Panel] ← DISABLED  ║
║          │     (dimmed)               ║
╚═══════════════════════════════════════╝

Panel Mode: Overlay (forced)
Toggle: Visible but disabled
Variant: Secondary (dimmed)
Tooltip: "Available on larger screens"
```text

### Desktop (≥1024px) - Overlay Mode

```text
╔═══════════════════════════════════════════════════════════════════╗
║  💻 Desktop - OVERLAY MODE                                         ║
║  Viewport: ≥1024px                                                 ║
╠═══════════════════════════════════════════════════════════════════╣
║  Filters       │  Email List                    [Split Panel] ✓   ║
║  ─────────────┼────────────────────────────────────────────────   ║
║                │                                                    ║
║  □ Promo       │  ✉ Email 1 - Application update                  ║
║  □ Bills       │  ✉ Email 2 - Interview invitation                ║
║  □ Safe        │  ✉ Email 3 - Weekly newsletter                   ║
║                │  ✉ Email 4 - Password reset                      ║
║                │  ✉ Email 5 - Meeting reminder                    ║
║  [Apply]       │                                                   ║
║                │                                                    ║
║                │  (List takes full width)                          ║
║                │                                                    ║
╚═══════════════════════════════════════════════════════════════════╝

Panel Mode: Overlay
Toggle: Enabled, "Split Panel" label
Variant: Outline (normal)
Panel: Hidden until email clicked
```text

### Desktop (≥1024px) - Split Mode

```text
╔═══════════════════════════════════════════════════════════════════════════════╗
║  💻 Desktop - SPLIT MODE                                                       ║
║  Viewport: ≥1024px                                                             ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  Filters       │  Email List                │  Email Details [Overlay Panel] ✓║
║  ─────────────┼────────────────────────────┼────────────────────────────────  ║
║                │                            │                                  ║
║  □ Promo       │  ✉ Email 1 ← selected     │  From: sender@example.com       ║
║  □ Bills       │  ✉ Email 2                │  Date: Oct 11, 2025             ║
║  □ Safe        │  ✉ Email 3                │  ──────────────────────────     ║
║                │  ✉ Email 4                │                                  ║
║  [Apply]       │  ✉ Email 5                │  Subject: Your application      ║
║                │                            │                                  ║
║                │                            │  Dear applicant,                 ║
║                │  (List resizes to fit)     │  Thank you for applying...      ║
║                │                            │                                  ║
║                │                            │  [← 1/3 →]  Thread navigation   ║
╚═══════════════════════════════════════════════════════════════════────════════╝

Panel Mode: Split
Toggle: Enabled, "Overlay Panel" label
Variant: Outline (normal)
Panel: Always visible, docked to right
Close Button: Hidden on desktop
```text

## Toggle Button States

### Desktop - Enabled

```text
┌──────────────────────────┐
│ ⚏  Split Panel          │  ← Normal outline style
└──────────────────────────┘
   Clickable, pointer cursor
   Shows label of TARGET mode
```text

### Mobile - Disabled

```text
┌──────────────────────────┐
│ ⚏  Split Panel          │  ← Dimmed secondary style
└──────────────────────────┘
   Not clickable, not-allowed cursor
   Tooltip: "Available on larger screens"
   Hidden on screens < md (768px)
```text

## Responsive Transitions

### Scenario 1: Desktop → Mobile (Window Shrink)

```text
BEFORE (Desktop, ≥1024px, Split Mode):
┌───────────────────────────────────────────┐
│  List          │  Panel (docked)          │
│  ✉ Email 1     │  ╔═══════════════════╗  │
│  ✉ Email 2     │  ║ Email Details     ║  │
│  ✉ Email 3     │  ║ ...               ║  │
└───────────────────────────────────────────┘
         │
         │ User resizes window below 1024px
         ▼
AFTER (Mobile, <1024px, Forced Overlay):
┌───────────────────────────────────────────┐
│  List (full width)                        │
│  ✉ Email 1                                │
│  ✉ Email 2                                │
│  ✉ Email 3                                │
│                                            │
│  [Split Panel] ← Disabled                 │
└───────────────────────────────────────────┘

Changes:
- Layout switches from grid to single column
- Panel closes (or becomes overlay if was open)
- Toggle button becomes disabled + dimmed
- Saved preference: PRESERVED in localStorage
```text

### Scenario 2: Mobile → Desktop (Window Expand)

```text
BEFORE (Mobile, <1024px):
┌───────────────────────────────────────────┐
│  List (full width)                        │
│  ✉ Email 1                                │
│  ✉ Email 2                                │
│  ✉ Email 3                                │
│                                            │
│  [Split Panel] ← Disabled                 │
└───────────────────────────────────────────┘
localStorage: "panelMode" = "split"
         │
         │ User resizes window above 1024px
         ▼
AFTER (Desktop, ≥1024px, Reads "split" from localStorage):
┌───────────────────────────────────────────┐
│  List          │  Panel (auto-opens!) ← AUTO│
│  ✉ Email 1     │  ╔═══════════════════╗  │
│  ✉ Email 2     │  ║ Email Details     ║  │
│  ✉ Email 3     │  ║ ...               ║  │
└───────────────────────────────────────────┘
              [Overlay Panel] ← Enabled

Changes:
- Layout switches to grid (split mode)
- Panel auto-opens (useEffect triggers)
- Toggle button becomes enabled
- Reads saved preference from localStorage
```text

### Scenario 3: Tablet Rotation

```text
PORTRAIT (<1024px):
┌─────────────────────┐
│                     │
│  List               │
│  ✉ Email 1          │
│  ✉ Email 2          │
│  ✉ Email 3          │
│                     │
│  [Split] disabled   │
│                     │
└─────────────────────┘
      Overlay mode
        │
        │ User rotates device
        ▼
LANDSCAPE (≥1024px):
┌────────────────────────────────────┐
│  List       │  Panel (auto-opens)  │
│  ✉ Email 1  │  ╔════════════════╗ │
│  ✉ Email 2  │  ║ Details...     ║ │
└────────────────────────────────────┘
         Split mode (if saved)
         [Overlay Panel] enabled
```text

## State Flow Diagram

```text
                    ┌──────────────┐
                    │  Page Load   │
                    └──────┬───────┘
                           │
                    Read localStorage
                           │
                ┌──────────┴──────────┐
                │                     │
           ┌────▼────┐          ┌────▼────┐
           │ Desktop │          │ Mobile  │
           │ ≥1024px │          │ <1024px │
           └────┬────┘          └────┬────┘
                │                    │
         ┌──────▼──────┐      ┌─────▼──────┐
         │ effectiveMode│      │effectiveMode│
         │ = panelMode  │      │ = "overlay" │
         │ (user choice)│      │  (forced)   │
         └──────┬───────┘      └─────┬───────┘
                │                    │
        ┌───────┴────────┐          │
        │                │          │
   ┌────▼────┐      ┌────▼────┐   │
   │ "split" │      │"overlay"│   │
   └────┬────┘      └────┬────┘   │
        │                │         │
  ┌─────▼──────┐   ┌─────▼──────┐ │
  │ Grid Layout│   │  Relative  │ │
  │ Panel open │   │   Layout   │ │
  └────────────┘   │Panel slide │ │
                   └─────────────┘ │
                                   │
                             ┌─────▼──────┐
                             │  Relative  │
                             │   Layout   │
                             │Panel slide │
                             └────────────┘

Toggle Button States:
Desktop: Enabled, outline variant
Mobile:  Disabled, secondary variant (dimmed)
```text

## Media Query Behavior

### matchMedia Listener

```javascript
// Set up listener
const mq = window.matchMedia("(min-width: 1024px)");

// Fires when crossing breakpoint:
1023px → 1024px  ✅ Fires (mobile → desktop)
1024px → 1023px  ✅ Fires (desktop → mobile)

// Does NOT fire for:
1024px → 1280px  ❌ (still desktop)
800px → 600px    ❌ (still mobile)
```text

### Resize Event (Fallback)

```javascript
window.addEventListener("resize", () => {
  setIsDesktop(window.innerWidth >= 1024);
});

// Fires on EVERY resize
// Less efficient but works in older browsers
// Both listeners active for maximum compatibility
```text

## User Preference Persistence

### localStorage Structure

```text
Key: "inbox:panelMode"
Values: "overlay" | "split"

Example states:
┌──────────────────────────────────────────┐
│ localStorage                             │
├──────────────────────────────────────────┤
│ "inbox:panelMode": "split"               │
│ "inbox:detailsPanelWidth": "720"         │
└──────────────────────────────────────────┘
```text

### How Preference is Applied

```text
1. Page Load
   ↓
2. Read localStorage → panelMode = "split"
   ↓
3. Check viewport → isDesktop = true
   ↓
4. Calculate effectiveMode = isDesktop ? "split" : "overlay"
   ↓
5. Render split layout
```text

### Mobile Override

```text
1. Page Load
   ↓
2. Read localStorage → panelMode = "split"
   ↓
3. Check viewport → isDesktop = false
   ↓
4. Calculate effectiveMode = isDesktop ? "split" : "overlay"
                                       ↓
                              effectiveMode = "overlay"
   ↓
5. Render overlay layout (preference ignored!)
```text

## Quick Reference Table

| Viewport | isDesktop | panelMode (saved) | effectiveMode | Toggle | Layout |
|----------|-----------|-------------------|---------------|--------|--------|
| <768px   | false     | "overlay"         | "overlay"     | Hidden | Overlay |
| <768px   | false     | "split"           | "overlay"     | Hidden | Overlay |
| 768-1023px | false   | "overlay"         | "overlay"     | Disabled | Overlay |
| 768-1023px | false   | "split"           | "overlay"     | Disabled | Overlay |
| ≥1024px  | true      | "overlay"         | "overlay"     | Enabled | Overlay |
| ≥1024px  | true      | "split"           | "split"       | Enabled | Split |

**Key Insight**: effectiveMode only equals "split" when BOTH conditions are true:

1. Viewport ≥1024px (isDesktop = true)
2. User has saved "split" preference (panelMode = "split")

---

**Visual Guide Version**: 1.0  
**Last Updated**: October 11, 2025  
**Breakpoint**: 1024px (lg)  
**Status**: ✅ Production Ready
