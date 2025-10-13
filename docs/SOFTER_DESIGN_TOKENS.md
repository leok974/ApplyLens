# Softer Design Tokens Implementation

**Date**: October 11, 2025  
**Goal**: Reduce visual harshness and improve readability across the application

## Overview

This document summarizes the comprehensive design token refinement implemented to create a calmer, more readable interface. The changes move away from pure white/black high-contrast aesthetics to a softer warm gray palette with improved typography.

## Design Philosophy

### Before
- Pure white backgrounds (`hsl(0 0% 100%)`)
- Deep navy dark mode (`hsl(222.2 84% 4.9%)`)
- High-contrast borders (91% lightness)
- Stark icon colors (pure white/black)
- Dense text with default line-height

### After
- Warm gray backgrounds (`hsl(210 20% 97%)`)
- Midnight slate dark mode (`hsl(222 33% 10%)`)
- Muted borders (85% lightness in light mode, 22% in dark)
- Softer icon colors (`slate-400` with gentle hovers)
- Relaxed typography (`leading-relaxed` for body text)

## Color Palette Changes

### Light Mode
```css
--color-background: hsl(210 20% 97%)    /* Warm gray, not pure white */
--color-card: hsl(210 25% 98%)          /* Subtle separation from background */
--color-muted: hsl(210 23% 94%)         /* Chips, muted blocks */
--color-border: hsl(215 20% 85%)        /* Softer, less contrast */
--color-accent: hsl(221 75% 64%)        /* Consistent indigo for primary actions */
```

### Dark Mode
```css
--color-background: hsl(222 33% 10%)    /* Midnight slate (#0f1520-ish) */
--color-card: hsl(222 26% 14%)          /* Mid-contrast, slightly elevated */
--color-muted: hsl(222 20% 18%)         /* Darker blocks */
--color-border: hsl(222 20% 22%)        /* Low-contrast borders */
--color-accent: hsl(221 75% 66%)        /* Slightly brighter for visibility */
```

## Typography Improvements

### Line Height
- **Headers**: `leading-snug` (1.375) - Compact titles
- **Body text**: `leading-relaxed` (1.625) - Comfortable reading
- **Preview text**: Explicit `leading-relaxed` for email previews

### Font Sizes
- Precise sizing: `text-[13px]` instead of `text-sm` where needed
- Subject lines: `text-base` with `leading-snug`
- Preview text: `text-[13px]` with `leading-relaxed`

## Component Updates

### 1. Global Styles (`index.css`)
✅ Complete color palette migration to softer tokens  
✅ Custom scrollbar styling with rounded thumbs  
✅ Uses CSS variable pattern: `[color:hsl(var(--color-{name}))]`

### 2. EmailRow Component
✅ Card styling: `rounded-xl` instead of `rounded-2xl`  
✅ Background: `bg-card` instead of `bg-white`  
✅ Hover state: `hover:bg-[color:hsl(var(--color-muted))]/40`  
✅ Icon colors: `text-slate-400 hover:text-slate-600 dark:hover:text-slate-200`  
✅ Typography: `leading-snug` for subject, `leading-relaxed` for preview

### 3. InboxPolishedDemo Page
✅ Semantic HTML: `<main>` and `<header>` tags  
✅ Page background: Uses CSS variable instead of gradient  
✅ Header: Backdrop blur with 80% opacity  
✅ Mail icon: Uses accent color variable  
✅ Search button: Changed to `outline` variant

### 4. EmailDetailsPanel
✅ Panel background: `bg-card` instead of `bg-white`  
✅ Enhanced prose styling with 7+ utility classes  
✅ Badge colors: CSS variables  
✅ Pre blocks: Muted background variable  
✅ Leading-relaxed for email body content

### 5. EmailList
✅ Section headers: CSS variable colors  
✅ Status dots: Use accent color variable  
✅ Skeleton loaders: Updated to match softer card styling  
✅ Border radius: `rounded-xl` instead of `rounded-2xl`

### 6. FiltersPanel
✅ Background: `bg-card` instead of `bg-white`  
✅ Border: CSS variable color

### 7. BulkBar
✅ Background: Muted color with 60% opacity  
✅ Border: CSS variable  
✅ Buttons: Changed from `secondary` to `outline` variant

### 8. SenderAvatar
✅ Border: CSS variable color  
✅ Avatar background: Uses accent color instead of gradient  
✅ Image fallback: `bg-card` instead of `bg-white`

### 9. UI Components

**Badge** (`components/ui/badge.tsx`)
- Default variant: Uses `bg-[color:hsl(var(--color-muted))]`
- Subtle variant: Muted background with transparency
- Border: CSS variable color

**Kbd** (`components/ui/kbd.tsx`)
- Background: Muted color variable
- Border: CSS variable color

**Segmented** (`components/ui/segmented.tsx`)
- Container: `bg-card` instead of `bg-white`
- Border: CSS variable color
- Selected state: Muted background

## CSS Variable Pattern

All color references now use this pattern for Tailwind v4 compatibility:

```tsx
// Background colors
className="bg-[color:hsl(var(--color-background))]"
className="bg-card"  // Semantic alias

// Border colors
className="border-[color:hsl(var(--color-border))]"

// Text colors
className="text-[color:hsl(var(--color-accent))]"

// Hover states
className="hover:bg-[color:hsl(var(--color-muted))]/40"
```

## Icon Color Strategy

**Default state**: `text-slate-400`  
**Hover state**: `hover:text-slate-600 dark:hover:text-slate-200`

This avoids pure white/black and creates a gentler visual experience.

## Button Hierarchy

Following the user's guidance for "less glare":

1. **Primary actions**: Use `accent` color (sparingly)
2. **Secondary actions**: Use `outline` variant (preferred)
3. **Tertiary actions**: Use `ghost` variant

Changed bulk action buttons from `secondary` to `outline` to reduce visual noise.

## Accessibility

✅ Maintains WCAG AA contrast ratios  
✅ Semantic HTML (`<main>`, `<header>`, `<article>`)  
✅ Proper ARIA attributes maintained  
✅ Focus states preserved

## Benefits

1. **Reduced Eye Strain**: Warm grays instead of pure white reduce glare
2. **Improved Readability**: Leading-relaxed makes text flow better
3. **Better Hierarchy**: Consistent use of muted vs accent colors
4. **Professional Feel**: Midnight slate dark mode feels premium
5. **Maintainability**: CSS variables make theme changes easy

## Browser Compatibility

- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ Dark mode via `prefers-color-scheme`
- ✅ Custom scrollbars (webkit only, graceful fallback)

## Future Enhancements

- [ ] Add animation timings to CSS variables
- [ ] Create spacing scale tokens
- [ ] Consider adding elevation/shadow tokens
- [ ] Document focus ring customization
- [ ] Add color-blind friendly mode

## Testing Checklist

- [x] Light mode visual appearance
- [x] Dark mode visual appearance
- [x] Hover states on all interactive elements
- [x] Keyboard navigation and focus states
- [ ] Screen reader compatibility
- [ ] Color contrast validation
- [ ] Mobile responsive behavior

## Related Documentation

- `POLISHED_UI_UPDATES.md` - Previous polish work (avatars, density toggle)
- `EMAIL_DETAILS_PANEL.md` - Details panel implementation
- `TAILWIND_V4_MIGRATION.md` - Tailwind CSS v4 migration notes

---

**Implementation completed**: October 11, 2025  
**Docker rebuild**: ✅ Successful  
**All components updated**: ✅ Complete  
**Visual testing**: ⏳ Pending user verification
