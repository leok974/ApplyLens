# ApplyLens v0.4.45 - UX Polish for Draft Replies

**Deployed:** October 25, 2025  
**Status:** ✅ Production Deployment Complete  
**Docker Tag:** `leoklemet/applylens-web:v0.4.45`

---

## 🎯 Overview

This release adds two quality-of-life improvements to the draft reply feature, making it more professional and trackable:

1. **Auto-prefix "Re:" to subject lines** - Prevents looking like cold outreach
2. **Timestamped confirmation messages** - Track when drafts were created

---

## 🚀 Features

### 1. Auto-prefix "Re:" in Gmail Subject Line

**Problem:** When replying to recruiters, the subject line might not have "Re:" prefix, making the follow-up look like a new cold email instead of a reply to an ongoing conversation.

**Solution:**
- ReplyDraftModal now checks if subject starts with "re:" (case-insensitive)
- If not present, automatically prefixes "Re: " before opening Gmail
- This makes follow-ups look professional and context-aware

**Implementation:**
```typescript
// apps/web/src/components/ReplyDraftModal.tsx
const handleOpenGmail = () => {
  const recipientEmail = draft.sender_email || senderEmail || draft.sender
  
  // Auto-prefix "Re:" if not already present (prevents looking like cold outreach)
  const finalSubject = draft.subject?.toLowerCase().startsWith("re:") 
    ? draft.subject 
    : `Re: ${draft.subject || ""}`
  
  const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(recipientEmail)}&su=${encodeURIComponent(finalSubject)}&body=${encodeURIComponent(editedDraft)}`
  window.open(gmailUrl, '_blank')
}
```

**Example:**
- Original subject: "Software Engineer Position - Follow Up"
- Gmail compose URL: "Re: Software Engineer Position - Follow Up"

---

### 2. Timestamped Confirmation Messages

**Problem:** When managing 8+ job applications, users need to track when drafts were created to follow up at appropriate intervals.

**Solution:**
- Confirmation messages now include ISO timestamp
- Displayed in readable format below the message
- Format: `MM/DD/YYYY, H:MM AM/PM`

**Implementation:**

**Backend (`ConversationMessage` interface):**
```typescript
// apps/web/src/components/MailChat.tsx
interface ConversationMessage extends Message {
  response?: ChatResponse
  assistantResponse?: AssistantQueryResponse
  error?: string
  timestamp?: string  // ISO 8601 timestamp for confirmation messages
}
```

**Timestamp Storage:**
```typescript
// When draft is generated
setMessages(prev => [...prev, {
  role: 'assistant',
  content: `✅ Draft ready for ${sender}`,
  timestamp: new Date().toISOString()  // e.g., "2025-10-25T14:22:15.123Z"
}])
```

**Timestamp Display:**
```typescript
// In message rendering
{msg.timestamp && (
  <div className="mt-1 text-[11px] text-neutral-500">
    {new Date(msg.timestamp).toLocaleString('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })}
  </div>
)}
```

**Example Output:**
```
✅ Draft ready for Sarah Johnson
10/25/2025, 2:14 PM
```

---

## 📁 Files Changed

### Frontend (`apps/web/`)
- **`src/components/ReplyDraftModal.tsx`**
  - Added "Re:" auto-prefix logic in `handleOpenGmail()`
  
- **`src/components/MailChat.tsx`**
  - Updated `ConversationMessage` interface with `timestamp?: string`
  - Added timestamp to confirmation messages in `handleDraftReply()`
  - Added timestamp rendering in message display section

### Infrastructure
- **`docker-compose.prod.yml`** - Updated image tag to v0.4.45

---

## 🧪 Testing

### Manual Testing Steps:

**Test 1: Re: Auto-prefix**
1. Generate a draft for an email with subject "Software Engineer Position"
2. Click "Open in Gmail"
3. ✅ Verify Gmail compose subject line shows: "Re: Software Engineer Position"
4. Generate a draft for an email with subject "Re: Follow-up on Interview"
5. Click "Open in Gmail"
6. ✅ Verify Gmail compose subject line shows: "Re: Follow-up on Interview" (no double "Re:")

**Test 2: Timestamp Display**
1. Ask assistant: "Which recruiters haven't replied in 5 days? Draft follow-ups."
2. Click "Draft Reply" on a suggested action
3. ✅ Verify assistant message appears: "✅ Draft ready for [Name]"
4. ✅ Verify timestamp appears below in format: "10/25/2025, 2:14 PM"
5. Generate multiple drafts
6. ✅ Verify each has its own unique timestamp

**Test 3: Edge Cases**
- Subject with "RE:" (uppercase) → Should not add second prefix
- Subject with "re:" (lowercase) → Should not add second prefix
- Subject with "Re:" (mixed case) → Should not add second prefix
- Empty/null subject → Should result in "Re: "
- Messages without timestamp → Should render normally (backward compatible)

---

## 📊 Deployment

**Build & Push:**
```bash
docker build -f apps/web/Dockerfile.prod -t leoklemet/applylens-web:v0.4.45 apps/web
docker push leoklemet/applylens-web:v0.4.45
```

**Deploy:**
```bash
docker compose -f docker-compose.prod.yml up -d web
```

**Status:**
- ✅ Image built successfully
- ✅ Image pushed to Docker Hub
- ✅ Container deployed and healthy
- ✅ Service accessible on port 5175

---

## 🎨 UI/UX Impact

### Before:
```
[Assistant Message]
✅ Draft ready for Sarah Johnson
[metadata about search results]
```

### After:
```
[Assistant Message]
✅ Draft ready for Sarah Johnson
10/25/2025, 2:14 PM
[metadata about search results]
```

**Gmail Subject Before:**
- Subject: "Software Engineer Position"

**Gmail Subject After:**
- Subject: "Re: Software Engineer Position"

---

## 🔄 Backward Compatibility

- ✅ Messages without `timestamp` field render normally
- ✅ Existing drafts still work (no breaking changes)
- ✅ Subject line logic handles all variations of "Re:"

---

## 🐛 Known Issues

None identified.

---

## 🔄 Rollback Plan

If issues arise, rollback to v0.4.44:

```bash
# Edit docker-compose.prod.yml
# Change: image: leoklemet/applylens-web:v0.4.45 → v0.4.44

docker compose -f docker-compose.prod.yml up -d web
```

---

## 💡 User Benefits

### For Job Seekers:

1. **More Professional Follow-ups**
   - Automatic "Re:" prefix shows you're continuing a conversation
   - Recruiters immediately recognize it as a reply, not spam

2. **Better Outreach Tracking**
   - Timestamps create a paper trail of when drafts were generated
   - Easy to see at a glance when you last followed up
   - Helps manage multiple applications simultaneously

3. **No Manual Cleanup Needed**
   - No more copying subject, adding "Re:", then pasting back
   - Timestamps automatically appear—no extra clicks

### Example Workflow:
```
User: "Which recruiters haven't replied in 5 days? Draft follow-ups."