# Companion Extension Protocol

## Overview

The ApplyLens Companion is a **Manifest V3** Chrome extension that communicates with the backend API to provide AI-powered autofill for job application forms. It uses a message-passing protocol between content scripts, the service worker, and the backend.

## Manifest V3 Architecture

### Key Components

```
┌─────────────────────────────────────────────────────┐
│                   Extension                         │
│                                                     │
│  ┌──────────────┐         ┌──────────────┐        │
│  │ Service      │◄───────►│   Content    │        │
│  │ Worker       │  msgs   │   Script     │        │
│  │ (sw.js)      │         │ (content.js) │        │
│  └──────┬───────┘         └──────┬───────┘        │
│         │                        │                 │
│         │ chrome.runtime         │ DOM access      │
│         │ .sendMessage           │ form detection  │
│         │                        │                 │
│  ┌──────▼───────┐         ┌──────▼───────┐        │
│  │   Popup      │         │  Side Panel  │        │
│  │ (popup.js)   │         │(sidepanel.js)│        │
│  └──────────────┘         └──────────────┘        │
│                                                     │
└─────────────────────────────────────────────────────┘
         │
         │ fetch() to backend API
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              Backend API                             │
│         (api.applylens.app)                         │
│                                                      │
│  /api/profile/me                                    │
│  /api/extension/generate-form-answers              │
│  /api/extension/applications                       │
│  /api/extension/learning/profile                   │
│  /api/extension/learning/sync                      │
└─────────────────────────────────────────────────────┘
```

### Component Roles

#### Service Worker (`sw.js`)

**Purpose**: Background script for API calls and history management

**Capabilities**:
- Makes fetch requests to backend API
- Stores application history in `chrome.storage.local`
- Receives messages from popup and content scripts
- Cannot access DOM

**Lifecycle**: Persistent background process (kept alive by event listeners)

#### Content Script (`content.js`)

**Purpose**: Interacts with web pages, detects forms, fills fields

**Capabilities**:
- Scans page DOM for job application forms
- Extracts field information (labels, IDs, types)
- Fills form fields with AI-generated answers
- Sends learning events when user edits answers
- Cannot make direct API calls (CORS restrictions)

**Lifecycle**: Injected into every page matching `<all_urls>`

**Injection**:
```json
// manifest.json
"content_scripts": [{
  "matches": ["<all_urls>"],
  "js": ["content.js"],
  "run_at": "document_idle"
}]
```

#### Popup (`popup.js`)

**Purpose**: Extension icon popup UI

**Features**:
- Shows connection status (checks `/api/profile/me`)
- Displays autofill history (last 10 applications)
- Provides manual controls (scan form, generate DM)
- Learning preferences toggle

#### Side Panel (`sidepanel.js`)

**Purpose**: Optional side panel view (Chrome 114+)

**Features**:
- Alternative UI to popup
- Shows connection status
- Future: Enhanced form preview

## Message Protocol

### Message Types

All messages follow this structure:

```typescript
interface ExtensionMessage {
  type: string;           // Message type identifier
  payload?: any;          // Optional data
}

interface MessageResponse {
  ok: boolean;            // Success/failure
  data?: any;            // Response data
  error?: string;        // Error message
}
```

### 1. GET_PROFILE

**Direction**: Popup → Service Worker → Backend
**Endpoint**: `GET /api/profile/me`

**Purpose**: Check if user is authenticated

**Request**:
```javascript
chrome.runtime.sendMessage({ type: "GET_PROFILE" }, (response) => {
  if (response.ok) {
    console.log("User:", response.data);
  } else {
    console.log("Not authenticated");
  }
});
```

**Response**:
```javascript
{
  ok: true,
  data: {
    id: "user-123",
    email: "user@example.com",
    name: "John Doe"
  }
}
```

**Backend Response**:
```json
{
  "id": "user-123",
  "email": "user@example.com",
  "name": "John Doe"
}
```

### 2. GEN_FORM_ANSWERS

**Direction**: Content Script → Service Worker → Backend
**Endpoint**: `POST /api/extension/generate-form-answers`

**Purpose**: Generate AI answers for form fields

**Request**:
```javascript
chrome.runtime.sendMessage({
  type: "GEN_FORM_ANSWERS",
  payload: {
    job: {
      title: "Senior AI Engineer",
      company: "AcmeCo",
      url: "https://jobs.acme.co/123"
    },
    fields: [
      {
        field_id: "cover_letter",
        label: "Why do you want to work here?",
        type: "textarea",
        max_length: 5000
      },
      {
        field_id: "years_experience",
        label: "Years of experience",
        type: "number"
      }
    ],
    context: {
      ats_family: "greenhouse",
      segment_key: "greenhouse|engineering|senior",
      url: window.location.href
    }
  }
}, (response) => {
  if (response.ok) {
    fillForm(response.data.answers);
  }
});
```

**Backend Request**:
```json
{
  "job": {
    "title": "Senior AI Engineer",
    "company": "AcmeCo",
    "url": "https://jobs.acme.co/123"
  },
  "fields": [
    {
      "field_id": "cover_letter",
      "label": "Why do you want to work here?",
      "type": "textarea",
      "max_length": 5000
    }
  ],
  "context": {
    "ats_family": "greenhouse",
    "segment_key": "greenhouse|engineering|senior"
  }
}
```

**Response**:
```javascript
{
  ok: true,
  data: {
    job: {
      title: "Senior AI Engineer",
      company: "AcmeCo"
    },
    answers: [
      {
        field_id: "cover_letter",
        answer: "I'm excited about AcmeCo's mission to...",
        confidence: 0.92
      },
      {
        field_id: "years_experience",
        answer: "7"
      }
    ],
    metadata: {
      style_id: "concise_bullets_v2",
      policy: "exploit",
      segment_key: "greenhouse|engineering|senior"
    }
  }
}
```

### 3. LOG_APPLICATION

**Direction**: Content Script → Service Worker → Backend
**Endpoint**: `POST /api/extension/applications`

**Purpose**: Log a submitted job application

**Request**:
```javascript
chrome.runtime.sendMessage({
  type: "LOG_APPLICATION",
  payload: {
    company: "AcmeCo",
    role: "Senior AI Engineer",
    source: "browser_extension",
    url: "https://jobs.acme.co/123",
    status: "applied",
    metadata: {
      ats_family: "greenhouse",
      submitted_at: new Date().toISOString()
    }
  }
});
```

**Backend Request**:
```json
{
  "company": "AcmeCo",
  "role": "Senior AI Engineer",
  "source": "browser_extension",
  "url": "https://jobs.acme.co/123",
  "status": "applied",
  "metadata": {
    "ats_family": "greenhouse"
  }
}
```

**Response**:
```javascript
{
  ok: true
}
```

### 4. GEN_DM

**Direction**: Popup → Service Worker → Backend
**Endpoint**: `POST /api/extension/generate-recruiter-dm`

**Purpose**: Generate LinkedIn DM to recruiter

**Request**:
```javascript
chrome.runtime.sendMessage({
  type: "GEN_DM",
  payload: {
    profile: {
      name: "Jane Recruiter",
      headline: "Senior Technical Recruiter @ AcmeCo",
      company: "AcmeCo",
      profile_url: "https://linkedin.com/in/jane-recruiter"
    },
    job: {
      title: "Senior AI Engineer",
      url: "https://jobs.acme.co/123"
    }
  }
}, (response) => {
  if (response.ok) {
    navigator.clipboard.writeText(response.data.message);
  }
});
```

**Response**:
```javascript
{
  ok: true,
  data: {
    message: "Hi Jane,\n\nI came across the Senior AI Engineer role...",
    style: "professional",
    word_count: 87
  }
}
```

### 5. LOG_OUTREACH

**Direction**: Popup → Service Worker → Backend
**Endpoint**: `POST /api/extension/outreach`

**Purpose**: Log a recruiter outreach

**Request**:
```javascript
chrome.runtime.sendMessage({
  type: "LOG_OUTREACH",
  payload: {
    recruiter_name: "Jane Recruiter",
    company: "AcmeCo",
    role: "Senior AI Engineer",
    platform: "linkedin",
    message_preview: "Hi Jane, I came across...",
    metadata: {
      profile_url: "https://linkedin.com/in/jane-recruiter"
    }
  }
});
```

**Response**:
```javascript
{
  ok: true
}
```

### 6. SCAN_AND_SUGGEST

**Direction**: Popup → Service Worker → Content Script
**Endpoint**: None (internal message)

**Purpose**: Trigger content script to scan page for forms

**Request** (from popup):
```javascript
chrome.runtime.sendMessage({ type: "SCAN_AND_SUGGEST" });
```

**Service Worker** forwards to active tab:
```javascript
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  chrome.tabs.sendMessage(tabs[0].id, { type: "SCAN_AND_SUGGEST" });
});
```

**Content Script** receives and scans:
```javascript
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "SCAN_AND_SUGGEST") {
    const fields = scanFormFields();
    showAutofillPanel(fields);
    sendResponse({ ok: true, fieldCount: fields.length });
  }
});
```

### 7. GET_HISTORY

**Direction**: Popup → Service Worker
**Storage**: `chrome.storage.local`

**Purpose**: Retrieve autofill/outreach history

**Request**:
```javascript
chrome.runtime.sendMessage({
  type: "GET_HISTORY",
  payload: { kind: "applications" }  // or "outreach"
}, (response) => {
  renderHistory(response.data);
});
```

**Response**:
```javascript
{
  ok: true,
  data: [
    {
      company: "AcmeCo",
      role: "Senior AI Engineer",
      timestamp: "2025-11-17T10:30:00Z",
      url: "https://jobs.acme.co/123"
    },
    // ... up to 50 entries
  ]
}
```

### 8. LEARNING_SYNC

**Direction**: Content Script → Service Worker → Backend
**Endpoint**: `POST /api/extension/learning/sync`

**Purpose**: Send learning events when user edits AI-generated answers

**Request**:
```javascript
chrome.runtime.sendMessage({
  type: "LEARNING_SYNC",
  payload: {
    host: "boards.greenhouse.io",
    schema_hash: "md5_of_field_structure",
    events: [
      {
        field_id: "cover_letter",
        generated_value: "I'm excited about AcmeCo's mission...",
        user_value: "I'm excited about your mission... [edited]",
        style_id: "concise_bullets_v2",
        edit_stats: {
          edit_distance: 45,
          avg_edit_chars: 120
        },
        metadata: {
          ats_family: "greenhouse",
          segment_key: "greenhouse|engineering|senior"
        }
      }
    ]
  }
});
```

**Backend Response**:
```json
{
  "status": "accepted",
  "events_processed": 1
}
```

### 9. LEARNING_PROFILE

**Direction**: Content Script → Service Worker → Backend
**Endpoint**: `GET /api/extension/learning/profile?host=...&schema_hash=...`

**Purpose**: Fetch learned field mappings for a form

**Request**:
```javascript
chrome.runtime.sendMessage({
  type: "LEARNING_PROFILE",
  payload: {
    host: "boards.greenhouse.io",
    schema_hash: "abc123def456"
  }
}, (response) => {
  if (response.ok && response.data.canonical_map) {
    applyLearnedMappings(response.data.canonical_map);
  }
});
```

**Backend Request**:
```
GET /api/extension/learning/profile?host=boards.greenhouse.io&schema_hash=abc123
```

**Response**:
```javascript
{
  ok: true,
  data: {
    host: "boards.greenhouse.io",
    schema_hash: "abc123def456",
    canonical_map: {
      "#full_name": "full_name",
      "#email": "email",
      "#cover_letter": "cover_letter"
    },
    style_hint: {
      gen_style_id: "concise_bullets_v2",
      confidence: 0.95
    }
  }
}
```

## Backend Endpoints

### Authentication

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/profile/me` | GET | Required | Get current user profile |
| `/api/auth/google/login` | GET | None | Start OAuth flow |
| `/api/auth/google/callback` | GET | None | OAuth callback |

### Extension Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/extension/generate-form-answers` | POST | Optional | Generate AI answers for form |
| `/api/extension/applications` | POST | Optional | Log job application |
| `/api/extension/outreach` | POST | Optional | Log recruiter outreach |
| `/api/extension/generate-recruiter-dm` | POST | Optional | Generate LinkedIn DM |
| `/api/extension/learning/sync` | POST | Optional | Send learning events |
| `/api/extension/learning/profile` | GET | Optional | Get learned field mappings |

**Note**: Extension endpoints use **CSRF-exempt** auth for browser extension context.

## Content Script Flow

### 1. Form Detection

```javascript
// Scan page for form elements
function scanFormFields() {
  const fields = [];

  // Find all input fields
  document.querySelectorAll('input, textarea, select').forEach(el => {
    const fieldInfo = {
      field_id: el.id || el.name || generateId(el),
      label: findLabel(el),
      type: el.type,
      element: el
    };

    // Skip hidden/irrelevant fields
    if (!isRelevantField(fieldInfo)) return;

    fields.push(fieldInfo);
  });

  return fields;
}
```

### 2. Context Extraction

```javascript
// Extract ATS family from URL
function detectATSFamily(url) {
  const hostname = new URL(url).hostname;

  if (hostname.includes('greenhouse.io')) return 'greenhouse';
  if (hostname.includes('lever.co')) return 'lever';
  if (hostname.includes('myworkdayjobs.com')) return 'workday';
  if (hostname.includes('taleo.net')) return 'taleo';

  return 'generic';
}

// Extract job info from page
function extractJobInfo() {
  // Look for common selectors
  const titleSelectors = [
    '.job-title',
    '[data-job-title]',
    'h1',
    '.posting-headline'
  ];

  const companySelectors = [
    '.company-name',
    '[data-company]',
    '.employer-name'
  ];

  return {
    title: findFirst(titleSelectors)?.textContent,
    company: findFirst(companySelectors)?.textContent,
    url: window.location.href
  };
}
```

### 3. Autofill Execution

```javascript
async function autofillForm(answers) {
  for (const answer of answers) {
    const field = document.getElementById(answer.field_id);
    if (!field) continue;

    // Store original value for learning
    const originalValue = field.value;

    // Fill field
    field.value = answer.answer;
    field.dispatchEvent(new Event('input', { bubbles: true }));
    field.dispatchEvent(new Event('change', { bubbles: true }));

    // Track for learning
    trackFieldFill(field, {
      field_id: answer.field_id,
      generated_value: answer.answer,
      original_value: originalValue
    });
  }
}
```

### 4. Learning Event Collection

```javascript
// Listen for user edits
function trackFieldFill(element, context) {
  let editTimeout;

  element.addEventListener('input', () => {
    clearTimeout(editTimeout);

    // Debounce: wait 2s after last edit
    editTimeout = setTimeout(() => {
      const userValue = element.value;
      const editStats = calculateEditStats(
        context.generated_value,
        userValue
      );

      // Send learning event
      sendLearningEvent({
        field_id: context.field_id,
        generated_value: context.generated_value,
        user_value: userValue,
        edit_stats: editStats
      });
    }, 2000);
  });
}

function calculateEditStats(generated, user) {
  return {
    edit_distance: levenshtein(generated, user),
    avg_edit_chars: Math.abs(user.length - generated.length)
  };
}
```

## Storage

### chrome.storage.local

Used for persistent history (survives browser restart):

**Schema**:
```javascript
{
  "history_applications": [
    {
      company: "AcmeCo",
      role: "Engineer",
      timestamp: "2025-11-17T10:30:00Z",
      url: "..."
    },
    // ... up to 50 entries
  ],
  "history_outreach": [
    // ... same structure
  ]
}
```

**API**:
```javascript
// Save
chrome.storage.local.set({ history_applications: items });

// Load
chrome.storage.local.get(['history_applications'], (result) => {
  const history = result.history_applications || [];
});
```

### chrome.storage.sync

Used for user preferences (syncs across devices):

**Schema**:
```javascript
{
  "learningEnabled": true,
  "autoScanForms": false,
  "preferredStyle": "concise_bullets_v2"
}
```

## CORS & Security

### Extension Context

Extensions run with special privileges:

```javascript
// Can make requests to any domain (no CORS)
fetch('https://api.applylens.app/api/profile/me', {
  credentials: 'include'  // Send cookies
});
```

### Content Script Context

Content scripts inherit page's origin:

```javascript
// ❌ CORS blocked (different origin)
fetch('https://api.applylens.app/...');

// ✅ Use message passing instead
chrome.runtime.sendMessage({ type: "GEN_FORM_ANSWERS", ... });
```

### Backend CORS

```python
# Backend allows extension origin
CORS_ALLOW_ORIGINS = [
    "https://applylens.app",
    "chrome-extension://*"  # All extension IDs
]
```

## Permissions

### Required Permissions

```json
// manifest.json
{
  "permissions": [
    "storage",           // chrome.storage API
    "activeTab",         // Access current tab
    "tabs",              // Query tabs
    "scripting"          // Inject scripts
  ],
  "host_permissions": [
    "<all_urls>"         // Access all websites
  ]
}
```

### Why <all_urls>?

Job boards exist on thousands of domains:
- greenhouse.io
- lever.co
- myworkdayjobs.com
- company-specific ATS systems

Extension needs broad permissions to work universally.

**Future**: Narrow to specific ATS domains for Chrome Web Store approval.

## Testing

### Unit Tests

Located in: `apps/extension-applylens/tests/`

```bash
cd apps/extension-applylens
npm test
```

**Test files**:
- `content.test.ts` - Form detection, field extraction
- `popup.test.ts` - Popup UI interactions
- `sw.test.ts` - Service worker message handling

### E2E Tests

Located in: `apps/extension-applylens/e2e/`

```bash
npx playwright test
```

**Key tests**:
- `with-extension.spec.ts` - Full autofill flow
- `learning-profile.spec.ts` - Learning events
- `autofill-bandit.spec.ts` - Bandit policy selection

### Manual Testing

```bash
# 1. Start dev server
cd apps/extension-applylens
npm run dev

# 2. Load extension in Chrome
chrome://extensions → Load unpacked → select folder

# 3. Navigate to demo form
http://localhost:5177/demo-form.html

# 4. Click extension icon → Scan form → Autofill
```

## Development

### Hot Reload

Extension doesn't support hot reload natively:

1. Make code changes
2. Go to `chrome://extensions`
3. Click reload button for ApplyLens Companion
4. Refresh page you're testing on

### Debug Logs

```javascript
// Service worker logs
chrome://extensions → ApplyLens Companion → Inspect service worker

// Content script logs
Right-click page → Inspect → Console

// Popup logs
Right-click extension icon → Inspect popup
```

### Mock Backend

For testing without backend:

```javascript
// In content.js, mock API responses
if (window.location.hostname === 'localhost') {
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'GEN_FORM_ANSWERS') {
      sendResponse({
        ok: true,
        data: {
          answers: [
            { field_id: 'cover_letter', answer: 'Mock answer' }
          ]
        }
      });
      return true;  // Keep channel open
    }
  });
}
```

## Future Enhancements

### Phase 7: Offline Support
- Cache generated answers in IndexedDB
- Queue learning events when offline
- Sync when connection restored

### Phase 8: Multi-Tab Sync
- Share autofill state across tabs
- Prevent duplicate applications
- Unified history across sessions

### Phase 9: Custom Styles
- Allow users to create custom generation styles
- A/B test user styles vs server styles
- Export/import style templates

### Phase 10: Form Prefill
- Prefetch common forms on extension load
- Predictive autofill as user types
- Instant fill for known ATS platforms
