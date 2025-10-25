# Debug Score Feature - Quick Summary

**Status**: ✅ **IMPLEMENTED** (Commit `1c26841`)
**Version**: Ready for v0.4.24
**Location**: Local dev server (can test now)

---

## What It Does

Adds `?debugScore=1` URL parameter to show raw Elasticsearch scores in search results.

**Normal view**:
```
score: 3     [Only shown if ≥1]
(hidden)     [Scores <1 not displayed]
```

**Debug view** (`?debugScore=1`):
```
raw 3.14 / ~3     ← Shows exact float and rounded value
raw 0.42 / ~0     ← Can see scores that would be hidden
raw 4.8 / ~5      ← Validate boosts are working
raw ? / ~?        ← See missing scores
```

---

## Why You Want This

### Problem: "Are my boosts working in production?"

**Before**: Need SSH, logs, manual ES queries, rebuild app
**After**: Just add `?debugScore=1` to URL ✓

### Test Right Now

```bash
# Local (dev server is running on :5176)
http://localhost:5176/search?q=Interview&debugScore=1

# Production (after deployment)
https://applylens.app/search?q=Interview&debugScore=1
```

You'll instantly see:
- ✅ "Interview" emails with `raw 3.2 / ~3` → boost working!
- ✅ "Offer" emails with `raw 4.5 / ~5` → boost working!
- ❌ Everything showing `raw 0.1 / ~0` → boosts not applied
- ❌ Everything showing `raw ? / ~?` → scoring broken

---

## Visual Indicators

**Header Badge** (yellow):
```
[debugScore ON] [ℹ Scoring]
```

**Score Display** (monospace):
```
raw 3.14 / ~3
```

---

## Safety

✅ Production-safe:
- Read-only (just displays existing data)
- No performance impact
- No backend changes
- Users must manually add URL param
- No sensitive data exposed

---

## Files Changed

1. **`apps/web/src/pages/Search.tsx`**
   - Extract `debugScore` from URL params
   - Conditional score rendering (debug vs normal)
   - Pass to SearchResultsHeader

2. **`apps/web/src/components/SearchResultsHeader.tsx`**
   - Add `debugScore` prop
   - Show yellow "debugScore ON" badge when enabled

---

## Test It Now

Your dev server is running on http://localhost:5176/

### Test Cases

```bash
# 1. Normal mode (no scores shown if <1)
http://localhost:5176/search?q=Interview

# 2. Debug mode (all scores shown)
http://localhost:5176/search?q=Interview&debugScore=1

# 3. Different queries
http://localhost:5176/search?q=Offer&debugScore=1
http://localhost:5176/search?q=Application&debugScore=1
```

### What to Look For

1. **Yellow badge** appears in header when debug enabled
2. **Score format** changes:
   - Normal: `score: 3`
   - Debug: `raw 3.14 / ~3`
3. **All results** show scores in debug mode (even if 0)
4. **No badge** and scores hidden when debug off

---

## Next Steps

### 1. Test Locally ✓

Open http://localhost:5176/search?debugScore=1 and verify:
- [x] Yellow badge shows
- [ ] Scores display in `raw X / ~Y` format
- [ ] All results show scores (even <1)
- [ ] Turning off param hides scores <1

### 2. Build & Deploy to Production

```bash
cd apps/web
npm version patch  # → v0.4.24

docker build -f apps/web/Dockerfile.prod -t leoklemet/applylens-web:v0.4.24 apps/web
docker push leoklemet/applylens-web:v0.4.24

# Update docker-compose.prod.yml to v0.4.24
docker-compose -f docker-compose.prod.yml up -d --force-recreate --no-deps web
```

### 3. Test on Production

```bash
https://applylens.app/search?q=Interview&debugScore=1
```

Validate boosts:
- Interview emails: `raw ~3.x`
- Offer emails: `raw ~4.x`
- Rejection emails: `raw ~0.5`

---

## Commits

1. **`1c26841`** - feat: add debugScore URL parameter to show raw score values
2. **`c6d5aea`** - docs: add debug score feature documentation

---

## Documentation

Full docs: `docs/debug-score-feature.md`

---

**Ready to test**: http://localhost:5176/search?debugScore=1 🚀
