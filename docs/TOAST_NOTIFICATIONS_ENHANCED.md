# Toast Notifications Enhancement

## Summary

Enhanced the Tracker page with contextual toast notifications that provide visual feedback for all user actions.

## Changes Applied

### 1. Toast Variant System

Added support for multiple toast styles based on action context:

- **Success** (green) - Positive actions (offers, interviews, application created)
- **Error** (red) - Failed operations or rejections
- **Warning** (yellow) - On-hold or ghosted status
- **Info** (blue) - HR screen status
- **Default** (gray) - Applied status and other actions

### 2. Status-Specific Toast Messages

Each status change now triggers a contextual toast:

```typescript
const STATUS_TO_TOAST_VARIANT: Record<AppStatus, ToastVariant> = {
  applied: 'default',
  hr_screen: 'info',
  interview: 'success',  // 🎉
  offer: 'success',      // 🎉
  rejected: 'error',     // ❌
  on_hold: 'warning',    // ⚠️
  ghosted: 'warning',    // ⚠️
}
```text

### 3. Enhanced User Feedback

**Status Updates:**

- Shows: `"Status: [Status Label] — [Company Name]"`
- Example: `"Status: Interview — OpenAI"`
- Color matches the status transition type

**Application Creation:**

- Shows: `"[Company Name] added to tracker"`
- Always uses success variant (green)

**Delete Operations:**

- Shows: `"Deleted [Company Name]"`
- Uses default variant (gray)

**Error Handling:**

- Shows: `"Failed to update status"` or `"Failed to delete application"`
- Uses error variant (red)

### 4. Visual Improvements

**Toast Appearance:**

- Fixed position in top-right corner
- Auto-dismisses after 3 seconds
- Icon prefix based on variant:
  - ✓ for success
  - ✗ for error
  - ⚠ for warning
  - ℹ for info
  - • for default

**Color Schemes:**

- Success: `bg-green-600 text-white`
- Error: `bg-red-600 text-white`
- Warning: `bg-yellow-500 text-white`
- Info: `bg-blue-600 text-white`
- Default: `bg-gray-800 text-white`

## Code Changes

### File: `apps/web/src/pages/Tracker.tsx`

**Added Types:**

```typescript
type ToastVariant = 'default' | 'success' | 'warning' | 'error' | 'info'
```text

**Added Constants:**

```typescript
const STATUS_TO_TOAST_VARIANT: Record<AppStatus, ToastVariant>
const STATUS_LABELS: Record<AppStatus, string>
```text

**Enhanced State:**

```typescript
const [toast, setToast] = useState<{ message: string; variant: ToastVariant } | null>(null)
```text

**Added Helper:**

```typescript
const showToast = (message: string, variant: ToastVariant = 'default') => {
  setToast({ message, variant })
  setTimeout(() => setToast(null), 3000)
}
```text

**Updated Functions:**

- `handleStatusChange()` - Now shows contextual toast with company name
- `handleDelete()` - Shows deletion confirmation toast
- Toast render logic - Supports all 5 variants with icons

## Testing

Test the enhancement by:

1. **Creating an Application:**
   - Use CreateFromEmailButton component
   - Should see green success toast: `"[Company] added to tracker"`

2. **Changing Status:**
   - Change to "Interview" → Green success toast
   - Change to "Offer" → Green success toast
   - Change to "Rejected" → Red error toast
   - Change to "On Hold" → Yellow warning toast
   - Change to "HR Screen" → Blue info toast

3. **Deleting Application:**
   - Delete an application
   - Should see gray toast: `"Deleted [Company]"`

4. **Error Handling:**
   - Stop the API server
   - Try to update status
   - Should see red error toast

## Benefits

1. **Better UX** - Users get immediate visual feedback for all actions
2. **Contextual Information** - Toast messages include company names
3. **Status Awareness** - Color coding helps users understand status significance
4. **Non-Intrusive** - Auto-dismisses after 3 seconds
5. **Error Visibility** - Failed operations are clearly communicated

## Technical Notes

- Uses React state and setTimeout for auto-dismiss
- No external toast libraries required
- Fully typed with TypeScript
- Responsive design (fixed positioning)
- z-index: 50 ensures toasts appear above other content

## Compatibility

- ✅ React Router (current implementation)
- ✅ No breaking changes to existing functionality
- ✅ Works with existing CreateFromEmailButton component
- ✅ Compatible with all existing API endpoints

## Future Enhancements

Potential improvements:

- Toast queue (multiple toasts at once)
- Dismiss button (manual close)
- Action buttons in toasts (e.g., "Undo")
- Persist toast preferences
- Sound notifications (optional)
