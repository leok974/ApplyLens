# Tracker Configuration System

## Overview

The ApplyLens Tracker UI now uses a centralized configuration system that allows customization of UI behavior without modifying component code. This makes it easy to tailor the application to different workflows, teams, or deployment environments.

**Status:** ✅ Production Ready  
**Date:** October 9, 2025

---

## Configuration File

**Location:** `apps/web/src/config/tracker.ts`

This file exports constants that control Tracker UI behavior. Currently supports note snippets, with extensibility for future settings.

---

## Note Snippets Configuration

### Default Behavior

By default, the Tracker displays 7 pre-configured snippet chips in the note editor:

```typescript
export const NOTE_SNIPPETS: string[] = [
  'Sent thank-you',
  'Follow-up scheduled',
  'Left voicemail',
  'Recruiter screen scheduled',
  'Sent take-home',
  'Referred by X',
  'Declined offer',
]
```text

### Environment Variable Override

You can customize snippets per environment using the `VITE_TRACKER_SNIPPETS` environment variable:

**Format:** Pipe-delimited string  
**Example:** `"Sent thank-you|Follow-up scheduled|Left voicemail"`

**Behavior:**

- If `VITE_TRACKER_SNIPPETS` is set: Uses environment variable (splits by `|`)
- If `VITE_TRACKER_SNIPPETS` is not set: Uses default array from config
- Empty strings are automatically filtered out

---

## Usage Examples

### Example 1: Development Environment (Minimal Snippets)

**File:** `apps/web/.env.development`

```bash
# Only show essential snippets during development
VITE_TRACKER_SNIPPETS="Sent thank-you|Follow-up scheduled|Left voicemail"
```text

### Example 2: Production Environment (Full Set)

**File:** `apps/web/.env.production`

```bash
# Show complete set of snippets in production
VITE_TRACKER_SNIPPETS="Sent thank-you|Follow-up scheduled|Left voicemail|Recruiter screen scheduled|Sent take-home|Referred by X|Declined offer"
```text

### Example 3: Custom Workflow

**File:** `apps/web/.env.local`

```bash
# Custom snippets for sales pipeline
VITE_TRACKER_SNIPPETS="Demo scheduled|Proposal sent|Contract signed|Payment received|Closed - Lost"
```text

### Example 4: No Environment Variable

If you don't set `VITE_TRACKER_SNIPPETS`, the application uses the default snippets defined in `config/tracker.ts`.

---

## How It Works

### 1. Configuration File (`config/tracker.ts`)

```typescript
// Check for environment variable
const ENV_SNIPPETS = (import.meta as any).env?.VITE_TRACKER_SNIPPETS as string | undefined

// Use env var if present, otherwise use defaults
export const NOTE_SNIPPETS: string[] = ENV_SNIPPETS
  ? ENV_SNIPPETS.split('|').map((s) => s.trim()).filter(Boolean)
  : [
      'Sent thank-you',
      'Follow-up scheduled',
      // ... other defaults
    ]
```text

### 2. Tracker Integration

```typescript
import { NOTE_SNIPPETS } from '../config/tracker'

// In the component
<InlineNote
  snippets={NOTE_SNIPPETS}
  // ... other props
/>
```text

### 3. Runtime Evaluation

1. **Build time:** Vite reads environment variables from `.env` files
2. **Config loads:** `tracker.ts` checks for `VITE_TRACKER_SNIPPETS`
3. **Array created:** Either from env var (split by `|`) or from defaults
4. **Component renders:** InlineNote receives the configured snippets

---

## Setup Instructions

### Step 1: Create Environment File

```bash
cd apps/web
cp .env.example .env.local
```text

### Step 2: Set Snippets

Edit `.env.local`:

```bash
VITE_TRACKER_SNIPPETS="Custom 1|Custom 2|Custom 3"
```text

### Step 3: Restart Dev Server

```bash
npm run dev
```text

**Important:** Environment variables are read at build/start time. You must restart the dev server for changes to take effect.

### Step 4: Verify

1. Open browser to <http://localhost:5175/tracker>
2. Click any note preview to open editor
3. Check that snippet chips match your configuration

---

## Customization Scenarios

### Scenario 1: Different Snippets per Environment

**Development:** Minimal set for testing

```bash
# .env.development
VITE_TRACKER_SNIPPETS="Test 1|Test 2"
```text

**Production:** Full set for end users

```bash
# .env.production
VITE_TRACKER_SNIPPETS="Sent thank-you|Follow-up scheduled|Left voicemail|Recruiter screen scheduled|Sent take-home|Referred by X|Declined offer"
```text

### Scenario 2: Team-Specific Workflows

**Team A (Engineering Recruiting):**

```bash
VITE_TRACKER_SNIPPETS="Technical screen passed|Coding challenge sent|System design completed|Team match scheduled|Offer extended"
```text

**Team B (Sales Pipeline):**

```bash
VITE_TRACKER_SNIPPETS="Discovery call|Demo scheduled|Proposal sent|Contract negotiation|Closed-won|Closed-lost"
```text

### Scenario 3: Industry-Specific

**Academia:**

```bash
VITE_TRACKER_SNIPPETS="Application submitted|Shortlisted|Interview scheduled|Campus visit|Offer received|Accepted position"
```text

**Freelance:**

```bash
VITE_TRACKER_SNIPPETS="Inquiry received|Proposal sent|Contract signed|Milestone completed|Payment received|Project closed"
```text

### Scenario 4: Multi-Tenant Deployment

Use environment variables in your deployment pipeline:

```bash
# Tenant A
docker run -e VITE_TRACKER_SNIPPETS="Snippet A1|Snippet A2" applylens-web

# Tenant B
docker run -e VITE_TRACKER_SNIPPETS="Snippet B1|Snippet B2" applylens-web
```text

---

## Advanced Usage

### Programmatic Customization

While environment variables work for most cases, you can also modify `config/tracker.ts` directly:

```typescript
// Example: Load from API at runtime
let runtimeSnippets: string[] | null = null

export async function loadSnippetsFromAPI() {
  const response = await fetch('/api/config/snippets')
  runtimeSnippets = await response.json()
}

export const NOTE_SNIPPETS: string[] = runtimeSnippets || [
  // ... defaults
]
```text

### Conditional Logic

```typescript
// Example: Different snippets based on user role
const isAdmin = localStorage.getItem('userRole') === 'admin'

export const NOTE_SNIPPETS: string[] = isAdmin
  ? ['Admin action 1', 'Admin action 2']
  : ['User action 1', 'User action 2']
```text

### Dynamic Import

```typescript
// Example: Load snippets based on feature flag
const featureFlags = JSON.parse(localStorage.getItem('features') || '{}')

export const NOTE_SNIPPETS: string[] = featureFlags.experimentalSnippets
  ? ['Experimental 1', 'Experimental 2']
  : ['Standard 1', 'Standard 2']
```text

---

## Future Configuration Options

The `config/tracker.ts` file is designed to be extensible. Future additions might include:

### Status Labels

```typescript
export const STATUS_LABEL: Record<string, string> = {
  applied: 'Application Sent',
  hr_screen: 'HR Screening',
  interview: 'Interviewing',
  // ...
}
```text

### Toast Variants

```typescript
export const STATUS_TO_VARIANT: Record<string, ToastVariant> = {
  applied: 'default',
  hr_screen: 'info',
  interview: 'success',
  // ...
}
```text

### Table Columns

```typescript
export const VISIBLE_COLUMNS = [
  'company',
  'role',
  'status',
  'notes',
  'actions',
]
```text

### Filters

```typescript
export const DEFAULT_FILTERS = {
  status: 'all',
  dateRange: 'last-30-days',
}
```text

---

## Testing

### Test with Different Configurations

```bash
# Test with custom snippets
VITE_TRACKER_SNIPPETS="Test 1|Test 2|Test 3" npm run dev

# Test with empty (uses defaults)
npm run dev

# Test E2E with custom config
VITE_TRACKER_SNIPPETS="Sent thank-you" npx playwright test
```text

### Verify Configuration Loading

Add debug logging to `config/tracker.ts`:

```typescript
const ENV_SNIPPETS = (import.meta as any).env?.VITE_TRACKER_SNIPPETS as string | undefined
console.log('ENV_SNIPPETS:', ENV_SNIPPETS)

export const NOTE_SNIPPETS: string[] = ENV_SNIPPETS
  ? ENV_SNIPPETS.split('|').map((s) => s.trim()).filter(Boolean)
  : [/* defaults */]

console.log('NOTE_SNIPPETS:', NOTE_SNIPPETS)
```text

---

## Troubleshooting

### Issue: Snippets don't change after editing .env file

**Solution:** Restart the Vite dev server

```bash
# Stop server (Ctrl+C)
npm run dev
```text

### Issue: Environment variable not recognized

**Symptoms:** Always uses default snippets

**Solutions:**

1. Check file name: Must be `.env`, `.env.local`, `.env.development`, or `.env.production`
2. Check variable name: Must start with `VITE_` prefix
3. Check format: Use pipe delimiter `|`, not commas or semicolons
4. Restart dev server after changes

### Issue: Snippets appear but are wrong

**Solutions:**

1. Check for typos in environment variable value
2. Verify no extra spaces (they're trimmed, but check anyway)
3. Check for special characters that might break parsing
4. Add debug logging to see what's being loaded

### Issue: Empty snippets array

**Symptoms:** No snippet chips appear in editor

**Solutions:**

1. Check if `VITE_TRACKER_SNIPPETS` is set to empty string
2. Verify pipe delimiters are correct
3. Check that snippets aren't all empty strings (filtered out)
4. Fall back to defaults by unsetting the env var

---

## Migration Guide

### From Hardcoded Snippets

**Before:**

```tsx
<InlineNote
  snippets={['Custom 1', 'Custom 2']}
/>
```text

**After:**

```tsx
import { NOTE_SNIPPETS } from '../config/tracker'

<InlineNote
  snippets={NOTE_SNIPPETS}
/>
```text

### From Component Props

If you were passing snippets as props through multiple components:

**Before:**

```tsx
function ParentComponent() {
  const snippets = ['Custom 1', 'Custom 2']
  return <ChildComponent snippets={snippets} />
}

function ChildComponent({ snippets }) {
  return <InlineNote snippets={snippets} />
}
```text

**After:**

```tsx
import { NOTE_SNIPPETS } from '../config/tracker'

function ChildComponent() {
  return <InlineNote snippets={NOTE_SNIPPETS} />
}
```text

---

## Best Practices

### 1. **Use Environment Variables for Deployment-Specific Config**

- Different snippets per environment (dev/staging/prod)
- Team-specific deployments
- Multi-tenant setups

### 2. **Keep Defaults in Code for Documentation**

- Fallback array shows what snippets look like
- Self-documenting code
- No external dependency for basic functionality

### 3. **Document Custom Snippets**

- Add comments in `.env` files
- Create team documentation for snippet meanings
- Keep snippet names clear and concise

### 4. **Test Configuration Changes**

- Verify snippets load correctly
- Test that chips render properly
- Ensure E2E tests still pass

### 5. **Version Control .env.example**

- Commit `.env.example` with documentation
- Never commit `.env.local` (contains secrets)
- Update example when adding new variables

---

## Security Considerations

### Safe for Client-Side

Environment variables starting with `VITE_` are:

- ✅ Embedded in client-side JavaScript bundle
- ✅ Visible to users in browser DevTools
- ✅ Safe for non-sensitive configuration

**Do NOT use for:**

- ❌ API keys
- ❌ Secrets or passwords
- ❌ Private configuration

### Public Configuration Only

Snippet chips are UI-only configuration. They don't affect:

- API behavior
- Database queries
- Authentication
- Authorization

---

## Summary

**What Was Built:**

- ✅ Centralized configuration file (`config/tracker.ts`)
- ✅ Environment variable support (`VITE_TRACKER_SNIPPETS`)
- ✅ Fallback to sensible defaults
- ✅ Example `.env` file with documentation
- ✅ Extensible pattern for future config options

**Benefits:**

- 🎯 Customize snippets without code changes
- 🚀 Deploy different configs per environment
- 👥 Support team-specific workflows
- 🏢 Enable multi-tenant deployments
- 📦 Maintain backward compatibility

**Production Ready:**

- ✅ No TypeScript errors
- ✅ Backward compatible
- ✅ Well-documented
- ✅ Tested configuration loading
- ✅ Example files provided

---

## Related Documentation

- **InlineNote Component:** `INLINE_NOTE_FEATURE_COMPLETE.md`
- **Snippet Chips:** `INLINE_NOTE_SNIPPETS_SUMMARY.md`
- **Quick Reference:** `INLINE_NOTE_QUICKREF.md`

---

**Feature Complete:** October 9, 2025  
**Developer:** GitHub Copilot  
**Status:** ✅ Production Ready
