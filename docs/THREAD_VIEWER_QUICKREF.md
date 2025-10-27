# ThreadViewer Quick Reference

## Usage in Any Page

### 1. Import the required dependencies
```typescript
import { ThreadViewer } from '../components/ThreadViewer';
import { useThreadViewer } from '../hooks/useThreadViewer';
```

### 2. Initialize the hook
```typescript
function MyPage() {
  const thread = useThreadViewer();

  // ... rest of component
}
```

### 3. Make your list items clickable
```typescript
// For email rows/cards:
<div onClick={() => thread.showThread(email.id)} className="cursor-pointer">
  {/* Your email card/row content */}
</div>
```

### 4. Add ThreadViewer at the end of your component
```typescript
return (
  <div>
    {/* Your page content */}

    {/* Thread Viewer */}
    <ThreadViewer
      emailId={thread.selectedId}
      isOpen={thread.isOpen}
      onClose={thread.closeThread}
    />
  </div>
);
```

## With Action Buttons

```typescript
<ThreadViewer
  emailId={thread.selectedId}
  isOpen={thread.isOpen}
  onClose={thread.closeThread}
  onArchive={(id) => handleArchive(id)}
  onMarkSafe={(id) => handleMarkSafe(id)}
  onQuarantine={(id) => handleQuarantine(id)}
/>
```

## Hook API

### `useThreadViewer()`

Returns an object with:

| Property | Type | Description |
|----------|------|-------------|
| `selectedId` | `string \| null` | Currently selected email ID |
| `isOpen` | `boolean` | Whether the drawer is open |
| `showThread(id: string)` | `function` | Opens drawer with specified email |
| `closeThread()` | `function` | Closes the drawer |
| `clearThread()` | `function` | Clears selected ID (for cleanup) |

## Component Props

### `ThreadViewer`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `emailId` | `string \| null` | ✅ | Email/message ID to display |
| `isOpen` | `boolean` | ✅ | Controls drawer visibility |
| `onClose` | `() => void` | ✅ | Called when drawer closes |
| `onArchive` | `(id: string) => void` | ❌ | Archive action handler |
| `onMarkSafe` | `(id: string) => void` | ❌ | Mark safe action handler |
| `onQuarantine` | `(id: string) => void` | ❌ | Quarantine action handler |

## API Function

### `fetchThreadDetail(messageId: string)`

```typescript
import { fetchThreadDetail } from '../lib/api';

// Fetches message detail from /api/actions/message/:id
const detail = await fetchThreadDetail('msg_123');

// Returns MessageDetail:
{
  message_id: string;
  subject: string;
  from_name?: string;
  from_email?: string;
  to_email?: string;
  received_at: string;
  category?: string;
  risk_score?: number;
  quarantined?: boolean;
  html_body?: string;
  text_body?: string;
}
```

## Styling Customization

The ThreadViewer uses Tailwind CSS with CSS variables for theming. To customize:

```css
/* Drawer width (desktop) */
.thread-viewer {
  @apply w-[480px]; /* Change to desired width */
}

/* Backdrop opacity */
.thread-viewer-backdrop {
  @apply bg-black/40; /* Adjust alpha value */
}

/* Animation duration */
.thread-viewer {
  @apply duration-300; /* Change to 200, 500, etc. */
}
```

## Keyboard Shortcuts

- **Escape**: Close drawer (built-in)
- **Enter/Space**: Open thread (when focus on list item in Search page)

## Examples

### Minimal Example (Inbox-style)
```typescript
function SimpleInbox() {
  const thread = useThreadViewer();
  const [emails, setEmails] = useState([]);

  return (
    <div>
      {emails.map(email => (
        <div
          key={email.id}
          onClick={() => thread.showThread(String(email.id))}
          className="cursor-pointer p-4 hover:bg-muted"
        >
          <h3>{email.subject}</h3>
          <p>{email.from}</p>
        </div>
      ))}

      <ThreadViewer
        emailId={thread.selectedId}
        isOpen={thread.isOpen}
        onClose={thread.closeThread}
      />
    </div>
  );
}
```

### With Actions (Actions page-style)
```typescript
function ActionableInbox() {
  const thread = useThreadViewer();
  const [rows, setRows] = useState([]);

  const handleArchive = async (id: string) => {
    await postArchive(id);
    setRows(prev => prev.filter(r => r.id !== id));
    thread.closeThread();
  };

  return (
    <div>
      {rows.map(row => (
        <div
          key={row.id}
          onClick={() => thread.showThread(row.id)}
          className={cn(
            'cursor-pointer',
            thread.selectedId === row.id && 'bg-muted/30'
          )}
        >
          {/* Row content */}
        </div>
      ))}

      <ThreadViewer
        emailId={thread.selectedId}
        isOpen={thread.isOpen}
        onClose={thread.closeThread}
        onArchive={handleArchive}
        onMarkSafe={(id) => handleMarkSafe(id)}
        onQuarantine={(id) => handleQuarantine(id)}
      />
    </div>
  );
}
```

## Troubleshooting

### Drawer not opening?
- Check that `emailId` is not null
- Verify `isOpen` is true
- Console log `thread.selectedId` to debug

### Action buttons not showing?
- Pass handler functions as props (`onArchive`, etc.)
- Handlers are optional - only provided ones will show

### Email ID type mismatch?
- Convert to string if needed: `String(email.id)`
- API expects string IDs

### Styling conflicts?
- ThreadViewer uses `z-50` for drawer, `z-40` for backdrop
- Adjust if conflicts with modals/tooltips

## Backend Requirements

ThreadViewer expects this endpoint:

**GET `/api/actions/message/:id`**

Returns:
```json
{
  "message_id": "string",
  "subject": "string",
  "from_name": "string",
  "from_email": "string",
  "to_email": "string",
  "received_at": "ISO8601 date",
  "category": "string (optional)",
  "risk_score": "number (optional)",
  "quarantined": "boolean (optional)",
  "html_body": "string (optional)",
  "text_body": "string (optional)"
}
```

If your backend uses different field names, update the `MessageDetail` type in `api.ts`.
