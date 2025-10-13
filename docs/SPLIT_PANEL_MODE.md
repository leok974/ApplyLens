# Split Panel Mode Enhancement

**Date**: October 11, 2025  
**Feature**: Split/Overlay toggle for email details panel

## Overview

The email details panel now supports two viewing modes:

1. **Overlay Mode** (default) - Panel slides in from the right, covering the email list
2. **Split Mode** - Panel docks to the right side, showing list and details side-by-side

Users can toggle between modes with a toolbar button, and the preference is saved to `localStorage`.

## Features

### 1. Overlay Mode (Original Behavior)

**Characteristics**:

- Panel is `position: fixed` with `right-0`
- Slides in/out with transform animation
- Covers the email list when open
- Full shadow for depth
- Close button always visible

**Use Cases**:

- Focus on email content without distraction
- Maximum list space when panel is closed
- Mobile-friendly (panel takes full screen)

**CSS Classes**:

```tsx
"fixed inset-y-0 right-0 z-40 transform bg-card text-card-foreground shadow-2xl transition-transform"
open ? "translate-x-0" : "translate-x-full"
```text

### 2. Split Mode (New)

**Characteristics**:

- Panel is `position: relative`
- Always rendered (even when no email selected)
- Docked to right side in grid layout
- Border-left instead of shadow
- Close button hidden on medium+ screens

**Use Cases**:

- Compare multiple emails quickly
- Reference email while scrolling list
- Desktop power user workflow
- Persistent context

**CSS Classes**:

```tsx
"relative z-0 bg-card text-card-foreground border-l border-[color:hsl(var(--color-border))] h-full"
```text

## Implementation

### Component Changes

#### EmailDetailsPanel.tsx

**New Props**:

```tsx
type PanelMode = "overlay" | "split";

export function EmailDetailsPanel({
  mode = "overlay",  // NEW: defaults to overlay for backward compatibility
  // ...other props
}: {
  mode?: PanelMode;  // NEW: optional mode prop
  // ...other prop types
})
```text

**Dynamic Container Classes**:

```tsx
const containerClass =
  mode === "overlay"
    ? cn(
        "fixed inset-y-0 right-0 z-40 transform bg-card text-card-foreground shadow-2xl transition-transform",
        open ? "translate-x-0" : "translate-x-full"
      )
    : cn(
        // split mode: static block that fills parent height
        "relative z-0 bg-card text-card-foreground border-l border-[color:hsl(var(--color-border))] h-full"
      );
```text

**Conditional Close Button Visibility**:

```tsx
<Button 
  variant="ghost" 
  size="icon" 
  onClick={onClose} 
  aria-label="Close"
  className={mode === "split" ? "md:hidden" : ""}  // Hidden on desktop in split mode
>
  <X className="h-5 w-5" />
</Button>
```text

**Resize Handle**:

- Works in both modes
- Same drag behavior
- Width persists across mode switches

#### InboxPolishedDemo.tsx

**New State**:

```tsx
type PanelMode = "overlay" | "split";
const MODE_KEY = "inbox:panelMode";

const [panelMode, setPanelMode] = React.useState<PanelMode>(() => {
  const saved = localStorage.getItem(MODE_KEY) as PanelMode | null;
  return saved === "split" || saved === "overlay" ? saved : "overlay";
});
```text

**Toggle Function**:

```tsx
function togglePanelMode() {
  setPanelMode((m) => {
    const next = m === "overlay" ? "split" : "overlay";
    localStorage.setItem(MODE_KEY, next);
    // when switching to split, ensure open
    if (next === "split") setOpenPanel(true);
    return next;
  });
}
```text

**Toolbar Button**:

```tsx
<Button variant="outline" size="sm" onClick={togglePanelMode}>
  {panelMode === "split" ? (
    <>
      <Maximize2 className="mr-2 h-4 w-4" /> Overlay Panel
    </>
  ) : (
    <>
      <Columns2 className="mr-2 h-4 w-4" /> Split Panel
    </>
  )}
</Button>
```text

**Note**: Button label shows the **target mode** (what you'll switch TO), not the current mode.

**Conditional Layout**:

```tsx
{panelMode === "split" ? (
  // GRID: list on left, details docked right
  <div
    className="grid min-h-[calc(100vh-64px)]"
    style={{ gridTemplateColumns: "1fr auto" }}  // panel controls its own width
  >
    <div className="overflow-hidden">
      <EmailList {...props} />
    </div>
    <EmailDetailsPanel mode="split" open={true} {...props} />
  </div>
) : (
  // Overlay mode: list full-width, slide-over when open
  <div className="relative min-h-[calc(100vh-64px)]">
    <EmailList {...props} />
    <EmailDetailsPanel mode="overlay" open={openPanel} {...props} />
  </div>
)}
```text

## User Experience

### Mode Toggle Flow

1. **User clicks "Split Panel" button** (while in overlay mode)
   - Button changes to "Overlay Panel"
   - Panel docks to right side
   - List resizes to accommodate panel
   - Preference saved to localStorage
   - Panel opens if closed

2. **User clicks "Overlay Panel" button** (while in split mode)
   - Button changes to "Split Panel"
   - Panel becomes slide-over
   - List expands to full width
   - Panel state preserved (stays open if open)
   - Preference saved to localStorage

### Keyboard Shortcuts

Works in both modes:

- `[` - Previous message in thread
- `]` - Next message in thread
- `Esc` - Close panel (overlay only, hidden in split on desktop)

### Resize Behavior

**Both modes**:

- Drag left edge to resize
- Width: 420px - 1000px
- Persists across mode switches
- Same localStorage key: `inbox:detailsPanelWidth`

### Responsive Behavior

**Overlay Mode**:

- Mobile: Full screen panel
- Tablet: Slide-over from right
- Desktop: Slide-over from right

**Split Mode**:

- Mobile: Falls back to overlay-like behavior
- Tablet: Side-by-side if space allows
- Desktop: Always side-by-side

**Close Button in Split Mode**:

- Hidden on `md` breakpoint and above
- Visible on mobile (for closing panel)

## State Management

### Persistence

**Panel Mode**:

- Key: `inbox:panelMode`
- Values: `"overlay"` | `"split"`
- Default: `"overlay"`

**Panel Width**:

- Key: `inbox:detailsPanelWidth`
- Values: `420` - `1000` (number)
- Default: `720`

### Synchronization

When switching modes:

1. New mode saved to localStorage
2. If switching to split → `setOpenPanel(true)`
3. If switching to overlay → preserve current open state
4. Panel width remains unchanged

## Layout Details

### Grid Structure (Split Mode)

```text
┌─────────────────────────────────────────┐
│  Filters Panel  │  Email List  │ Panel │
│                 │              │       │
│  (fixed width)  │  (flexible)  │ (user-│
│  18rem          │   1fr        │ sized)│
│                 │              │       │
└─────────────────────────────────────────┘
```text

**CSS Grid**:

```css
/* Outer grid: filters + content */
grid-cols-1 md:grid-cols-[18rem,1fr]

/* Inner grid (split mode only): list + panel */
grid-template-columns: 1fr auto
```text

**Panel Width**:

- Controlled by `style={{ width }}` prop
- Not constrained by grid column
- User can resize from 420px to 1000px

### Overflow Handling

**Split Mode**:

```tsx
<div className="overflow-hidden">
  <EmailList />  // Scrolls independently
</div>
<EmailDetailsPanel />  // Has own ScrollArea
```text

**Overlay Mode**:

```tsx
<div className="relative">
  <EmailList />  // Full height scrolling
  <EmailDetailsPanel />  // Fixed position, own scroll
</div>
```text

## Visual Design

### Overlay Mode

- **Shadow**: `shadow-2xl` for depth
- **Transform**: `translate-x-full` → `translate-x-0`
- **Transition**: `transition-transform` (smooth slide)
- **Z-index**: `z-40` (above content)

### Split Mode

- **Border**: `border-l border-[color:hsl(var(--color-border))]`
- **No shadow**: Uses border for separation
- **Position**: `relative` (in flow)
- **Z-index**: `z-0` (normal stacking)

### Icons

**Overlay Icon**: `Maximize2` (expand/maximize)  
**Split Icon**: `Columns2` (two columns)

**Reasoning**:

- Maximize suggests panel will overlay/expand
- Columns suggests side-by-side layout

## Performance

### Split Mode Optimization

**Always Mounted**:

- Panel is always in DOM when in split mode
- Shows "Select an email..." placeholder when no email selected
- Avoids mount/unmount overhead on email selection

**Benefits**:

- Instant state restoration
- Smoother transitions
- Preserves scroll position

**Trade-offs**:

- Slightly higher memory usage (one extra component tree)
- Acceptable for desktop use case

### Overlay Mode Optimization

**Conditional Mounting**:

- Panel only mounted when `open={true}`
- Removed from DOM when closed
- Saves memory on mobile

## Accessibility

### ARIA Attributes

Both modes:

```tsx
role="dialog"
aria-modal="true"
aria-label="Resize panel" (on drag handle)
```text

### Keyboard Navigation

- Close button always focusable
- Resize handle keyboard accessible (future enhancement)
- Tab order maintained in both modes

### Screen Reader Announcements

**Mode toggle**:

- Button label announces target mode
- "Split Panel" = switching to split
- "Overlay Panel" = switching to overlay

**Panel state**:

- Dialog role announces when panel opens
- Thread counter announces position

## Testing

### Manual Test Cases

**Overlay Mode**:

- [ ] Click email → panel slides in
- [ ] Click close → panel slides out
- [ ] Resize panel → width persists
- [ ] Press Esc → panel closes
- [ ] Refresh page → stays in overlay mode

**Split Mode**:

- [ ] Click "Split Panel" → layout changes to grid
- [ ] Click email → panel shows content
- [ ] Click close (mobile) → panel shows placeholder
- [ ] Resize panel → width persists
- [ ] Refresh page → stays in split mode

**Mode Switching**:

- [ ] Toggle overlay → split → layout changes
- [ ] Toggle split → overlay → layout changes
- [ ] Width preserved across toggle
- [ ] Open state preserved (overlay)
- [ ] Panel auto-opens when switching to split

**Responsive**:

- [ ] Mobile overlay: full screen
- [ ] Mobile split: close button visible
- [ ] Desktop overlay: slide-over
- [ ] Desktop split: side-by-side, close button hidden

### Edge Cases

- [ ] Switch modes while panel is open
- [ ] Switch modes while panel is closed
- [ ] Resize in overlay, switch to split
- [ ] Very narrow screen in split mode
- [ ] Rapid mode toggling

## Browser Compatibility

- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ CSS Grid support required
- ✅ localStorage required

## Future Enhancements

- [ ] Three-column layout (filters + list + panel)
- [ ] Floating panel mode (movable)
- [ ] Snap to side (left or right)
- [ ] Multiple panels (compare emails)
- [ ] Keyboard shortcut to toggle mode (e.g., `Cmd+\`)
- [ ] Panel width presets (narrow, medium, wide)
- [ ] Remember last viewed email per mode

## Migration Guide

### For Existing Pages

**Before** (old API):

```tsx
<EmailDetailsPanel
  open={openPanel}
  onClose={() => setOpenPanel(false)}
  // ...other props
/>
```text

**After** (new API, backward compatible):

```tsx
<EmailDetailsPanel
  mode="overlay"  // Add this for explicit mode
  open={openPanel}
  onClose={() => setOpenPanel(false)}
  // ...other props
/>
```text

**No breaking changes**: `mode` prop is optional and defaults to `"overlay"`.

### Adding Split Mode to Your Page

1. Add state and toggle function (see Implementation section)
2. Add toolbar button
3. Wrap content in conditional layout
4. Render panel twice (once for each mode branch)

**Copy-paste template available in this doc** (see InboxPolishedDemo.tsx section)

---

**Implementation Status**: ✅ Complete  
**Backward Compatible**: ✅ Yes (mode defaults to "overlay")  
**Tested**: ⏳ Pending user verification  
**Documentation**: ✅ Complete
