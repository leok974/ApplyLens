# Tailwind CSS Setup for ApplyLens Extension

## Overview

This extension uses **Tailwind CSS v3** for styling both `popup.html` and `sidepanel.html` with a shared build system and **reusable component classes** that support light/dark themes.

## File Structure

- **`src/popup.css`**: Tailwind input file with `@tailwind` directives and custom `@layer components`
- **`popup.css`**: Generated output (minified) - loaded by both popup.html and sidepanel.html
- **`tailwind.config.js`**: Configuration with custom theme extensions
- **`package.json`**: Build scripts for development and production

## Reusable Components

We use `@layer components` to define reusable CSS classes that automatically adapt to light/dark themes:

### Theme System

**Root Classes**:
- `.alp-theme-root` - Applied to `<body>`, sets baseline styles
- `.alp-theme-dark` - Dark mode theme (default)
- `.alp-theme-light` - Light mode theme

**Usage**:
```html
<body class="alp-theme-root alp-theme-dark">
  <!-- All child elements inherit theme-aware styles -->
</body>
```

### Component Classes

**Layout**:
- `.alp-panel` - Main sidepanel card (420×92vh with border and shadow)
- `.alp-metric-card` - Metric display card with border and padding
- `.alp-tabs` - Tab navigation container
- `.alp-tab` - Individual tab button
- `.alp-tab-active` - Active tab state (use with `.alp-tab`)

**Content**:
- `.alp-field-rows` - Field rows container with scrolling
- `.alp-field-row` - Individual field row grid layout
- `.alp-status-pill` - Status indicator pill (Connected/Scanning/Idle)

**Buttons**:
- `.alp-btn-primary` - Primary action button (gradient with glow)
- `.alp-btn-secondary` - Secondary action button (outlined)

### Theme-Aware Styling

All component classes automatically adapt to the current theme:

**Dark Mode** (`.alp-theme-dark`):
- Background: slate-950, slate-900
- Text: slate-50, slate-300, slate-400
- Accents: cyan-400, emerald-400
- Borders: slate-700/70

**Light Mode** (`.alp-theme-light`):
- Background: white, slate-50, slate-100
- Text: slate-900, slate-800, slate-600
- Accents: cyan-400, emerald-700
- Borders: slate-200, slate-300

## Custom Theme Extensions

Defined in `tailwind.config.js`:

```javascript
boxShadow: {
  'alp-glow': '0 0 28px rgba(56,189,248,0.55)' // Cyan neon glow
}
borderRadius: {
  'alp-xl': '1.75rem',  // 28px
  'alp-lg': '1.25rem'   // 20px
}
```

## Theme Toggle

The sidepanel includes a light/dark mode toggle:

**Implementation**:
```javascript
// Store preference in localStorage
const THEME_KEY = 'applylens_companion_theme';

function applyTheme(theme) {
  document.body.classList.remove('alp-theme-light', 'alp-theme-dark');
  document.body.classList.add(theme === 'light' ? 'alp-theme-light' : 'alp-theme-dark');
}
```

**UI**:
- Button shows ☀️ in dark mode (click to switch to light)
- Button shows 🌙 in light mode (click to switch to dark)
- Preference persists across sessions

## Build Commands

**Production Build** (minified):
```bash
pnpm run build:css
```

**Development Build** (watch mode):
```bash
pnpm run dev:css
```

## Usage

After making changes to classes in `popup.html`, `popup.js`, `sidepanel.html`, or `sidepanel.js`:

1. Run `pnpm run build:css` to regenerate `popup.css`
2. Reload the extension in `chrome://extensions`
3. Test both light and dark themes

## Example Component Usage

**Before** (verbose Tailwind utilities):
```html
<div class="rounded-alp-lg border border-slate-700/70 bg-slate-900/90 px-2.5 py-1.5">
  <div class="text-slate-400">Fields</div>
  <div class="mt-0.5 text-[13px] font-semibold">11</div>
</div>
```

**After** (reusable component):
```html
<div class="alp-metric-card">
  <div class="text-slate-400">Fields</div>
  <div class="mt-0.5 text-[13px] font-semibold">11</div>
</div>
```

Benefits:
- Shorter HTML markup
- Automatic theme switching
- Consistent styling across views
- Easier maintenance

## Color Palette

Following ApplyLens brand colors:

- **Background**: `slate-950`, `slate-900`
- **Accent**: `cyan-400`, `cyan-300`
- **Text**: `slate-50` (main), `slate-400` (muted)
- **Borders**: `slate-700/70` (with 70% opacity)
