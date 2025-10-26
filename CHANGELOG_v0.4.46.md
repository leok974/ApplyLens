# ApplyLens v0.4.46 - Complete Outreach Tracking

**Deployed:** October 25, 2025
**Status:** ✅ Production Deployment Complete
**Docker Tag:** `leoklemet/applylens-web:v0.4.46`

---

## 🎯 Overview

This release transforms the draft reply feature into a complete outreach tracking system with a visible timeline of all job application follow-ups.

### **Three Key Enhancements:**

1. **Subject line in draft confirmations** - See exactly which email you drafted
2. **"Sent follow-up" logs** - Auto-logged when you open draft in Gmail
3. **Visual timeline styling** - Draft vs Sent messages have distinct appearances

---

## 🚀 Features

### 1. Subject Line in Draft Confirmations

**Before:**
```
✅ Draft ready for Sarah Johnson
10/25/2025, 2:14 PM
```

**After:**
```
✅ Draft ready for Sarah Johnson (Re: Platform Engineer role)
10/25/2025, 2:14 PM
```

**Why it matters:** When managing 8+ applications, you need to know WHICH email was drafted without opening the modal.

**Implementation:**
```typescript
// MailChat.tsx - handleDraftReply
setMessages(prev => [...prev, {
  role: 'assistant',
  content: `✅ Draft ready for ${sender}${subject ? ` (Re: ${subject})` : ""}`,
  timestamp: new Date().toISOString(),
  meta: {
    kind: "draft_ready",
    sender: sender,
    subject: subject ?? "",
  },
}])
```

---

### 2. Automatic "Sent Follow-up" Logging

**Problem:** Users had no record of when they actually sent drafts from Gmail. The timeline ended at "draft ready" with no confirmation of sending.

**Solution:** ReplyDraftModal now triggers a callback when "Open in Gmail" is clicked, which logs a "sent" confirmation in the chat.

**After clicking "Open in Gmail":**
```
📨 Sent follow-up to Sarah Johnson (Re: Platform Engineer role)
10/25/2025, 2:16 PM
```

**Implementation:**

**MailChat.tsx - New handler:**
```typescript
function handleConfirmSentFollowup(sender: string, subject?: string) {
  setMessages(prev => [
    ...prev,
    {
      role: 'assistant',
      content: `📨 Sent follow-up to ${sender}${subject ? ` (Re: ${subject})` : ""}`,
      timestamp: new Date().toISOString(),
      meta: {
        kind: "sent_confirm",
        sender,
        subject: subject ?? "",
      },
    },
  ])
}
```

**Modal integration:**
```typescript
<ReplyDraftModal
  draft={draftModal}
  onClose={() => setDraftModal(null)}
  emailId={(draftModal as any)._emailId}
  account={userEmail}
  senderEmail={(draftModal as any)._senderEmail}
  onOpenedInGmail={() => {
    handleConfirmSentFollowup(
      draftModal.sender,
      draftModal.subject
    )
  }}
/>
```

**ReplyDraftModal.tsx - Trigger callback:**
```typescript
const handleOpenGmail = () => {
  const recipientEmail = draft.sender_email || senderEmail || draft.sender
  const finalSubject = draft.subject?.toLowerCase().startsWith("re:")
    ? draft.subject
    : `Re: ${draft.subject || ""}`

  const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(recipientEmail)}&su=${encodeURIComponent(finalSubject)}&body=${encodeURIComponent(editedDraft)}`
  window.open(gmailUrl, '_blank', 'noopener,noreferrer')

  // NEW: log the send
  if (onOpenedInGmail) {
    onOpenedInGmail()
  }
}
```

---

### 3. Visual Timeline Styling

**Problem:** All assistant messages looked the same. Hard to distinguish drafts from actual sends.

**Solution:** "Sent" messages now have italic green styling, creating a clear visual distinction.

**Draft message styling:**
- Normal text color (white/gray)
- ✅ checkmark icon
- Regular font weight

**Sent message styling:**
- Italic green text (`text-green-400`)
- 📨 mail icon
- "Logged action" vibe

**Implementation:**
```typescript
// MailChat.tsx - Message rendering
<div className={`whitespace-pre-wrap break-words ${
  msg.meta?.kind === "sent_confirm" ? "italic text-green-400" : ""
}`}>
  {msg.content}
</div>
```

**Visual Result:**
```
✅ Draft ready for Sarah Johnson (Re: Platform Engineer role)
10/25/2025, 2:14 PM

📨 Sent follow-up to Sarah Johnson (Re: Platform Engineer role)  [italic green]
10/25/2025, 2:16 PM
```

---

## 📊 Complete User Flow

### **Example: Following up with 3 recruiters**

**User:** "Which recruiters haven't replied in 5 days? Draft follow-ups."

**Assistant:**
```
Found 3 recruiters who haven't replied:

1. Sarah Johnson - Platform Engineer role
2. Mike Chen - Backend Developer position
3. Lisa Rodriguez - Full Stack Engineer opening

[Suggested Actions]
[Draft Reply to Sarah Johnson]
[Draft Reply to Mike Chen]
[Draft Reply to Lisa Rodriguez]
```

**User clicks: Draft Reply to Sarah Johnson**

**Assistant (immediately):**
```
✅ Draft ready for Sarah Johnson (Re: Platform Engineer role)
10/25/2025, 2:14 PM
```

**[Modal opens with pre-filled draft]**

**User edits draft, clicks "Open in Gmail"**

**Assistant (immediately):**
```
📨 Sent follow-up to Sarah Johnson (Re: Platform Engineer role)  [italic green]
10/25/2025, 2:16 PM
```

**Gmail compose opens with:**
- To: sarah.johnson@company.com
- Subject: Re: Platform Engineer role
- Body: [edited draft]

**User repeats for Mike Chen and Lisa Rodriguez**

**Final chat history:**
```
User: Which recruiters haven't replied in 5 days? Draft follow-ups.
