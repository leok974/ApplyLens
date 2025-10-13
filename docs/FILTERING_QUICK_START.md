# Advanced Filtering - Quick Start Guide

## Overview

Interactive label and date filtering added to search interface.

## Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Search Box                                          [Search] │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Filter by label:                                             │
│ [Offer] [Interview] [Rejection]  Clear                       │
│                                                               │
│ Filter by date:                                              │
│ From: [___/___/___]  To: [___/___/___]  Clear dates          │
└─────────────────────────────────────────────────────────────┘

Results (showing X emails matching "query")
...
```

## Label Chips

### Visual States

**Inactive (clickable)**:

- Offer: Light yellow background (bg-yellow-100), yellow ring
- Interview: Light green background (bg-green-100), green ring  
- Rejection: Light gray background (bg-gray-100), gray ring

**Active (selected)**:

- Offer: Darker yellow (bg-yellow-200), yellow ring
- Interview: Darker green (bg-green-200), green ring
- Rejection: Darker gray (bg-gray-200), gray ring

### Interaction

1. Click any chip to toggle selection
2. Click again to deselect
3. Multiple chips can be active (OR logic)
4. "Clear" button appears when any label selected
5. Results update automatically on change

## Date Range Controls

### Visual Elements

```
From: [date picker input]  To: [date picker input]  Clear dates
```

### Interaction

1. Click "From" input → native date picker opens
2. Select date → auto-updates search
3. Same for "To" date
4. "Clear dates" button appears when any date selected
5. Can set from-only, to-only, or both dates

## Usage Examples

### Example 1: Find all offers from last month

1. Search for any text (e.g., "congratulations")
2. Click "Offer" chip (turns yellow-200)
3. Set From: 2025-10-01, To: 2025-10-31
4. Results show only offers from October

### Example 2: Find recent interviews + offers

1. Search for "interview" or "meeting"
2. Click "Offer" chip
3. Click "Interview" chip (both active)
4. Set From: 2025-11-01
5. Results show offers OR interviews from November onwards

### Example 3: Clear filters

1. Click "Clear" under labels → removes all label filters
2. Click "Clear dates" → removes date range
3. Or click active chips individually to deselect

## Filter Logic

### Combination Rules

- **Multiple labels**: OR logic (matches ANY selected label)
- **Date range**: Inclusive (gte/lte)
- **All filters together**: AND logic (must match ALL conditions)

### Examples

**Labels: [offer, interview] + Date: Oct 2025**

- Matches: Emails labeled "offer" OR "interview"
- AND received between Oct 1-31, 2025

**Labels: [offer] + Date: From Oct 1**

- Matches: Emails labeled "offer"
- AND received on or after Oct 1, 2025

**Date: To Oct 31 (no labels)**

- Matches: All emails received on or before Oct 31, 2025
- Any label (no label filtering)

## Smart Scoring Integration

### Scoring Still Active

Even with filters applied:

- ✅ Label boosts still apply (offer^4, interview^3, rejection^0.5)
- ✅ Recency decay still applies (Gaussian with selected scale)
- ✅ Field boosting still active (subject^3, sender^1.5)
- ✅ ATS synonym expansion still works

### Example

Search "interview" with Offer filter + 7-day scale:

1. Filters to emails labeled "offer"
2. Expands "interview" to include Lever, Greenhouse, etc.
3. Boosts offers 4x
4. Applies 7-day recency decay
5. Shows highest-scored offers first

## Settings Integration

### Recency Scale

The recency scale setting (3d/7d/14d) from Settings page:

- ✅ Still applies to filtered results
- ✅ Changes affect both filtered and unfiltered searches
- ✅ Visible in scoring hint: "3d recency boost" or "7d recency boost"

### Persistence

- **Recency scale**: Persists in localStorage
- **Filters**: Currently reset on page reload (could be enhanced with URL params)

## API Integration

### Request Format

```
GET /api/search?q=interview&labels=offer&labels=interview&date_from=2025-10-01&date_to=2025-10-31&scale=7d
```

### Parameters

- `q`: Search query (required)
- `labels`: Repeatable param for each selected label
- `date_from`: ISO date string (YYYY-MM-DD or full ISO 8601)
- `date_to`: ISO date string
- `scale`: Recency scale (3d/7d/14d)
- `size`: Result limit (default 25)

### Response

Standard SearchHit array with highlights, scores, labels, etc.

## Accessibility

### Keyboard Navigation

- Tab through chips and date inputs
- Enter/Space to toggle chips
- Native date picker keyboard shortcuts

### Visual Feedback

- Transition effects on chip state changes
- Clear visual distinction between active/inactive
- Section headers for screen readers
- Semantic button elements

## Mobile Considerations

### Responsive Design

- Flex layout wraps on narrow screens
- Native date picker adapts to mobile
- Touch targets sized appropriately
- Clear buttons easily tappable

## Tips & Tricks

1. **Quick offer search**: Click "Offer" chip without typing → shows all offers
2. **Date shortcuts**: Use keyboard to type dates (depends on browser)
3. **Clear all**: Use individual clear buttons or deselect chips
4. **Combine with autocomplete**: Type to get suggestions, then filter results
5. **Scale tuning**: Adjust recency scale in Settings for different result ordering

## Common Workflows

### Workflow 1: Track Offer Timeline

1. Click "Offer" chip only
2. Sort by date (implicit via recency scoring)
3. Review offer progression over time

### Workflow 2: Recent Interview Follow-ups

1. Click "Interview" chip
2. Set From date to 7 days ago
3. Find interviews needing follow-up

### Workflow 3: Compare Offers in Period

1. Search for company name
2. Click "Offer" chip
3. Set date range for decision period
4. Review all offers to compare

## Troubleshooting

### No results after filtering

- Check if label selection is too restrictive
- Try widening date range
- Verify emails actually have those labels
- Clear filters and search again

### Date picker not working

- Browser compatibility (modern browsers only)
- Try typing date in YYYY-MM-DD format
- Check console for errors

### Filters not updating results

- Ensure JavaScript is enabled
- Check browser console for API errors
- Verify backend is running (port 8003)

## Future Enhancements

Potential improvements not yet implemented:

- URL parameter persistence (shareable filtered links)
- Filter preset saving
- Combined company + label filtering UI
- Date range presets (Last 7 days, This month, etc.)
- Filter result count preview
- Bulk filter operations

---

**Ready to use!** The filtering system is live and integrated with all existing smart search features.
