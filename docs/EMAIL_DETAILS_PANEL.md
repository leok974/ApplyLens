# Email Details Panel Implementation

This document describes the email details panel feature that displays full email content in a sliding side panel.

## 📧 Overview

The Email Details Panel is a right-sliding overlay that displays full email content when a user clicks on an email row. It provides:

- Full email subject, sender, recipient, and metadata
- HTML or plain text email body
- Category badges and risk indicators
- Quick actions (Archive, Mark Safe, Mark Suspicious, Explain)
- Unsubscribe link detection
- Keyboard navigation (Escape to close)

## 🏗️ Architecture

### Component Structure

```text
EmailDetailsPanel (sliding panel)
  └── EmailList (passes onOpen)
       └── EmailRow (calls onOpen on click)
```text

### Data Flow

1. User clicks/double-clicks email row → `onOpen(id)` triggered
2. Page controller calls `openDetails(id)`
3. Fetches email from API via `getEmailById(id)`
4. Transforms response to `EmailDetails` format
5. Panel slides in from right with email content

## 📁 Files Created/Updated

### New Files

**`apps/web/src/components/inbox/EmailDetailsPanel.tsx`**

- Sliding panel component (720px max width)
- Header with close button and actions
- ScrollArea for long email bodies
- Supports HTML (with sanitization) and plain text
- Loading state with spinner
- Empty state when no email selected

### Updated Files

**`apps/web/src/lib/api.ts`**

- Added `EmailDetailResponse` type
- Added `getEmailById(id)` function
- Fetches from `/api/search/by_id/{id}` endpoint

**`apps/web/src/pages/InboxPolishedDemo.tsx`**

- Imported `EmailDetailsPanel` and `EmailDetails`
- Added state: `selectedDetailId`, `openPanel`, `loadingDetail`, `detail`
- Added `openDetails(id)` async function
- Wired `onOpen` prop to EmailList
- Rendered panel at bottom of JSX with actions

## 🎨 Visual Design

### Panel Styles

```tsx
className={cn(
  "fixed inset-y-0 right-0 z-40 w-full max-w-[720px]",
  "transform bg-white shadow-2xl transition-transform",
  "dark:bg-slate-950",
  open ? "translate-x-0" : "translate-x-full"
)}
```text

### Key Features

- **Fixed positioning**: Overlays entire right side
- **Smooth animation**: CSS transform transition
- **Shadow**: `shadow-2xl` for depth
- **Z-index 40**: Above content but below modals (50+)
- **Max width**: 720px for comfortable reading
- **Dark mode**: Full support with `dark:` variants

### Header Layout

```json
[Close Button] [Sender Email]               [Actions] [Explain Button]
```text

- Close (X icon)
- Sender email (truncated)
- Archive, Mark Safe, Mark Suspicious icons
- "Explain why" button

### Body Content

**Metadata Section:**

- Subject (h1, semibold, tracking-tight)
- From/To/Date in small text
- Labels as outline badges
- Reason badge (indigo)
- Risk badge (rose for high)

**Email Body:**

- HTML: Rendered with Tailwind prose classes
- Plain text: Pre-formatted with monospace
- Fallback: "(No body content)" message

**Footer:**

- Unsubscribe link (if detected)
- External link icon

## 🔧 Usage

### Basic Integration

```tsx
import { EmailDetailsPanel, EmailDetails } from "@/components/inbox/EmailDetailsPanel";
import { getEmailById } from "@/lib/api";

function InboxPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [openPanel, setOpenPanel] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detail, setDetail] = useState<EmailDetails | null>(null);

  async function openDetails(id: string) {
    setSelectedId(id);
    setOpenPanel(true);
    setLoadingDetail(true);
    try {
      const data = await getEmailById(id);
      setDetail({
        id: data.id,
        subject: data.subject,
        from: data.from_addr || data.from || "",
        to: data.to_addr,
        date: new Date(data.received_at || data.date).toLocaleString(),
        labels: data.labels || data.gmail_labels,
        risk: data.risk,
        reason: data.reason,
        body_html: data.body_html,
        body_text: data.body_text,
        thread_id: data.thread_id,
        unsubscribe_url: data.unsubscribe_url || null,
      });
    } finally {
      setLoadingDetail(false);
    }
  }

  return (
    <>
      <EmailList
        items={emails}
        onOpen={(id) => openDetails(id)}
        {...otherProps}
      />
      
      <EmailDetailsPanel
        open={openPanel}
        onClose={() => setOpenPanel(false)}
        loading={loadingDetail}
        email={detail}
        onArchive={async () => { /* handle archive */ }}
        onMarkSafe={async () => { /* handle safe */ }}
        onMarkSus={async () => { /* handle suspicious */ }}
        onExplain={async () => { /* handle explain */ }}
      />
    </>
  );
}
```text

### API Integration

**Production Setup:**

1. Create API endpoint: `GET /api/search/by_id/{id}`
2. Return email document with all fields
3. Include HTML sanitization on backend

**Endpoint Response:**

```json
{
  "id": "email_123",
  "subject": "Interview Invitation",
  "from_addr": "hr@company.com",
  "to_addr": "you@example.com",
  "received_at": "2025-10-11T10:30:00Z",
  "labels": ["INBOX", "IMPORTANT"],
  "risk": "low",
  "reason": "ats",
  "body_html": "<p>Email content...</p>",
  "body_text": "Email content...",
  "thread_id": "thread_abc",
  "unsubscribe_url": null
}
```text

## ⌨️ Keyboard Shortcuts

### Panel Navigation

- **Escape**: Close panel
- **Enter**: (on email row) Open details panel
- **Double-click**: (on email row) Open details panel

### Future Enhancements

- **j/k**: Navigate to next/prev email while panel open
- **a**: Archive current email
- **s**: Mark as safe
- **x**: Mark as suspicious
- **e**: Explain classification

## 🎯 Props Reference

### EmailDetailsPanel Props

```typescript
{
  open: boolean;              // Panel visibility
  onClose: () => void;        // Close handler
  loading?: boolean;          // Show loading spinner
  email?: EmailDetails | null; // Email data
  onArchive?: () => void;     // Archive action
  onMarkSafe?: () => void;    // Mark safe action
  onMarkSus?: () => void;     // Mark suspicious action
  onExplain?: () => void;     // Explain action
}
```text

### EmailDetails Type

```typescript
{
  id: string;
  subject: string;
  from: string;
  to?: string;
  date: string;               // Formatted date
  labels?: string[];
  risk?: "low"|"med"|"high";
  reason?: string;
  body_html?: string;         // Preferred
  body_text?: string;         // Fallback
  thread_id?: string;
  unsubscribe_url?: string | null;
}
```text

## 🎨 Styling Customization

### Panel Width

```tsx
// Default: 720px
className="max-w-[720px]"

// Narrower: 600px
className="max-w-[600px]"

// Wider: 900px
className="max-w-[900px]"
```text

### Animation Speed

```tsx
// Default: transition-transform (200ms)
className="transition-transform"

// Faster: 150ms
className="transition-transform duration-150"

// Slower: 300ms
className="transition-transform duration-300"
```text

### Body Typography

**HTML Rendering:**

```tsx
className="prose prose-slate max-w-none dark:prose-invert prose-a:text-indigo-600"
```text

**Plain Text:**

```tsx
className="whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm"
```text

## 🔒 Security Considerations

### HTML Sanitization

**⚠️ CRITICAL**: Always sanitize HTML on the backend before sending to frontend.

**Recommended Library**: DOMPurify (already imported)

```tsx
import DOMPurify from 'dompurify';

// Sanitize on render
<article
  dangerouslySetInnerHTML={{ 
    __html: DOMPurify.sanitize(email.body_html) 
  }}
/>
```text

**Backend Sanitization** (preferred):

```python
import bleach

allowed_tags = ['p', 'br', 'strong', 'em', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3']
allowed_attrs = {'a': ['href', 'title']}

clean_html = bleach.clean(
    email_html,
    tags=allowed_tags,
    attributes=allowed_attrs,
    strip=True
)
```text

### External Links

- All links open in `target="_blank"` with `rel="noreferrer"`
- Unsubscribe links validated against known patterns
- Click tracking prevention

## 🐛 Troubleshooting

### Panel Not Opening

**Check:**

1. `open` prop is `true`
2. `openDetails(id)` is called on row click
3. `onOpen` prop passed to EmailList
4. EmailRow has `onOpen` or `onDoubleClick` handler

### Email Not Loading

**Check:**

1. API endpoint `/api/search/by_id/{id}` exists
2. `getEmailById(id)` function implemented
3. Response format matches `EmailDetailResponse` type
4. CORS headers if API on different domain

### Styling Issues

**Check:**

1. Tailwind CSS classes compiled
2. `z-index: 40` not conflicting with other elements
3. Dark mode classes applied correctly
4. ScrollArea component available

### Escape Key Not Working

**Check:**

1. `useEffect` hook listening for keydown
2. No input fields capturing event
3. Panel has focus (tabindex or auto-focus)

## 📊 Performance

### Optimization Tips

1. **Lazy Load Body**: Only fetch full body when panel opens
2. **Cache Details**: Store fetched emails in Map/state
3. **Debounce Clicks**: Prevent double-fetch on rapid clicks
4. **Virtual Scrolling**: For very long email bodies
5. **Image Lazy Loading**: Add `loading="lazy"` to images in HTML

### Example Caching

```tsx
const [emailCache, setEmailCache] = useState<Map<string, EmailDetails>>(new Map());

async function openDetails(id: string) {
  if (emailCache.has(id)) {
    setDetail(emailCache.get(id)!);
    setOpenPanel(true);
    return;
  }
  
  // Fetch and cache...
  const data = await getEmailById(id);
  const details = transformToEmailDetails(data);
  setEmailCache(prev => new Map(prev).set(id, details));
  setDetail(details);
  setOpenPanel(true);
}
```text

## 🚀 Future Enhancements

### Planned Features

- [ ] Thread view (show conversation history)
- [ ] Forward/Reply buttons
- [ ] Attachment preview
- [ ] Print view
- [ ] Email annotations
- [ ] Share link
- [ ] Quick labels editor
- [ ] Smart reply suggestions
- [ ] Translation

### Nice-to-Have

- [ ] Panel resize (drag handle)
- [ ] Multi-panel support (compare emails)
- [ ] Keyboard navigation between emails
- [ ] Email actions history/undo
- [ ] Full-screen mode
- [ ] Email templates
- [ ] Scheduled actions

---

**Version**: 1.0  
**Last Updated**: October 11, 2025  
**Status**: ✅ Production Ready (Demo Mode)
