# Sortable TTR - Quick Reference

## 🎯 Quick Start

### In the UI

1. Go to <http://localhost:5175/search>
2. Search for emails (e.g., "interview")
3. Open "Sort results" dropdown
4. Choose your sort option

### Sort Options

| Option | Description | Use Case |
|--------|-------------|----------|
| **Relevance** | ES score (label boosts + recency) | Default, find important recent emails |
| **Newest** | Most recent first | See latest emails |
| **Oldest** | Oldest first | Find old unreplied emails |
| **Fastest response** | Quickest TTR first | Analyze response patterns |
| **Slowest / no-reply** | No-reply → top, slowest → top | **Triage workflow** |

---

## 🔍 Common Workflows

### Find Emails Needing Replies

```
Filter: "Not replied"
Sort: "Slowest / no-reply first"
```

→ All unreplied emails, oldest first

### Analyze Response Times

```
Filter: "Replied"
Sort: "Fastest response"
```

→ See your quickest responses

### Recent Offers

```
Query: "offer"
Label: "offer"
Sort: "Newest"
```

→ Most recent offers at top

---

## 🧪 API Quick Tests

```bash
# Fastest responses
curl "http://localhost:8003/search?q=interview&replied=true&sort=ttr_asc&size=3"

# Slowest/no-reply
curl "http://localhost:8003/search?q=interview&sort=ttr_desc&size=3"

# Newest
curl "http://localhost:8003/search?q=offer&sort=received_desc&size=3"

# Oldest
curl "http://localhost:8003/search?q=application&sort=received_asc&size=3"
```

---

## ⚙️ API Parameters

```
GET /search?q={query}&sort={option}

sort options:
  - relevance (default)
  - received_desc
  - received_asc
  - ttr_asc
  - ttr_desc
```

---

## 🎯 Pro Tips

1. **Triage Mode**: Use "Slowest / no-reply first" to find emails needing attention
2. **Combine Filters**: Sort + reply filter + labels = powerful queries
3. **Auto-refresh**: Results update instantly when you change sort
4. **Score vs Sort**: Relevance shows scores, custom sorts don't (by design)

---

## 🔧 Technical Notes

- **TTR Calculation**: `(first_reply - received) / 3600000.0` hours
- **Script-based**: Computed at query time via Elasticsearch Painless script
- **Null handling**: No-reply emails pushed to bottom (asc) or top (desc)
- **Performance**: Fast for datasets < 10k emails

---

## 📁 Files Modified

- `services/api/app/routers/search.py` - Backend sort logic
- `apps/web/src/components/SortControl.tsx` - Sort dropdown (NEW)
- `apps/web/src/pages/Search.tsx` - UI integration
- `apps/web/src/lib/api.ts` - API client update

---

**Ready to use!** 🚀

For full documentation, see `SORTABLE_TTR_COMPLETE.md`
