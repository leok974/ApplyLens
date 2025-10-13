# InlineNote Feature - Quick Reference

## Component Usage

```tsx
import InlineNote from '../components/InlineNote'

<InlineNote
  value={application.notes || ''}
  updatedAt={application.updated_at}
  testId={`note-${application.id}`}
  snippets={[
    'Sent thank-you',
    'Follow-up scheduled',
    'Left voicemail',
    'Recruiter screen scheduled',
    'Sent take-home',
    'Referred by X',
    'Declined offer',
  ]}
  onSave={async (nextValue) => {
    await updateApplication(application.id, { notes: nextValue })
    showToast(`Note saved — ${application.company}`, 'success')
    await refetch()
  }}
/>
```

## User Workflow

1. **Click** note preview (shows "—" if empty)
2. **Type** your note OR **click snippet chip** for quick insertion
3. **Click away** to auto-save
4. **Or press** Cmd/Ctrl+Enter to save immediately

## Snippet Chips

**Default Snippets:** 7 common note phrases  
**Behavior:**

- Click chip to insert text
- Empty note: sets snippet as value
- Existing note: appends on new line
- Cursor moves to end after insertion

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Click preview** | Open editor |
| **Blur** (click away) | Auto-save |
| **Cmd/Ctrl+Enter** | Save & close |
| **Escape** | Cancel & revert |

## Props API

```typescript
interface InlineNoteProps {
  value: string                           // Current note content
  onSave: (nextValue: string) => Promise<void>  // Save handler
  updatedAt?: string                      // Last update timestamp
  maxPreviewChars?: number                // Preview truncation (default: 80)
  placeholder?: string                    // Empty state text
  testId?: string                         // E2E test ID prefix
  snippets?: string[]                     // Custom snippet chips (optional)
}
```

## Testing

**E2E Tests:**

- `apps/web/tests/e2e/tracker-notes.spec.ts`
- `apps/web/tests/e2e/tracker-note-snippets.spec.ts`

```bash
cd apps/web
npx playwright test tests/e2e/tracker-notes.spec.ts
npx playwright test tests/e2e/tracker-note-snippets.spec.ts
```

**Coverage:**

- ✅ Save on blur with toast
- ✅ Cmd+Enter save shortcut
- ✅ Escape cancel shortcut
- ✅ Snippet chip insertion
- ✅ Text persistence after reload

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `InlineNote.tsx` | 165 | ➕ Created (with snippets) |
| `Tracker.tsx` | ~50 | 🔄 Refactored + snippets |
| `tracker-notes.spec.ts` | 110 | ➕ Created |
| `tracker-note-snippets.spec.ts` | 75 | ➕ Created |
| `index.css` | +5 | ➕ Added hover utility |

## Status

✅ **Production Ready**

- No TypeScript errors
- E2E tests written (3 scenarios)
- Snippet chips operational
- API integrated
- Toast notifications working
- Backward compatible

## Related Docs

- Full guide: `INLINE_NOTE_FEATURE_COMPLETE.md`
- Toast system: `TOAST_NOTIFICATIONS_ENHANCED.md`
- UI polish: `TRACKER_UI_POLISH_COMPLETE.md`
