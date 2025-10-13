# Design Token Migration Quick Reference

## Color Mapping (Before → After)

### Light Mode

| Element | Before (Harsh) | After (Soft) | Change |
|---------|----------------|--------------|--------|
| Page background | `hsl(0 0% 100%)` pure white | `hsl(210 20% 97%)` warm gray | Added warmth, reduced glare |
| Card background | `bg-white` | `bg-card` = `hsl(210 25% 98%)` | Subtle elevation |
| Muted areas | `bg-slate-50` = `hsl(210 40% 98%)` | `bg-[color:hsl(var(--color-muted))]` = `hsl(210 23% 94%)` | Lower saturation |
| Borders | `border-slate-200` = `hsl(214 31.8% 91.4%)` | `border-[color:hsl(var(--color-border))]` = `hsl(215 20% 85%)` | Less contrast |
| Accent | `bg-indigo-500` = `hsl(239 84% 67%)` | `bg-[color:hsl(var(--color-accent))]` = `hsl(221 75% 64%)` | Consistent brand color |

### Dark Mode

| Element | Before (Harsh) | After (Soft) | Change |
|---------|----------------|--------------|--------|
| Page background | `hsl(222.2 84% 4.9%)` deep navy | `hsl(222 33% 10%)` midnight slate | Mid-contrast, less saturation |
| Card background | `bg-slate-900` = `hsl(222.2 84% 4.9%)` | `bg-card` = `hsl(222 26% 14%)` | Elevated from background |
| Muted areas | `bg-slate-800` = `hsl(215 27.9% 16.9%)` | `bg-[color:hsl(var(--color-muted))]` = `hsl(222 20% 18%)` | Consistent with palette |
| Borders | `border-slate-800` = `hsl(215 27.9% 16.9%)` | `border-[color:hsl(var(--color-border))]` = `hsl(222 20% 22%)` | Low contrast |
| Accent | `bg-indigo-500` | `bg-[color:hsl(var(--color-accent))]` = `hsl(221 75% 66%)` | Slightly brighter |

## Component-Specific Changes

### EmailRow Cards

```tsx
// BEFORE (Harsh)
<div className="rounded-2xl border bg-white shadow-sm">
  <h3 className="font-semibold text-[15px]">Subject</h3>
  <p className="text-slate-600 text-sm">Preview text</p>
  <Archive className="h-4 w-4" /> {/* Pure white in dark */}
</div>

// AFTER (Soft)
<div className="rounded-xl border border-[color:hsl(var(--color-border))] bg-card shadow-sm">
  <h3 className="font-semibold text-base leading-snug">Subject</h3>
  <p className="text-slate-600 dark:text-slate-300 text-[13px] leading-relaxed">Preview text</p>
  <Archive className="h-4 w-4 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200" />
</div>
```text

**Key improvements:**

- `rounded-2xl` → `rounded-xl` (less extreme)
- `bg-white` → `bg-card` (semantic, theme-aware)
- `text-[15px]` → `text-base leading-snug` (better readability)
- `text-sm` → `text-[13px] leading-relaxed` (precise, comfortable)
- Icon color: explicit `slate-400` with hover states

### Section Headers

```tsx
// BEFORE (Harsh)
<div className="border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
  <span className="bg-indigo-500" />
  Today
</div>

// AFTER (Soft)
<div className="border border-[color:hsl(var(--color-border))] bg-card">
  <span className="bg-[color:hsl(var(--color-accent))]" />
  Today
</div>
```text

**Key improvements:**

- CSS variables replace hardcoded Tailwind classes
- Automatic dark mode handling (no duplicate classes)
- Consistent with design system

### Page Header

```tsx
// BEFORE (Harsh)
<div className="border-b bg-white">
  <Mail className="h-5 w-5" />
  <Button variant="secondary" size="icon">
    <Search />
  </Button>
</div>

// AFTER (Soft)
<header className="border-b border-[color:hsl(var(--color-border))] 
  bg-[color:hsl(var(--color-background))]/80 backdrop-blur">
  <Mail className="h-5 w-5 text-[color:hsl(var(--color-accent))]" />
  <Button variant="outline" size="icon">
    <Search />
  </Button>
</header>
```text

**Key improvements:**

- Semantic HTML (`<header>` instead of `<div>`)
- Backdrop blur with 80% opacity (glassmorphism)
- Accent color for branding
- Outline button instead of secondary (less visual weight)

### Bulk Actions Bar

```tsx
// BEFORE (Harsh)
<div className="bg-slate-50/80 dark:bg-slate-900/60">
  <Button variant="secondary">Archive</Button>
  <Button variant="secondary">Mark safe</Button>
</div>

// AFTER (Soft)
<div className="bg-[color:hsl(var(--color-muted))]/60 backdrop-blur">
  <Button variant="outline">Archive</Button>
  <Button variant="outline">Mark safe</Button>
</div>
```text

**Key improvements:**

- Muted background (semantic)
- Outline buttons (less glare, better hierarchy)

## Typography Scale

| Use Case | Before | After | Reason |
|----------|--------|-------|--------|
| Email subject | `text-[15px]` | `text-base leading-snug` | Standard size with tight leading |
| Email preview | `text-sm` | `text-[13px] leading-relaxed` | Precise size with comfortable spacing |
| Body text | `leading-normal` (1.5) | `leading-relaxed` (1.625) | Better readability |
| Headings | No explicit leading | `leading-snug` (1.375) | Compact but not cramped |

## Icon Color Strategy

```tsx
// BEFORE: No explicit color (inherited, often pure white in dark)
<Archive className="h-4 w-4" />

// AFTER: Soft default with gentle hover
<Archive className="h-4 w-4 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200" />
```text

**Pattern:**

- Default: `text-slate-400`
- Light hover: `hover:text-slate-600`
- Dark hover: `dark:hover:text-slate-200`

## Button Hierarchy

| Priority | Variant | Use Case | Example |
|----------|---------|----------|---------|
| Primary | `default` with accent bg | Critical actions only | "Save changes", "Submit application" |
| Secondary | `outline` | Most actions | "Archive", "Mark safe", Search |
| Tertiary | `ghost` | Inline/subtle actions | Close panel, dismiss |

**Changed:**

- Bulk actions: `secondary` → `outline`
- Search button: `secondary` → `outline`
- Reserve filled buttons for truly primary actions

## CSS Variable Syntax

For Tailwind v4 compatibility with CSS variables:

```tsx
// ✅ CORRECT
className="bg-[color:hsl(var(--color-background))]"
className="border-[color:hsl(var(--color-border))]"
className="text-[color:hsl(var(--color-accent))]"

// ❌ WRONG (Tailwind v3 style)
className="bg-background"  // Won't work with Tailwind v4 CSS-first
className="border-border"

// ✅ ALSO CORRECT (Semantic aliases defined in @theme)
className="bg-card"         // Maps to --color-card
className="text-foreground" // Maps to --color-foreground
```text

## Migration Pattern

When updating components:

1. **Find hardcoded colors:**

   ```bash
   grep -r "bg-white\|border-slate-200\|bg-slate-50" components/
   ```

2. **Replace with CSS variables:**
   - `bg-white` → `bg-card`
   - `border-slate-200` → `border-[color:hsl(var(--color-border))]`
   - `bg-slate-50` → `bg-[color:hsl(var(--color-muted))]`

3. **Remove dark mode duplicates:**
   - `dark:border-slate-800` → remove (handled by CSS variable)
   - `dark:bg-slate-900` → remove (handled by `bg-card`)

4. **Add typography improvements:**
   - Headings: Add `leading-snug`
   - Body text: Add `leading-relaxed`
   - Preview text: Use `text-[13px]` instead of `text-sm`

5. **Update icon colors:**
   - Add `text-slate-400 hover:text-slate-600 dark:hover:text-slate-200`

## Visual Testing

After migration, verify:

- [ ] Cards have warm gray background (not stark white)
- [ ] Borders are subtle (low contrast)
- [ ] Text breathes (not cramped)
- [ ] Icons are muted (not bright white)
- [ ] Dark mode feels midnight blue (not pure black)
- [ ] Hover states are smooth
- [ ] Backdrop blur works on header
- [ ] Section headers float above content

## Accessibility Checklist

- [x] WCAG AA contrast ratios maintained
- [x] Focus states preserved
- [x] Semantic HTML used
- [x] ARIA attributes intact
- [ ] Screen reader testing
- [ ] High contrast mode testing

---

**Quick tip**: Use browser DevTools to toggle dark mode rapidly:

```javascript
// In console:
document.documentElement.classList.toggle('dark')
```text
