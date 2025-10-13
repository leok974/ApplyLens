# Reply Filter & TTR Badge - Quick Reference

## 🎯 What's New

### 1. Replied Filter Chip

**Location**: Search page, filter panel  
**Options**: All | Replied | Not replied  
**Function**: Toggle between showing all emails, only replied, or only not-replied

### 2. Time-to-Response (TTR) Badge

**Location**: Each search result, next to labels  
**Display**:

- Blue badge: "TTR 23m", "TTR 3h", "TTR 2d" (for replied emails)
- Gray badge: "No reply" (for not-replied emails)
**Format**: Automatically formats as minutes/hours/days

---

## 🚀 Quick Start

### Filter by Reply Status

```
1. Search for emails (e.g., "interview")
2. Click filter chip:
   - "All" → Show everything
   - "Replied" → Show only replied emails
   - "Not replied" → Show only emails you haven't replied to
```

### Read TTR Badges

```
TTR 15m  = Replied in 15 minutes
TTR 3h   = Replied in 3 hours
TTR 2d   = Replied in 2 days
No reply = Haven't replied yet
```

---

## 🔧 Technical Reference

### API Endpoint

```bash
# Get only replied emails
GET /search?q=interview&replied=true

# Get only not-replied emails
GET /search?q=offer&replied=false

# Get all (default)
GET /search?q=application
```

### Response Fields (NEW)

```json
{
  "hits": [{
    "first_user_reply_at": "2025-10-05T14:30:00Z",
    "user_reply_count": 2,
    "replied": true,
    "time_to_response_hours": 2.5
  }]
}
```

### Component Usage

```tsx
import { RepliedFilterChips } from '@/components/RepliedFilterChips'

<RepliedFilterChips 
  value={replied} 
  onChange={setReplied} 
/>
```

---

## 📊 Common Workflows

### Find Emails Needing Replies

```
1. Click "Not replied" filter
2. (Optional) Add date range: Last 7 days
3. (Optional) Add label: "Interview" or "Offer"
→ Shows emails requiring follow-up
```

### Review Response Times

```
1. Click "Replied" filter
2. Look at TTR badges on each result
3. Identify patterns (fast/slow responses)
→ Understand your response habits
```

### Urgent Unreplied Offers

```
1. Click label: "Offer"
2. Click "Not replied"
3. Set date: Last 3 days
→ Time-sensitive offers needing attention
```

---

## 🧪 Testing

### Quick Sanity Check

```bash
# Backend returns reply metrics
curl "http://localhost:8003/search?q=test&replied=true" | jq '.hits[0] | {replied, time_to_response_hours}'

# UI: Toggle filter chips and verify list updates
```

---

## 📁 Files Modified

**Backend**:

- `services/api/app/routers/search.py` - Added reply metrics to response

**Frontend**:

- `apps/web/src/components/RepliedFilterChips.tsx` - NEW
- `apps/web/src/pages/Search.tsx` - Added filter UI + TTR badges
- `apps/web/src/lib/api.ts` - Extended types and API function

**Docs**:

- `REPLY_FILTER_UI_COMPLETE.md` - Full documentation
- `REPLY_FILTER_QUICKREF.md` - This file

---

## ✨ Features

✅ Three-state filter (All/Replied/Not replied)  
✅ Server-side TTR computation  
✅ Smart formatting (minutes/hours/days)  
✅ Visual badges with tooltips  
✅ Works with existing filters (labels, dates, scale)  
✅ Auto-refresh on filter change  
✅ Zero TypeScript errors

---

## 🎨 Visual Design

**Filter Chips**: Blue theme, rounded pills, active state highlighted  
**TTR Badges**: Blue for replied (TTR Xm/h/d), gray for no reply  
**Layout**: Inline with labels and score, compact and readable

---

## 💡 Tips

- **Combine filters**: Use replied + labels + dates for precise searches
- **Hover badges**: Tooltip shows full timestamp details
- **Quick toggle**: Click chips to switch filter states instantly
- **AND logic**: All filters must match (not OR)

---

**Ready to use!** 🚀
