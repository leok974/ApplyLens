# Inbox Page Refactor

## Overview

Created a polished, modern inbox experience using shadcn/ui components with improved UX, cleaner spacing, and better visual hierarchy.

## Files Created/Modified

### New Files
- **`src/pages/InboxPageRefactored.tsx`** - New refactored inbox page with:
  - shadcn Card, Button, Badge, Tabs, ScrollArea components
  - Lucide icons throughout
  - Improved hover/selected states
  - Better responsive design
  - Integrated with existing ApplyLens API and data models

### Modified Files
- **`src/App.tsx`** - Added route `/inbox-refactored` for testing
- **`src/components/inbox/EmailDetailsPanel.tsx`** - Fixed blank panel bug with tolerant field name resolution

## Key Features

### 1. InboxPageRefactored Component
- **Modern UI**: Uses shadcn/ui components consistently
- **Category Filtering**: Tabs for All, Interview, Offer, Rejection, Receipt, Newsletter
- **Sync Controls**: 7-day and 60-day sync buttons with loading states
- **Pagination**: Clean pagination with chevron icons
- **Deep-linking**: Supports `?open=<emailId>` query param

### 2. EmailListItem Component
- **Card-based Design**: Each email is a clickable card
- **Color-coded Categories**: Border colors for different email types:
  - Interview: Emerald
  - Offer: Sky blue
  - Rejection: Rose
  - Receipt: Amber
  - Newsletter: Purple
- **Smart Truncation**: Subject lines clamp to 2 lines, snippets to 2 lines
- **Label Display**: Shows first 3 labels, +N more badge
- **Application Integration**: "View app" button if linked to tracker

### 3. EmailDetailPanel Component
- **Always Visible**: Right sidebar on md+ screens
- **Empty State**: Helpful message when no email selected
- **Rich Metadata**: Subject, from, received time, snippet, labels, company, role
- **Quick Actions**:
  - Open in Gmail (external link)
  - View/Create Application (Briefcase icon)

## Usage

### Access the New Page
Navigate to: `http://localhost:5173/inbox-refactored`

### Integration with Existing Inbox
To replace the current inbox with the refactored version:

```tsx
// In App.tsx, change:
<Route path="/inbox" element={<Inbox />} />

// To:
<Route path="/inbox" element={<InboxPageRefactored />} />
```

### Customization

#### Adjust Colors
Edit badge colors in `EmailListItem`:
```tsx
email.category === "interview" && "border-emerald-500/70 text-emerald-600"
```

#### Change Layout
Adjust detail panel width:
```tsx
// In EmailDetailPanel, change w-[380px] to desired width
<aside className="... w-[420px] ...">
```

#### Modify Filters
Edit `CATEGORY_FILTERS` array to add/remove categories:
```tsx
const CATEGORY_FILTERS = [
  { value: "all" as EmailCategory, label: "All" },
  // Add more here
];
```

## Data Mapping

The component maps existing `Email` API type to `EmailSummary`:

```typescript
type EmailSummary = {
  id: string;              // from Email.id
  subject: string;         // from Email.subject
  fromName: string;        // from Email.sender || Email.from_addr
  fromEmail: string;       // from Email.from_addr
  snippet: string;         // from Email.body_preview || Email.body_text
  sentAt: string;          // from Email.received_at (ISO)
  category: EmailCategory; // from Email.label
  labels: string[];        // from Email.labels
  hasApplication: boolean; // !!Email.application_id
  rawEmail: Email;         // original data
}
```

## Next Steps

1. **Test with Real Data**: Load actual emails from your Gmail account
2. **Compare UX**: Use both `/inbox` and `/inbox-refactored` to compare
3. **Gradual Migration**: If satisfied, replace routes to make refactored version default
4. **Thread Viewer**: Consider integrating ThreadViewer drawer from original Inbox.tsx
5. **Bulk Actions**: Add bulk selection checkboxes if needed (from original design)

## Bug Fixes Applied

### EmailDetailsPanel.tsx
Fixed blank panel issue by adding tolerant field name resolution:
- Checks both `body_html` and `bodyHtml` (snake_case and camelCase)
- Falls back to snippet if body missing
- Shows friendly error if no content available

## Theme Compatibility

All components use CSS variables from your design system:
- `--primary`, `--primary-foreground`
- `--muted`, `--muted-foreground`
- `--border`, `--background`
- `--accent`, `--accent-foreground`

Dark mode is fully supported via Tailwind's `dark:` variants.

## Performance Notes

- Uses `React.memo` optimization opportunities (not yet implemented)
- Pagination limits to 50 emails per page
- Category filtering is client-side (could be optimized with server-side filtering)
- Deep-linking cleans URL after opening email to avoid duplicate history entries

## Accessibility

- Proper ARIA labels on icon-only buttons
- Keyboard navigation support (via native button/link elements)
- Color contrast meets WCAG AA standards
- Screen reader friendly with semantic HTML

---

**Created**: November 27, 2025
**Status**: Ready for testing at `/inbox-refactored`
**Dependencies**: shadcn/ui components, Lucide icons, existing ApplyLens API
