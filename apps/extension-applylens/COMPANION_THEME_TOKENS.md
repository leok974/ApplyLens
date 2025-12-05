# ApplyLens Companion Design Tokens

Centralized design system for the Chrome extension UI (popup + sidepanel) to match applylens.app.

---

## Color Palette

### Background Colors

**Dark Mode** (default):
```css
--bg-primary: #020617        /* slate-950 - Main background */
--bg-secondary: #0f172a      /* slate-900 - Cards, panels */
--bg-tertiary: #1e293b       /* slate-800 - Hover states */
```

**Light Mode**:
```css
--bg-primary: #f8fafc        /* slate-50 - Main background */
--bg-secondary: #ffffff      /* white - Cards, panels */
--bg-tertiary: #f1f5f9       /* slate-100 - Hover states, metrics */
```

### Text Colors

**Dark Mode**:
```css
--text-primary: #f8fafc      /* slate-50 - Headings, main text */
--text-secondary: #cbd5e1    /* slate-300 - Secondary text, inactive states */
--text-muted: #94a3b8        /* slate-400 - Muted text, labels */
```

**Light Mode**:
```css
--text-primary: #0f172a      /* slate-900 - Headings, main text */
--text-secondary: #475569    /* slate-600 - Secondary text */
--text-muted: #64748b        /* slate-500 - Muted text, labels */
```

### Accent Colors

**Cyan (Primary Accent)**:
```css
--accent-cyan-primary: #22d3ee   /* cyan-400 - Primary actions, highlights */
--accent-cyan-light: #67e8f9     /* cyan-300 - Lighter accents */
--accent-cyan-dark: #06b6d4      /* cyan-500 - Darker accents (light mode) */
```

**Emerald (Success/Status)**:
```css
--accent-emerald: #34d399        /* emerald-400 - Success states, online status */
--accent-emerald-light: #6ee7b7  /* emerald-300 - Lighter success */
--accent-emerald-dark: #10b981   /* emerald-500 - Darker success (light mode) */
```

**Blue (Gradients)**:
```css
--accent-blue: #3b82f6           /* blue-500 - Gradient end */
--accent-blue-dark: #2563eb      /* blue-600 - Darker gradient */
```

**Red (Error/Warning)**:
```css
--accent-red: #f87171            /* red-400 - Error states */
--accent-red-dark: #ef4444       /* red-500 - Darker errors */
```

**Indigo (AI Suggestions)**:
```css
--accent-indigo: #818cf8         /* indigo-400 - AI suggestion badges */
--accent-indigo-light: #a5b4fc   /* indigo-300 - Lighter AI accents */
```

### Border Colors

**Dark Mode**:
```css
--border-default: rgba(51, 65, 85, 0.7)    /* slate-700/70 - Default borders */
--border-muted: rgba(71, 85, 105, 0.6)     /* slate-600/60 - Subtle borders */
--border-accent: rgba(34, 211, 238, 0.7)   /* cyan-400/70 - Active/focused borders */
--border-success: rgba(52, 211, 153, 0.6)  /* emerald-400/60 - Success borders */
```

**Light Mode**:
```css
--border-default: #e2e8f0        /* slate-200 - Default borders */
--border-muted: #cbd5e1          /* slate-300 - Subtle borders */
--border-accent: #22d3ee         /* cyan-400 - Active/focused borders */
--border-success: rgba(52, 211, 153, 0.7)  /* emerald-400/70 - Success borders */
```

---

## Typography

### Font Families
```css
--font-sans: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif
```

### Font Sizes
```css
--text-xs: 10px        /* Labels, timestamps */
--text-sm: 11px        /* Secondary text, badges */
--text-base: 12px      /* Body text, descriptions */
--text-md: 13px        /* Metrics, button text */
--text-lg: 14px        /* Section headings */
--text-xl: 16px        /* Main headings */
--text-2xl: 19px       /* Large headings (popup title) */
```

### Font Weights
```css
--font-normal: 400
--font-medium: 500
--font-semibold: 600
--font-bold: 700
```

---

## Spacing

### Gaps & Padding
```css
--space-1: 0.25rem    /* 4px */
--space-2: 0.5rem     /* 8px */
--space-3: 0.75rem    /* 12px */
--space-4: 1rem       /* 16px */
--space-5: 1.25rem    /* 20px */
--space-6: 1.5rem     /* 24px */
```

### Layout Dimensions
```css
--popup-width: 420px
--popup-height: 640px
--popup-sidebar-width: 96px     /* 24 × 4px = 96px (w-24) */

--sidepanel-width: 420px
--sidepanel-height: 92vh
```

---

## Border Radius

### Custom Radii (ApplyLens specific)
```css
--radius-alp-xl: 1.75rem    /* 28px - Main cards, panels */
--radius-alp-lg: 1.25rem    /* 20px - Metrics, buttons */
```

### Standard Radii
```css
--radius-sm: 0.375rem       /* 6px */
--radius-md: 0.5rem         /* 8px */
--radius-lg: 0.75rem        /* 12px */
--radius-xl: 1rem           /* 16px */
--radius-2xl: 1.5rem        /* 24px */
--radius-full: 9999px       /* Circular elements */
```

---

## Shadows

### Box Shadows

**Cyan Glow (Primary)**:
```css
--shadow-alp-glow: 0 0 28px rgba(56, 189, 248, 0.55)
--shadow-alp-glow-sm: 0 0 18px rgba(56, 189, 248, 0.35)
--shadow-alp-glow-xs: 0 0 8px rgba(56, 189, 248, 0.8)
```

**Emerald Glow (Success)**:
```css
--shadow-emerald-glow: 0 0 8px rgba(52, 211, 153, 0.8)
```

**Standard Shadows**:
```css
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05)
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1)
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1)
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1)
--shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25)
```

---

## Gradients

### Radial Gradients
```css
--gradient-radial-dark: radial-gradient(circle, #020617, #020617, #0f172a)
--gradient-radial-accent: radial-gradient(circle, rgba(34, 211, 238, 0.3), transparent)
```

### Linear Gradients
```css
--gradient-primary: linear-gradient(to top right, #22d3ee, #3b82f6)
--gradient-scan-progress: linear-gradient(to right, #22d3ee, #3b82f6, #22d3ee)
```

---

## Component-Specific Tokens

### Status Pills

**Connected (Online)**:
```css
Dark: bg-emerald-500/10, border-emerald-400/60, text-emerald-300
Light: bg-emerald-100, border-emerald-400/70, text-emerald-700
```

**Scanning (In Progress)**:
```css
Dark: bg-cyan-500/10, border-cyan-400/60, text-cyan-200
Light: bg-cyan-100, border-cyan-400/70, text-cyan-700
```

**Idle/Offline**:
```css
Dark: bg-slate-900/80, border-slate-600/60, text-slate-300
Light: bg-slate-100, border-slate-300, text-slate-600
```

### Field Source Badges

**Profile (Trusted)**:
```css
Dark: bg-emerald-500/15, text-emerald-300
Light: bg-emerald-100, text-emerald-700
```

**Learned (Trusted)**:
```css
Dark: bg-cyan-500/15, text-cyan-300
Light: bg-cyan-100, text-cyan-700
```

**AI Suggestion**:
```css
Dark: bg-indigo-500/15, text-indigo-200
Light: bg-indigo-100, text-indigo-700
```

**Manual/Unknown**:
```css
Dark: bg-slate-700/30, text-slate-400
Light: bg-slate-200, text-slate-600
```

### Buttons

**Primary Action**:
```css
Background: linear-gradient(to top right, cyan-400, blue-600)
Text: slate-950
Shadow: --shadow-alp-glow
Hover: brightness(110%)
```

**Secondary Action**:
```css
Dark: border-cyan-400/70, bg-slate-950/70, text-cyan-300, shadow-alp-glow-sm
Light: border-cyan-400, bg-white, text-cyan-700, hover:bg-cyan-50
```

**Tertiary/Outline**:
```css
Dark: border-slate-600/80, bg-slate-900/90, text-slate-200
Light: border-slate-300, bg-white, text-slate-800
```

---

## Theme Toggle

### Icon States
```css
Dark Mode Icon: ☀️ (Sun - click to switch to light)
Light Mode Icon: 🌙 (Moon - click to switch to dark)
```

### Storage Key
```javascript
const THEME_KEY = 'applylens_companion_theme';
// Values: 'light' | 'dark'
// Default: 'dark'
```

---

## Tailwind Config Reference

These tokens map to `tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    extend: {
      boxShadow: {
        'alp-glow': '0 0 28px rgba(56,189,248,0.55)',
      },
      borderRadius: {
        'alp-xl': '1.75rem',
        'alp-lg': '1.25rem',
      },
    },
  },
}
```

---

## Usage Guidelines

### When to Update

Update this file when:
- Adding new accent colors or semantic colors
- Changing brand colors to match applylens.app
- Adding new shadow effects or glows
- Modifying border radii for consistency
- Introducing new component patterns

### Consistency Rules

1. **Always use semantic color names** (e.g., `--accent-cyan-primary`) instead of raw hex values
2. **Match applylens.app exactly** - check the web app for color accuracy
3. **Use opacity variants** (e.g., `/70`, `/60`) for borders and overlays
4. **Keep dark/light variants symmetrical** - same visual hierarchy in both themes
5. **Test both themes** before committing color changes

### Component Class Naming

All component classes use the `alp-` prefix:
- `alp-theme-*` - Theme classes
- `alp-popup-*` - Popup-specific components
- `alp-panel`, `alp-metric-card`, `alp-tabs`, etc. - Shared components
- `alp-btn-*` - Button variants
- `alp-status-pill` - Status indicators

---

## Cross-Reference

**Related Files**:
- `src/popup.css` - Component definitions using `@layer components`
- `tailwind.config.js` - Tailwind customization
- `popup.html` - Popup UI implementation
- `sidepanel.html` - Sidepanel UI implementation
- `popup.js` - Theme toggle logic (popup)
- `sidepanel.js` - Theme toggle logic (sidepanel)

**Documentation**:
- `TAILWIND.md` - Tailwind build system and component usage
- `SIDEPANEL_WIRING.md` - Sidepanel message protocol and data flow
