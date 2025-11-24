# Thread Viewer – Follow-up Drafts

This document describes the AI-powered follow-up draft feature in the Thread Viewer, which helps users generate professional follow-up emails for recruiter threads.

## Overview

When viewing a recruiter email thread that has an associated Tracker application, users can generate an AI-powered follow-up email draft with a single click. The feature uses Agent V2 with LLM integration (Ollama/OpenAI) to analyze the thread history and application context to produce contextually relevant follow-up emails.

## Features

### 1. Draft Follow-up Button

**Purpose**: Allows users to quickly generate a professional follow-up email draft based on the thread conversation history and application context.

**Behavior**:
- Button appears in the Thread Viewer header when viewing any thread
- Labeled "Draft follow-up" with a purple Sparkles icon (AI indicator)
- When clicked, calls the backend API to generate a draft
- Shows "Generating..." state while the LLM processes the request
- Disabled during generation to prevent duplicate requests

**UI Elements**:
- Button with Sparkles icon and "Draft follow-up" label
- Purple theme (consistent with Agent V2 AI features)
- `data-testid="thread-viewer-draft-followup"` for testing

**Code Location**:
- Component: `src/components/mail/ThreadViewer.tsx` (lines 227-241)
- Hook: `src/hooks/useFollowupDraft.ts`

### 2. Draft Display Card

**Purpose**: Displays the AI-generated follow-up draft in an attractive, easy-to-read format with copy actions.

**Layout**:
- Purple-themed card with subtle border and background
- Header with title "Follow-up Draft" and description
- Close button to dismiss the draft
- Two sections:
  - **Subject Line**: Shows email subject with subtle background
  - **Body**: Shows email body text with proper formatting

**Copy Actions**:
Two copy buttons are provided for flexibility:
1. **Copy Full Draft**: Copies subject + body in email format:
   ```
   Subject: [subject line]

   [body text]
   ```
2. **Copy Body Only**: Copies just the body text for pasting into an existing email

**UI Elements**:
- Purple card with `border-purple-500/30` and `bg-purple-950/20`
- Two badge-style copy buttons with clipboard icons
- Toast notifications on successful copy
- `data-testid` attributes for testing

**Code Location**:
- Component: `src/components/mail/ThreadViewer.tsx` (lines 244-328)
- Copy handlers: `src/hooks/useFollowupDraft.ts`

### 3. Backend API Endpoint

**Endpoint**: `POST /v2/agent/followup-draft`

**Purpose**: Generate AI-powered follow-up email drafts using Agent V2 orchestrator with thread and application context.

**Request Payload**:
```typescript
{
  user_id: string;          // User ID (resolved from session or payload)
  thread_id: string;        // Gmail thread ID
  application_id?: number;  // Optional: Tracker application ID for context
  mode: "preview_only";     // Only "preview_only" supported (future: "execute")
}
```

**Response**:
```typescript
{
  status: "ok" | "error";
  draft?: {
    subject: string;  // Email subject line
    body: string;     // Email body text
  };
  message?: string;   // Error message if status="error"
}
```

**Implementation Details**:
- Uses Agent V2 `orchestrator.draft_followup()` method
- Calls `thread_detail` tool to fetch thread context from Elasticsearch
- Queries Application model for job/company context (if `application_id` provided)
- Builds LLM prompt with:
  - System prompt: Professional follow-up assistant
  - User prompt: Thread summary + application context
- LLM fallback chain: Ollama (llama3:latest) → OpenAI (gpt-4o-mini)
- Temperature: 0.3 (balanced creativity)
- JSON format enforced for structured output

**Code Location**:
- Router: `services/api/app/routers/agent.py` (lines 393-490)
- Orchestrator: `services/api/app/agent/orchestrator.py` (lines 1512-1689)
- Schemas: `services/api/app/schemas_agent.py` (lines 395-435)

### 4. Analytics & Metrics

**Purpose**: Track usage and performance of the follow-up draft feature for product insights and debugging.

**Prometheus Metrics**:
- **Counter**: `applylens_followup_draft_requested_total{source="thread_viewer"}`
  - Increments on each draft request
  - Labeled by source (currently only "thread_viewer")
  - Location: `services/api/app/metrics.py`

**Analytics Events**:
1. `followup_draft_generated` - Draft successfully created
   - Properties: `thread_id`, `has_application_context`
2. `followup_draft_error` - Draft generation failed
   - Properties: `error_message`
3. `followup_draft_copied` - Full draft copied to clipboard
   - Properties: `thread_id`
4. `followup_draft_body_copied` - Body-only copied to clipboard
   - Properties: `thread_id`

**Code Location**:
- Metrics: `services/api/app/metrics.py`, `services/api/app/metrics/__init__.py`
- Analytics: `apps/web/src/lib/analytics.ts` (lines 19-22)

## User Workflow

### Typical Use Case

1. **User navigates to /chat** and clicks "Follow-ups" mail tool
2. **Thread list appears** showing recruiter threads needing replies
3. **User clicks a thread row** to open Thread Viewer
4. **User sees "Draft follow-up" button** in the Thread Viewer header
5. **User clicks the button** to generate a draft
6. **Draft appears in purple card** below the button with subject and body
7. **User reviews the draft** and decides to use it
8. **User clicks "Copy" or "Copy Body Only"** to copy to clipboard
9. **User pastes into Gmail** (or other email client) and edits as needed
10. **User sends the follow-up email** to the recruiter

### With Application Context

If the thread is linked to a Tracker application (`applicationId` present):
- The draft includes context like job title, company name, and application status
- More personalized and relevant follow-up content
- Example: "I wanted to follow up on my application for Software Engineer at Acme Corp..."

### Without Application Context

If the thread is NOT linked to a Tracker application:
- The draft is based solely on the thread conversation history
- Still professional and contextually appropriate
- Example: "I wanted to follow up on our recent conversation..."

## Technical Architecture

### Frontend Components

1. **useFollowupDraft Hook**
   - State management for draft, isGenerating, error
   - `generateDraft()` - Calls API with thread_id and optional application_id
   - `clearDraft()` - Clears draft and error state
   - `copyDraftToClipboard()` - Copies full draft (subject + body)
   - `copyBodyToClipboard()` - Copies body only
   - Toast notifications for user feedback
   - Analytics tracking

2. **ThreadViewer Component**
   - Integrates `useFollowupDraft` hook
   - Renders "Draft follow-up" button
   - Conditionally renders draft display card
   - Passes `threadId` and `applicationId` to hook

### Backend Components

1. **Agent Router** (`/v2/agent/followup-draft`)
   - Validates request payload
   - Resolves user_id from session or payload
   - Calls orchestrator method
   - Increments Prometheus counter
   - Returns JSON response

2. **Orchestrator** (`draft_followup()`)
   - Executes `thread_detail` tool to fetch thread context
   - Queries Application model for job/company context
   - Builds LLM prompt with combined context
   - Calls `_call_llm_for_draft()` helper
   - Parses JSON response {subject, body}
   - Returns `FollowupDraftResponse`

3. **LLM Integration** (`_call_llm_for_draft()`)
   - Primary: Ollama (llama3:latest) via httpx POST
   - Fallback: OpenAI (gpt-4o-mini) via httpx POST
   - Temperature: 0.3
   - JSON format enforced
   - Error handling and logging

## Testing

### Backend Tests

**File**: `services/api/tests/test_agent_followup_draft.py` (334 lines, 8 tests)

**TestFollowupDraftEndpoint** (5 tests):
- `test_followup_draft_success` - Happy path with valid thread_id
- `test_followup_draft_missing_thread_id` - 400 error validation
- `test_followup_draft_invalid_mode` - 400 error validation
- `test_followup_draft_orchestrator_error` - 500 error handling
- `test_followup_draft_no_application_context` - Success without application_id

**TestOrchestratorDraftFollowup** (3 tests):
- `test_orchestrator_draft_followup_executes_tool` - Tool execution validation
- `test_orchestrator_draft_followup_empty_thread` - Handles empty thread
- `test_orchestrator_draft_followup_llm_failure` - LLM error handling

### Frontend Tests

**File**: `apps/web/src/test/ThreadViewer.followupDraft.test.tsx` (334 lines, 8 tests)

**Coverage**:
- ✅ Button renders correctly
- ✅ Draft generation with application_id
- ✅ Draft generation without application_id
- ✅ API error handling
- ✅ Copy full draft to clipboard
- ✅ Copy body only to clipboard
- ✅ Clear draft action
- ✅ Network error handling

### E2E Tests

**File**: `apps/web/tests/e2e/chat-followup-draft-button.spec.ts`

**Behavior**:
- Navigate to `/chat`
- Click "Follow-ups" mail tool
- Find thread with `data-application-id` attribute
- Click thread row to open Thread Viewer
- Assert "Draft follow-up" button is visible
- **Does NOT click button** (avoids LLM calls in prod)

**Tags**: `@prodSafe`, `@chat`, `@threads`, `@followup-draft`

## Configuration

### Environment Variables

**Backend** (services/api):
- `OLLAMA_BASE` - Ollama API URL (e.g., `http://localhost:11434`)
- `OLLAMA_MODEL` - Model name (e.g., `llama3:latest`, `gpt-oss:20b`)
- `OPENAI_API_KEY` - OpenAI API key (fallback)
- `OPENAI_MODEL` - OpenAI model name (e.g., `gpt-4o-mini`)

**Frontend** (apps/web):
- No specific env vars required
- Uses standard API base URL configuration

## Future Enhancements

### Planned Features

1. **Execute Mode** (`mode="execute"`)
   - Send draft directly to Gmail without manual copy/paste
   - Requires Gmail API send permissions
   - Integration with `gmail_service.py`

2. **Draft Templates**
   - Predefined templates for common scenarios
   - User can select template before generation
   - Examples: "Initial follow-up", "Second follow-up", "Thank you"

3. **Draft History**
   - Save generated drafts for later reference
   - View previously generated drafts
   - Edit and re-generate based on feedback

4. **Multi-draft Generation**
   - Generate multiple variations of the same draft
   - User can choose the best version
   - A/B test different prompts for quality

5. **Inline Editing**
   - Edit draft within the UI before copying
   - Real-time preview
   - Save edits as custom template

## Troubleshooting

### Draft Generation Fails

**Symptom**: Error toast appears after clicking "Draft follow-up"

**Possible Causes**:
1. **Ollama not running**: Check `OLLAMA_BASE` URL is accessible
2. **OpenAI API key invalid**: Verify `OPENAI_API_KEY` is set and valid
3. **Thread not found**: Ensure thread_id exists in Elasticsearch
4. **LLM timeout**: Increase timeout in orchestrator (currently 30s)

**Solution**:
- Check API logs for detailed error messages
- Verify LLM service health
- Check Prometheus metrics for error rates

### Button Not Visible

**Symptom**: "Draft follow-up" button doesn't appear in Thread Viewer

**Possible Causes**:
1. **Thread not loaded**: Thread Viewer not fully initialized
2. **Component not mounted**: React component tree issue

**Solution**:
- Refresh the page
- Check browser console for React errors
- Verify `data-testid="thread-viewer-draft-followup"` exists in DOM

### Copy to Clipboard Fails

**Symptom**: "Failed to copy" toast appears

**Possible Causes**:
1. **Browser permissions**: Clipboard API requires HTTPS or localhost
2. **Browser compatibility**: Older browsers don't support Clipboard API

**Solution**:
- Use HTTPS in production
- Test in modern browser (Chrome 76+, Firefox 63+, Safari 13.1+)
- Check browser console for permission errors

## Related Documentation

- [Agent V2 Deployment](../../AGENT_V2_DEPLOYMENT.md)
- [Tracker Mail Integration](./TRACKER_MAIL_INTEGRATION.md)
- [E2E Testing Guide](./docs/E2E_GUIDE.md)
- [Production Deployment](../../docs/PRODUCTION_DEPLOYMENT.md)

## Version History

- **v0.6.1** (2025-11-24): Initial release of follow-up draft feature
  - POST /v2/agent/followup-draft endpoint
  - Thread Viewer "Draft follow-up" button
  - Clipboard copy actions
  - Analytics and metrics tracking
  - Comprehensive test coverage (backend + frontend + E2E)
