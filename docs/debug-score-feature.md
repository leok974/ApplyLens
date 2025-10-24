# Debug Score Feature

**Added**: v0.4.24
**Type**: Developer Tool / Production Debugging

---

## Overview

The `debugScore` URL parameter allows you to see raw Elasticsearch scores in the search results without needing to redeploy or access logs. This is perfect for validating that scoring boosts are working in production.

---

## Usage

### Enable Debug Mode

Add `?debugScore=1` to any search URL:

```
http://localhost:5176/search?q=Interview&debugScore=1
https://applylens.app/search?q=Offer&debugScore=1
```

Both `debugScore=1` and `debugScore=true` work.

### What You'll See

**Normal View** (without debugScore):
```
score: 3    [Only shown if score rounds to ≥1]
score: 0    [Hidden - this was the bug we fixed]
```

**Debug View** (with ?debugScore=1):
```
raw 3.14 / ~3     [Interview email with boost]
raw 0.42 / ~0     [Newsletter - low relevance]
raw 4.8 / ~5      [Offer email with strong boost]
raw 0.15 / ~0     [Promotion - low relevance]
```

---

## Visual Indicators

### 1. Header Badge

When debug mode is active, you'll see a yellow badge in the results header:

```
[debugScore ON] [ℹ Scoring]
```

This reminds you that you're in debug mode.

### 2. Score Display

**Format**: `raw X.XX / ~Y`
- `raw`: The exact float returned by Elasticsearch
- `~`: The rounded integer (what users normally see)

**Examples**:
- `raw 0.42 / ~0` - Scoring is working but rounds to 0 (hidden normally)
- `raw 3.14 / ~3` - Good relevance score
- `raw ? / ~?` - Score missing or undefined

---

## Why This Helps

### Problem 1: "Are scores all 0 or just hidden?"

**Without debug**: Can't tell if:
- Scores are actually `0.3`, `0.4` (which round to 0)
- Scoring pipeline isn't working at all
- Boosts aren't being applied

**With debug**: Immediately see raw values
- `raw 0.42 / ~0` → Scoring works, just low relevance ✓
- `raw ? / ~?` → Scoring isn't returning values ✗

### Problem 2: "Are my boosts working in production?"

**Without debug**: Need to:
- SSH into server
- Check Elasticsearch logs
- Run manual queries
- Build and deploy debug version

**With debug**: Just add `?debugScore=1`
- See `raw 4.8 / ~5` next to "Offer" → Boost working! ✓
- See `raw 0.1 / ~0` for everything → Boosts not applied ✗

### Problem 3: "Testing in production safely"

**This approach**:
- ✅ No code changes needed
- ✅ No redeploy required
- ✅ Works in any environment (dev/staging/prod)
- ✅ No security risk (just showing existing data)
- ✅ No performance impact
- ✅ Users don't see it unless they add the URL param

---

## Implementation Details

### Frontend Changes

**File**: `apps/web/src/pages/Search.tsx`

```tsx
// Extract debug flag from URL
const debugScore = searchParams.get('debugScore') === '1' ||
                  searchParams.get('debugScore') === 'true'

// Pass to header
<SearchResultsHeader
  query={query}
  total={total}
  showHint
  debugScore={debugScore}
/>

// Conditional score display
{debugScore ? (
  // Debug view: show raw + rounded
  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border">
    raw {h.score ?? "?"} / ~{Math.round(h.score) ?? "?"}
  </span>
) : (
  // Normal view: only if rounds to >= 1
  Math.round(h.score) > 0 && (
    <span>score: {Math.round(h.score)}</span>
  )
)}
```

**File**: `apps/web/src/components/SearchResultsHeader.tsx`

```tsx
// Add debugScore prop
type Props = {
  query: string;
  total?: number;
  showHint?: boolean;
  debugScore?: boolean
}

// Show debug badge when enabled
{debugScore && (
  <Badge className="text-yellow-600 bg-yellow-500/10 border-yellow-500/30">
    debugScore ON
  </Badge>
)}
```

---

## Use Cases

### 1. Validate Production Deployment

```bash
# After deploying new scoring logic:
https://applylens.app/search?q=Interview&debugScore=1

# Check that "Interview" emails show high scores:
# raw 3.2 / ~3  ✓ Boost applied (×3)
# raw 4.1 / ~4  ✓ Strong relevance
```

### 2. Debug Low Relevance

```bash
# Why are newsletters showing up?
https://applylens.app/search?q=job&debugScore=1

# See their scores:
# raw 0.3 / ~0  ← Low relevance, correctly hidden
# raw 0.15 / ~0 ← Very low, good
```

### 3. Compare Query Terms

```bash
# Test different queries:
?q=Interview&debugScore=1  → raw 3.2 / ~3
?q=Offer&debugScore=1      → raw 4.5 / ~5
?q=Application&debugScore=1 → raw 1.8 / ~2
```

### 4. Validate Label Boosts

```bash
# Check if "interview" label gives boost:
?q=*&labels=interview&debugScore=1

# Should see higher scores for labeled emails
```

---

## Testing

### Local Development

```bash
# Start dev server
cd apps/web
npm run dev

# Visit with debug enabled
http://localhost:5176/search?debugScore=1
```

### Production

```bash
# Safe to use in production (read-only)
https://applylens.app/search?q=Interview&debugScore=1
```

---

## Security & Privacy

**Safe to use in production because**:
- ✅ Only shows scores that already exist in the response
- ✅ No sensitive data exposed (just float numbers)
- ✅ No backend changes required
- ✅ No database queries affected
- ✅ Users must manually add URL parameter
- ✅ No cookies or sessions modified

**What it does NOT do**:
- ❌ Change how backend ranks results
- ❌ Expose internal APIs or auth tokens
- ❌ Show other users' data
- ❌ Impact performance
- ❌ Leave debug mode enabled for other users

---

## Future Enhancements

### Possible Additions

1. **Click to copy score** - Click badge to copy raw score to clipboard
2. **Score histogram** - Show distribution of scores in results
3. **Explain button** - Show ES explain JSON for why score is X
4. **Color coding** - Red for <1, Yellow for 1-3, Green for >3
5. **Persist debug mode** - Remember preference in localStorage

### Other Debug Params (Future)

```
?debugScore=1       ← Current feature
?debugQuery=1       ← Show ES query JSON
?debugTiming=1      ← Show request latencies
?debugHighlight=1   ← Show match positions
```

---

## Commit

**Hash**: `1c26841`
**Message**: "feat: add debugScore URL parameter to show raw score values"

**Files Changed**:
- `apps/web/src/pages/Search.tsx` - Added debugScore extraction and conditional rendering
- `apps/web/src/components/SearchResultsHeader.tsx` - Added debug badge

---

## Quick Reference

| URL Parameter | Effect |
|--------------|--------|
| `?debugScore=1` | Show raw scores: `raw 3.14 / ~3` |
| `?debugScore=true` | Same as above |
| (no param) | Normal mode: hide scores <1 |

**Badge Colors**:
- 🟡 Yellow badge = debug mode active
- ⚪ Outline badge = normal scoring info

---

**Status**: ✅ **IMPLEMENTED - Ready for Testing**

Test it now: http://localhost:5176/search?q=Interview&debugScore=1
