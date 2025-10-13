# Tracker Configuration - Quick Reference

## Config File Location

`apps/web/src/config/tracker.ts`

## Usage in Components

```tsx
import { NOTE_SNIPPETS } from '../config/tracker'

<InlineNote snippets={NOTE_SNIPPETS} />
```text

## Default Snippets

7 pre-configured phrases:

1. Sent thank-you
2. Follow-up scheduled
3. Left voicemail
4. Recruiter screen scheduled
5. Sent take-home
6. Referred by X
7. Declined offer

## Environment Override

**Variable:** `VITE_TRACKER_SNIPPETS`  
**Format:** Pipe-delimited string  
**Example:** `"Custom 1|Custom 2|Custom 3"`

### Setup

```bash
# 1. Create .env.local file
cd apps/web
cp .env.example .env.local

# 2. Set custom snippets
echo 'VITE_TRACKER_SNIPPETS="Sent thank-you|Follow-up scheduled|Left voicemail"' >> .env.local

# 3. Restart dev server
npm run dev
```text

## Examples

### Development (Minimal)

```bash
# .env.development
VITE_TRACKER_SNIPPETS="Test 1|Test 2|Test 3"
```text

### Production (Full)

```bash
# .env.production
VITE_TRACKER_SNIPPETS="Sent thank-you|Follow-up scheduled|Left voicemail|Recruiter screen scheduled|Sent take-home|Referred by X|Declined offer"
```text

### Custom Workflow

```bash
# .env.local
VITE_TRACKER_SNIPPETS="Demo scheduled|Proposal sent|Contract signed|Payment received"
```text

## How It Works

1. **Vite reads** `.env` files at build/start time
2. **Config checks** for `VITE_TRACKER_SNIPPETS`
3. **If found:** Splits by `|`, trims, filters empty strings
4. **If not found:** Uses default array
5. **Component imports** and renders configured snippets

## Important Notes

- ⚠️ **Must restart dev server** after changing `.env` files
- ✅ Variable must start with `VITE_` prefix
- ✅ Use pipe `|` delimiter (not comma or semicolon)
- ✅ Empty strings are automatically filtered out
- ✅ Leading/trailing spaces are trimmed

## Files

| File | Purpose |
|------|---------|
| `config/tracker.ts` | Centralized configuration |
| `.env.example` | Template with examples |
| `.env.local` | Local overrides (gitignored) |
| `.env.development` | Dev environment |
| `.env.production` | Prod environment |

## Testing

```bash
# Test with custom snippets
VITE_TRACKER_SNIPPETS="Test 1|Test 2" npm run dev

# Test with defaults
npm run dev
```text

## Documentation

- Full guide: `TRACKER_CONFIG_SYSTEM.md`
- Component docs: `INLINE_NOTE_FEATURE_COMPLETE.md`
- Snippets: `INLINE_NOTE_SNIPPETS_SUMMARY.md`

## Status

✅ Production Ready

- Centralized config
- Environment support
- Backward compatible
- Well documented
