# Toast Variants Visual Reference

## Overview

The Tracker page now supports 5 different toast notification variants, each with a distinct color scheme and icon to communicate the nature of the action.

---

## Variants

### 1. Success ✓

**Color:** Green (`bg-green-600 text-white`)  
**Icon:** ✓  
**Use Cases:**

- Application created successfully
- Status changed to "Interview"
- Status changed to "Offer"

**Example Messages:**

```
✓ OpenAI added to tracker
✓ Status: Interview — Anthropic
✓ Status: Offer — Google
```

---

### 2. Error ✗

**Color:** Red (`bg-red-600 text-white`)  
**Icon:** ✗  
**Use Cases:**

- Status changed to "Rejected"
- API request failed
- Delete operation failed

**Example Messages:**

```
✗ Status: Rejected — Meta
✗ Failed to update status
✗ Failed to delete application
```

---

### 3. Warning ⚠

**Color:** Yellow (`bg-yellow-500 text-white`)  
**Icon:** ⚠  
**Use Cases:**

- Status changed to "On Hold"
- Status changed to "Ghosted"

**Example Messages:**

```
⚠ Status: On Hold — Stripe
⚠ Status: Ghosted — Databricks
```

---

### 4. Info ℹ

**Color:** Blue (`bg-blue-600 text-white`)  
**Icon:** ℹ  
**Use Cases:**

- Status changed to "HR Screen"
- Informational updates

**Example Messages:**

```
ℹ Status: HR Screen — Tesla
ℹ Application updated
```

---

### 5. Default •

**Color:** Gray (`bg-gray-800 text-white`)  
**Icon:** •  
**Use Cases:**

- Status changed to "Applied"
- Application deleted
- Generic actions

**Example Messages:**

```
• Status: Applied — Amazon
• Deleted SpaceX
```

---

## Implementation Details

### Toast Structure

```tsx
{toast && (
  <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg ${variantClasses}`}>
    <div className="flex items-center">
      <span className="mr-2">{icon}</span>
      <span>{toast.message}</span>
    </div>
  </div>
)}
```

### Auto-Dismiss Behavior

- All toasts automatically dismiss after **3 seconds**
- Implemented using `setTimeout` in the `showToast()` helper
- Previous toast is replaced if a new one appears

### Status Mapping

```typescript
const STATUS_TO_TOAST_VARIANT: Record<AppStatus, ToastVariant> = {
  applied: 'default',      // Gray with •
  hr_screen: 'info',       // Blue with ℹ
  interview: 'success',    // Green with ✓
  offer: 'success',        // Green with ✓
  rejected: 'error',       // Red with ✗
  on_hold: 'warning',      // Yellow with ⚠
  ghosted: 'warning',      // Yellow with ⚠
}
```

---

## User Experience Flow

### Example 1: Successful Application Flow

1. User clicks "Create Application" → **Green success toast**: `"✓ Acme Corp added to tracker"`
2. User changes status to "HR Screen" → **Blue info toast**: `"ℹ Status: HR Screen — Acme Corp"`
3. User changes status to "Interview" → **Green success toast**: `"✓ Status: Interview — Acme Corp"`
4. User changes status to "Offer" → **Green success toast**: `"✓ Status: Offer — Acme Corp"`

### Example 2: Rejection Flow

1. User changes status to "Rejected" → **Red error toast**: `"✗ Status: Rejected — Acme Corp"`

### Example 3: Uncertainty Flow

1. User changes status to "On Hold" → **Yellow warning toast**: `"⚠ Status: On Hold — Acme Corp"`
2. Weeks pass with no response
3. User changes status to "Ghosted" → **Yellow warning toast**: `"⚠ Status: Ghosted — Acme Corp"`

---

## Accessibility Considerations

1. **Color Contrast:** All variants use high-contrast text on colored backgrounds
2. **Icons:** Visual icons supplement color coding for colorblind users
3. **Auto-Dismiss:** 3-second duration is long enough to read but short enough to not be intrusive
4. **Message Content:** Clear, concise text describes the action taken

---

## Testing Checklist

- [ ] Create new application → Green success toast appears
- [ ] Change status to each option → Correct color/icon appears
- [ ] Delete application → Gray toast appears
- [ ] Cause an error (disconnect API) → Red error toast appears
- [ ] Toast auto-dismisses after 3 seconds
- [ ] Multiple rapid actions → Latest toast replaces previous
- [ ] Toast appears in top-right corner above all content
- [ ] Toast is readable on both light and dark backgrounds

---

## Technical Notes

**Position:** `fixed top-4 right-4`  
**Z-Index:** `50` (above most content)  
**Animation:** `animate-fade-in` (CSS class, if defined)  
**Timing:** `setTimeout(..., 3000)` for auto-dismiss

**No External Dependencies:** Uses only Tailwind CSS and React state.
