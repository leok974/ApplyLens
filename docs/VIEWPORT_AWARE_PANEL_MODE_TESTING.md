# Viewport-Aware Panel Mode - Testing Checklist

**Feature**: Responsive split panel that adapts to screen size  
**Status**: Ready for testing  
**URL**: <http://localhost:5175/inbox-polished-demo>

---

## Pre-Testing Setup

- [ ] Docker container running (`infra-web-1` up)
- [ ] Web app accessible at <http://localhost:5175>
- [ ] Browser dev tools ready (for viewport testing)
- [ ] localStorage cleared (or note existing values)

---

## 1. Desktop Testing (≥1024px)

### Initial Load - Overlay Mode (Default)

- [ ] Open <http://localhost:5175/inbox-polished-demo>
- [ ] Viewport set to ≥1024px (e.g., 1280px)
- [ ] Page loads without errors
- [ ] Email list visible on left
- [ ] No panel visible initially
- [ ] Toggle button visible in toolbar
- [ ] Toggle button shows: "Split Panel" label
- [ ] Toggle button variant: outline (normal style)
- [ ] Toggle button enabled (clickable)

### Switch to Split Mode

- [ ] Click "Split Panel" button
- [ ] Layout switches to grid immediately
- [ ] Panel appears docked on right
- [ ] Panel shows "Select an email..." placeholder
- [ ] Email list resizes to accommodate panel
- [ ] Toggle button label changes to: "Overlay Panel"
- [ ] No console errors

### Select Email in Split Mode

- [ ] Click an email from list
- [ ] Email details appear in right panel
- [ ] Panel shows email subject, sender, date
- [ ] Thread navigation visible ([, ])
- [ ] Close button NOT visible on right panel header (desktop)
- [ ] Email list still visible and scrollable

### Resize Panel in Split Mode

- [ ] Hover over left edge of panel
- [ ] Cursor changes to resize cursor
- [ ] Drag left to make panel narrower
- [ ] Drag right to make panel wider
- [ ] Panel width stays between 420px - 1000px
- [ ] Email list adjusts width accordingly
- [ ] Smooth resize without jank

### Switch Back to Overlay Mode

- [ ] Click "Overlay Panel" button
- [ ] Layout switches to full-width list
- [ ] Panel slides over list (if email selected)
- [ ] Toggle button label changes to: "Split Panel"
- [ ] Panel width preserved from split mode

### Persistence Test

- [ ] Set mode to "split"
- [ ] Refresh page (F5)
- [ ] Split mode restored automatically
- [ ] Panel auto-opens
- [ ] Email list and panel visible
- [ ] localStorage contains: `"inbox:panelMode": "split"`

---

## 2. Mobile Testing (<1024px)

### Initial Load - Mobile Size

- [ ] Set viewport to <1024px (e.g., 375px mobile)
- [ ] Open <http://localhost:5175/inbox-polished-demo>
- [ ] Email list takes full width
- [ ] No panel visible initially
- [ ] Toggle button HIDDEN on small screens (<768px)
- [ ] Layout looks clean (no horizontal scroll)

### Toggle Button on Tablet (768px - 1023px)

- [ ] Set viewport to 800px (tablet portrait)
- [ ] Toggle button visible in toolbar
- [ ] Toggle button shows: "Split Panel" label
- [ ] Toggle button variant: secondary (dimmed)
- [ ] Toggle button DISABLED (cannot click)
- [ ] Hover shows tooltip: "Available on larger screens"
- [ ] Button has reduced opacity/contrast

### Select Email on Mobile

- [ ] Click an email from list
- [ ] Panel slides in from right
- [ ] Panel covers entire screen
- [ ] Close button [X] visible in panel header
- [ ] Email details readable
- [ ] Can scroll email content
- [ ] Click [X] to close → panel slides out

### Saved Split Preference on Mobile

- [ ] Set viewport to desktop (≥1024px)
- [ ] Switch to split mode
- [ ] Verify localStorage: `"inbox:panelMode": "split"`
- [ ] Set viewport to mobile (<1024px)
- [ ] Page still shows overlay mode (forced)
- [ ] Split preference ignored on mobile
- [ ] No layout breaking

---

## 3. Responsive Transition Testing

### Desktop → Mobile (Window Shrink)

- [ ] Start at desktop size (≥1024px)
- [ ] Set mode to split
- [ ] Email details visible in right panel
- [ ] Slowly resize browser window narrower
- [ ] At 1024px breakpoint:
  - [ ] Layout switches to overlay mode
  - [ ] Panel closes or becomes slide-over
  - [ ] Toggle button becomes disabled
  - [ ] Toggle button variant changes to secondary
  - [ ] Email list expands to full width
- [ ] Continue to <768px:
  - [ ] Toggle button hidden
- [ ] No console errors
- [ ] Smooth visual transition

### Mobile → Desktop (Window Expand)

- [ ] Start at mobile size (<1024px)
- [ ] Verify localStorage has: `"inbox:panelMode": "split"`
- [ ] Toggle button disabled/hidden
- [ ] Slowly resize browser window wider
- [ ] At 1024px breakpoint:
  - [ ] Layout switches to split mode
  - [ ] Panel auto-opens
  - [ ] Toggle button becomes enabled
  - [ ] Toggle button variant changes to outline
  - [ ] Email list resizes to accommodate panel
- [ ] No console errors
- [ ] Smooth visual transition

### Mobile → Desktop with Overlay Saved

- [ ] Start at desktop (≥1024px)
- [ ] Ensure mode is overlay
- [ ] Verify localStorage: `"inbox:panelMode": "overlay"`
- [ ] Resize to mobile (<1024px)
- [ ] Resize back to desktop (≥1024px)
- [ ] Mode stays overlay
- [ ] Panel does NOT auto-open
- [ ] Toggle shows "Split Panel"

### Rapid Resizing

- [ ] Quickly resize window back and forth across 1024px
- [ ] Layout switches appropriately each time
- [ ] No flickering or jank
- [ ] No console errors
- [ ] No memory leaks (check dev tools)

---

## 4. Tablet Orientation Testing

### Portrait Mode (<1024px)

- [ ] Test on actual tablet (iPad, Android tablet)
- [ ] Hold device in portrait
- [ ] Toggle button disabled
- [ ] Overlay mode active
- [ ] Email list full width

### Landscape Mode (≥1024px)

- [ ] Rotate device to landscape
- [ ] Toggle button becomes enabled
- [ ] Can switch to split mode
- [ ] Split layout works on landscape tablet
- [ ] Panel resizable

### Back to Portrait

- [ ] Rotate device back to portrait
- [ ] Layout switches to overlay
- [ ] Toggle button disabled again
- [ ] If split was active → forced to overlay

---

## 5. Keyboard & Accessibility Testing

### Toggle Button Focus

- [ ] Tab to toggle button (desktop)
- [ ] Button receives focus outline
- [ ] Enter/Space key toggles mode
- [ ] Focus visible indicator

### Toggle Button Disabled State

- [ ] Resize to mobile (<1024px)
- [ ] Tab to toggle button
- [ ] Button still focusable
- [ ] Enter/Space does nothing (disabled)
- [ ] Screen reader announces "disabled"

### Keyboard Shortcuts (Both Modes)

**Overlay Mode**:

- [ ] Select email
- [ ] Press `[` → previous in thread
- [ ] Press `]` → next in thread
- [ ] Press `Esc` → panel closes

**Split Mode**:

- [ ] Select email
- [ ] Press `[` → previous in thread
- [ ] Press `]` → next in thread
- [ ] Press `Esc` → panel closes (or shows placeholder)

### Screen Reader Testing

- [ ] Toggle button label read correctly
- [ ] "Split Panel" vs "Overlay Panel" announced
- [ ] Disabled state announced on mobile
- [ ] Tooltip read on hover (mobile)
- [ ] Panel role="dialog" announced

---

## 6. Cross-Browser Testing

### Chrome/Edge (Chromium)

- [ ] Desktop: All features work
- [ ] Mobile: Forced overlay works
- [ ] Resize: Transitions smooth
- [ ] matchMedia: Fires at breakpoint
- [ ] No console errors

### Firefox

- [ ] Desktop: All features work
- [ ] Mobile: Forced overlay works
- [ ] Resize: Transitions smooth
- [ ] matchMedia: Fires at breakpoint
- [ ] No console errors

### Safari (macOS)

- [ ] Desktop: All features work
- [ ] Mobile: Forced overlay works
- [ ] Resize: Transitions smooth
- [ ] matchMedia: Fires at breakpoint
- [ ] No console errors

### Mobile Safari (iOS)

- [ ] Portrait: Overlay mode forced
- [ ] Landscape: Toggle enabled (if ≥1024px)
- [ ] Rotation: Smooth transition
- [ ] Touch: Panel slides correctly
- [ ] No layout breaking

### Chrome Mobile (Android)

- [ ] Portrait: Overlay mode forced
- [ ] Landscape: Toggle enabled (if ≥1024px)
- [ ] Rotation: Smooth transition
- [ ] Touch: Panel slides correctly
- [ ] No layout breaking

---

## 7. Edge Cases & Error Handling

### Case 1: localStorage Cleared

- [ ] Open dev tools → Application → localStorage
- [ ] Delete `inbox:panelMode` key
- [ ] Refresh page
- [ ] Defaults to overlay mode
- [ ] No console errors

### Case 2: Invalid localStorage Value

- [ ] Set `inbox:panelMode` to "invalid"
- [ ] Refresh page
- [ ] Falls back to overlay mode
- [ ] No console errors

### Case 3: Panel Open During Resize

- [ ] Desktop: Open email in split mode
- [ ] Resize to mobile
- [ ] Panel state handled gracefully
- [ ] No errors

### Case 4: Multiple Rapid Toggles

- [ ] Desktop: Click toggle 10 times rapidly
- [ ] Mode switches each time
- [ ] localStorage updates correctly
- [ ] No console errors
- [ ] No race conditions

### Case 5: Browser Zoom

- [ ] Desktop: Set zoom to 200%
- [ ] Effective viewport width halved
- [ ] Breakpoint respects zoom (1024 CSS pixels)
- [ ] Mode switches if viewport falls below 1024px
- [ ] Set zoom to 50%
- [ ] Mode switches if viewport exceeds 1024px

### Case 6: Window Undefined (SSR)

- [ ] Not applicable (client-only app)
- [ ] But code has `typeof window !== "undefined"` check
- [ ] No errors if accidentally rendered server-side

---

## 8. Performance Testing

### Resize Performance

- [ ] Open browser performance monitor
- [ ] Resize window slowly across breakpoint
- [ ] Monitor CPU usage
- [ ] Monitor memory usage
- [ ] No excessive re-renders
- [ ] No memory leaks

### matchMedia Listener

- [ ] Open dev tools → Console
- [ ] Add log in matchMedia listener
- [ ] Resize window
- [ ] Listener fires ONLY at 1024px crossing
- [ ] Does NOT fire for every pixel change

### Component Re-renders

- [ ] Install React DevTools Profiler
- [ ] Toggle between modes
- [ ] Only affected components re-render
- [ ] No full page re-render

---

## 9. Visual Regression Testing

### Desktop - Overlay Mode

- [ ] Screenshot at 1280px viewport
- [ ] Email list full width
- [ ] Toggle button: outline variant
- [ ] Label: "Split Panel"

### Desktop - Split Mode

- [ ] Screenshot at 1280px viewport
- [ ] Grid layout: list + panel
- [ ] Toggle button: outline variant
- [ ] Label: "Overlay Panel"

### Mobile - Forced Overlay

- [ ] Screenshot at 375px viewport
- [ ] Email list full width
- [ ] Toggle button hidden (<768px)

### Tablet - Button Disabled

- [ ] Screenshot at 800px viewport
- [ ] Toggle button: secondary variant (dimmed)
- [ ] Tooltip visible on hover

---

## 10. Documentation Verification

- [ ] README.md mentions viewport-aware behavior
- [ ] SPLIT_PANEL_MODE.md updated with responsive section
- [ ] VIEWPORT_AWARE_PANEL_MODE.md exists and accurate
- [ ] VIEWPORT_AWARE_PANEL_MODE_VISUAL_GUIDE.md exists
- [ ] Code comments explain effectiveMode calculation
- [ ] localStorage keys documented

---

## Bug Report Template

If you find an issue, report with:

**Bug Title**: [Concise description]

**Environment**:

- Browser: [Chrome/Firefox/Safari/etc.]
- OS: [Windows/macOS/iOS/Android]
- Viewport: [Width x Height]
- Device: [Desktop/Mobile/Tablet]

**Steps to Reproduce**:

1. [First step]
2. [Second step]
3. [Third step]

**Expected Behavior**: [What should happen]

**Actual Behavior**: [What actually happens]

**Screenshots**: [If applicable]

**Console Errors**: [If any]

**localStorage State**: [Value of `inbox:panelMode`]

---

## Success Criteria

### Must Pass (Blocking)

- ✅ Desktop users can toggle between split/overlay
- ✅ Mobile users always get overlay (no broken layouts)
- ✅ Toggle button disabled on mobile
- ✅ Mode preference persists across refresh
- ✅ Resize transitions work smoothly
- ✅ No console errors in any scenario
- ✅ No breaking changes to existing features

### Should Pass (Important)

- ✅ Toggle button tooltip shows on mobile
- ✅ Button variant changes (outline ↔ secondary)
- ✅ matchMedia listener fires efficiently
- ✅ Keyboard shortcuts work in both modes
- ✅ Screen reader announces states correctly
- ✅ All browsers tested

### Nice to Have (Enhancement)

- ✅ Smooth CSS transitions on resize
- ✅ Visual feedback during transition
- ✅ Performance metrics logged

---

## Testing Status

| Area | Status | Tester | Date | Notes |
|------|--------|--------|------|-------|
| Desktop Overlay | ⏳ Pending | - | - | - |
| Desktop Split | ⏳ Pending | - | - | - |
| Mobile Forced Overlay | ⏳ Pending | - | - | - |
| Resize Desktop→Mobile | ⏳ Pending | - | - | - |
| Resize Mobile→Desktop | ⏳ Pending | - | - | - |
| Tablet Rotation | ⏳ Pending | - | - | - |
| Chrome/Edge | ⏳ Pending | - | - | - |
| Firefox | ⏳ Pending | - | - | - |
| Safari | ⏳ Pending | - | - | - |
| Mobile Safari | ⏳ Pending | - | - | - |
| Chrome Mobile | ⏳ Pending | - | - | - |
| Keyboard Nav | ⏳ Pending | - | - | - |
| Screen Reader | ⏳ Pending | - | - | - |
| Edge Cases | ⏳ Pending | - | - | - |
| Performance | ⏳ Pending | - | - | - |

---

**Checklist Version**: 1.0  
**Last Updated**: October 11, 2025  
**Feature**: Viewport-Aware Panel Mode  
**Status**: ✅ Ready for Testing

**Next Step**: Start with Section 1 (Desktop Testing) and work through sequentially.
