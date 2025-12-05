# Sidepanel Wiring Documentation

## Overview

The sidepanel is now fully wired with:
- Auto-checked profile/learned suggestions
- Apply to page functionality
- Real-time metrics updates
- Scan progress indicator
- Animated tab transitions

## Message Protocol

The sidepanel communicates with `contentV2.js` using these message types:

### 1. **COMPANION_GET_STATE**

**Direction**: Sidepanel → Content Script
**Purpose**: Load initial state when sidepanel opens
**Response**:
```javascript
{
  jobBoard: "Greenhouse",
  fields: [...],
  metrics: {
    fieldCount: 12,
    mappedCount: 8,
    profileCount: 5,
    learningLevel: "Intermediate"
  }
}
```

### 2. **SCAN_AND_SUGGEST_V2**

**Direction**: Sidepanel → Content Script
**Purpose**: Trigger full scan + AI suggestions
**Button**: "Generate suggestions"
**Response**: Same as GET_STATE

**Behavior**:
- Shows scan progress indicator
- Updates status pill to "Scanning…" with animated dot
- Renders field rows after completion
- Auto-checks profile/learned fields

### 3. **COMPANION_APPLY_MAPPINGS**

**Direction**: Sidepanel → Content Script
**Purpose**: Apply checked fields to page
**Button**: "Apply to page"
**Payload**:
```javascript
{
  type: "COMPANION_APPLY_MAPPINGS",
  mappings: [
    {
      fieldId: "email-field",
      selector: "#email",
      canonicalType: "email",
      value: "user@example.com"
    }
  ]
}
```

**Behavior**:
- Only sends fields with checked checkboxes
- Button shows "✓ Applied" for 2 seconds after success
- Button is disabled when no fields are checked

### 4. **GEN_COVER_LETTER**

**Direction**: Sidepanel → Content Script
**Purpose**: Generate cover letter
**Button**: "Cover Letter"

### 5. **LOG_APPLICATION**

**Direction**: Sidepanel → Content Script
**Purpose**: Log application to backend
**Button**: "Log application"
**Payload**:
```javascript
{
  type: "LOG_APPLICATION",
  payload: {
    source: "companion_sidepanel"
  }
}
```

**Behavior**:
- Button shows "✓ Logged" for 2 seconds after success

## Auto-Check Logic

Fields are automatically checked if:
1. `field.source === "profile"` (emerald badge)
2. `field.source === "learned"` (cyan badge)
3. `field.suggestedValue` is not empty

AI suggestions (`source === "ai"`) are NOT auto-checked by default.

## Badge Color System

| Source | Badge Color | Badge Text | Auto-Checked |
|--------|-------------|------------|--------------|
| `profile` | Emerald | "From profile" | ✓ Yes |
| `learned` | Cyan | "Learned" | ✓ Yes |
| `ai` | Indigo | "AI suggestion" | ✗ No |

## Status Pill States

| State | Color | Dot Animation | Label |
|-------|-------|---------------|-------|
| `connected` | Emerald | Static glow | "Connected" |
| `scanning` | Cyan | Pulsing | "Scanning…" |
| `disconnected` | Gray | None | "Idle" |

## Tab Switching

Three tabs available:
- **Fields**: Shows field mapping table (default)
- **Profile**: Shows user profile data (future)
- **Activity**: Shows application history (future)

**Animation**: 150ms ease-out with opacity + translateY transitions

## Metrics Updates

Metrics are recalculated automatically after every scan:

```javascript
state.metrics = {
  jobBoard: "Greenhouse",      // Auto-detected from URL
  fieldCount: fields.length,   // Total fields detected
  mappedCount: fieldsWithSuggestions.length,
  profileCount: fieldsFromProfile.length,
  learningLevel: "Intermediate" // From backend
}
```

## Integration Points

### Content Script (contentV2.js)

You need to handle these messages:

```javascript
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "COMPANION_GET_STATE") {
    sendResponse({
      jobBoard: detectJobBoard(),
      fields: currentFields,
      metrics: calculateMetrics()
    });
    return true;
  }

  if (msg.type === "SCAN_AND_SUGGEST_V2") {
    scanAndSuggest().then(result => {
      sendResponse(result);
    });
    return true;
  }

  if (msg.type === "COMPANION_APPLY_MAPPINGS") {
    applyMappings(msg.mappings);
    sendResponse({ success: true });
    return true;
  }
});
```

### Field Data Structure

Each field should have:

```javascript
{
  id: "unique-field-id",
  label: "Email Address",
  canonicalType: "email",
  selector: "#email",
  currentValue: "",
  suggestedValue: "user@example.com",
  source: "profile" | "learned" | "ai"
}
```

## Development Tips

1. **Testing**: Use demo fields in `sidepanel.js` (commented out) to test UI without scan
2. **Logging**: All actions log to console with `[ApplyLens Sidepanel]` prefix
3. **Error Handling**: If content script doesn't respond, status pill shows "Idle"
4. **Apply Button**: Automatically disabled when no checkboxes are checked

## Next Steps

To complete the integration:

1. Implement `COMPANION_GET_STATE` handler in contentV2.js
2. Implement `COMPANION_APPLY_MAPPINGS` to actually fill fields
3. Update `SCAN_AND_SUGGEST_V2` to return the new response shape
4. Add profile loading logic for Profile tab
5. Add activity history for Activity tab
