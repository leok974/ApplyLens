# UI Polish - Quick Reference Card

## 🎨 Impact-Ordered Labels

### Visual Hierarchy
```
┌─────────────────────────────────────┐
│ Search Results for "interview"      │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ Google Software Engineer        │ │
│ │ recruiter@google.com            │ │
│ │                    [Offer] ←── Yellow, highest │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ Meta Interview Invitation       │ │
│ │ jobs@meta.com                   │ │
│ │                 [Interview] ←── Green, important │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ Amazon Application Received     │ │
│ │ noreply@amazon.com              │ │
│ │              [Application] ←── Blue, neutral │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ Thanks for Applying             │ │
│ │ hr@company.com                  │ │
│ │               [Rejection] ←── Gray, de-emphasized │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## 🔧 Recency Scale Selector (Settings)

```
┌──────────────────────────────────────┐
│ Settings                             │
├──────────────────────────────────────┤
│ Search Scoring                       │
│                                      │
│ Recency Scale:                       │
│ ┌──────────────────────────────────┐ │
│ │ ○ 3 days (more freshness)        │ │
│ │ ● 7 days (balanced) - Default    │ │ ← Selected
│ │ ○ 14 days (more recall)          │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Current Scoring Weights:             │
│ • Offer:      4.0× (highest)        │
│ • Interview:  3.0×                  │
│ • Others:     1.0×                  │
│ • Rejection:  0.5× (de-emphasized)  │
└──────────────────────────────────────┘
```

## 📊 Scoring Hint (Search Header)

```
┌────────────────────────────────────────────────────────────┐
│ Results (42) for "interview google"                        │
│ Scoring: offer^4 • interview^3 • rejection^0.5 •          │
│          Recency: 7-day decay (gauss scale=7d, decay=0.5) •│
│          Scale: 7d                                         │
└────────────────────────────────────────────────────────────┘
```

## 🎨 Label Color Palette

```css
Offer (Yellow - Highest Priority)
┌────────────────┐
│ bg-yellow-100  │  Soft yellow background
│ ring-yellow-300│  Darker yellow border
└────────────────┘

Interview (Green - Important)
┌────────────────┐
│ bg-green-100   │  Soft green background
│ ring-green-300 │  Darker green border
└────────────────┘

Others (Blue - Neutral)
┌────────────────┐
│ bg-blue-50     │  Very light blue background
│ ring-blue-200  │  Light blue border
└────────────────┘

Rejection (Gray - De-emphasized)
┌────────────────┐
│ bg-gray-100    │  Light gray background
│ ring-gray-300  │  Darker gray border
│ opacity-80     │  Slightly faded
└────────────────┘
```

## 🔌 API Integration

### Request with Scale
```http
GET /api/search/?q=interview&size=20&scale=3d
```

### Response Structure
```json
{
  "total": 42,
  "hits": [
    {
      "subject": "Google Interview Invitation",
      "from_addr": "recruiter@google.com",
      "label_heuristics": ["interview", "offer"],  ← Sorted by impact
      "score": 12.5,
      "received_at": "2025-10-09T10:00:00Z"
    }
  ]
}
```

## 🧪 Testing Checklist

### Visual Tests
- [ ] Labels appear in impact order (offer first, rejection last)
- [ ] Offer labels are yellow
- [ ] Interview labels are green
- [ ] Rejection labels are gray and faded
- [ ] Other labels are light blue
- [ ] Scoring hint displays at top of results
- [ ] Current scale shown in hint

### Functional Tests
- [ ] Settings dropdown changes recency scale
- [ ] Scale persists across page refreshes (localStorage)
- [ ] Search results reflect new scale
- [ ] Label sorting works with empty/null labels
- [ ] Multiple labels on same email sorted correctly

### API Tests
- [ ] `?scale=3d` parameter accepted
- [ ] `?scale=7d` parameter accepted (default)
- [ ] `?scale=14d` parameter accepted
- [ ] Invalid scale defaults to `7d`
- [ ] Recency decay applied correctly

## 📝 Component Usage

### EmailLabels Component
```tsx
import EmailLabels from '../components/EmailLabels'

// Basic usage
<EmailLabels labels={['interview', 'offer', 'rejection']} />

// With custom className
<EmailLabels 
  labels={email.label_heuristics} 
  className="flex gap-2 justify-end"
/>

// Handles null/undefined
<EmailLabels labels={email.labels || []} />
```

### SearchResultsHeader Component
```tsx
import SearchResultsHeader from '../components/SearchResultsHeader'

// With scoring hint
<SearchResultsHeader 
  query="interview google" 
  total={42} 
  showHint={true} 
/>

// Without hint
<SearchResultsHeader 
  query={searchQuery} 
  total={totalResults} 
/>
```

### Search Preferences
```typescript
import { getRecencyScale, setRecencyScale } from '../state/searchPrefs'

// Get current scale
const scale = getRecencyScale()  // "3d" | "7d" | "14d"

// Set new scale
setRecencyScale("3d")  // Saves to localStorage
```

## 🚀 Deployment Notes

### No Breaking Changes
- ✅ All changes are additive
- ✅ Backward compatible with existing code
- ✅ Default behavior unchanged (7d scale)
- ✅ Works without Settings page

### Feature Flags (Optional)
```typescript
// Disable scoring hint if needed
<SearchResultsHeader query={q} total={total} showHint={false} />

// Hide labels if needed
{showLabels && <EmailLabels labels={email.labels} />}
```

### Rollback Plan
1. Remove `scale` param from API calls → defaults to 7d
2. Replace `<EmailLabels>` with old badge rendering
3. Remove `<SearchResultsHeader>` → use plain text

---

**Files to Deploy**:
- Frontend: 4 new + 4 updated
- Backend: 1 updated (search.py)

**Zero Downtime**: Yes, all changes backward compatible

**User Impact**: Improved visual hierarchy and search customization
