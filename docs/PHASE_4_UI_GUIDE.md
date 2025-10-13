# Phase 4 UI Guide

## Actions Button in Header

```
┌─────────────────────────────────────────────────────────────────┐
│  Gmail Inbox    [Inbox] [Search] [Tracker] [Profile] [Settings] │
│                                                                   │
│  [Sync 7 days] [Sync 60 days] [✨ Actions 3] [🌙]               │
│                                    ↑                              │
│                              Badge shows pending count            │
└─────────────────────────────────────────────────────────────────┘
```

When clicked, tray slides in from right →

## ActionsTray Component

```
                              ┌────────────────────────────────────┐
                              │ ✨ Proposed Actions           [↻] [×] │
                              │                                   3 │
                              ├────────────────────────────────────┤
                              │                                     │
                              │ ┌─────────────────────────────────┐ │
                              │ │ Job Application: Software Eng   │ │
                              │ │ jobs@linkedin.com               │ │
                              │ │                    [Add Label] │ │
                              │ │                                │ │
                              │ │ ████████████░░░░░ 75%          │ │
                              │ │                                │ │
                              │ │ label: "Job Applications"      │ │
                              │ │ via Job application auto-label │ │
                              │ │                                │ │
                              │ │ ▼ Explain                      │ │
                              │ │   This email matches job       │ │
                              │ │   application keywords:        │ │
                              │ │   • Subject contains "offer"   │ │
                              │ │   • Category is "applications" │ │
                              │ │   • High confidence (75%)      │ │
                              │ │                                │ │
                              │ │ [✓ Approve]    [✗ Reject]     │ │
                              │ └─────────────────────────────────┘ │
                              │                                     │
                              │ ┌─────────────────────────────────┐ │
                              │ │ 50% off sale ends today!        │ │
                              │ │ deals@store.com                 │ │
                              │ │                      [Archive]  │ │
                              │ │                                │ │
                              │ │ ████████░░░░░░░░ 85%           │ │
                              │ │                                │ │
                              │ │ expires_at: 2025-10-11         │ │
                              │ │ via Promo auto-archive         │ │
                              │ │                                │ │
                              │ │ ▶ Explain                      │ │
                              │ │                                │ │
                              │ │ [✓ Approve]    [✗ Reject]     │ │
                              │ └─────────────────────────────────┘ │
                              │                                     │
                              │ ┌─────────────────────────────────┐ │
                              │ │ Urgent: Verify your account     │ │
                              │ │ phishing@bad.com                │ │
                              │ │                   [Quarantine]  │ │
                              │ │                                │ │
                              │ │ ████████████████████ 100%      │ │
                              │ │                                │ │
                              │ │ risk_score: 95                 │ │
                              │ │ via High-risk quarantine       │ │
                              │ │                                │ │
                              │ │ ▶ Explain                      │ │
                              │ │                                │ │
                              │ │ [✓ Approve]    [✗ Reject]     │ │
                              │ └─────────────────────────────────┘ │
                              │                                     │
                              └────────────────────────────────────┘
                                      420px width
                                      Fixed right position
```

## Empty State

```
                              ┌────────────────────────────────────┐
                              │ ✨ Proposed Actions           [↻] [×] │
                              ├────────────────────────────────────┤
                              │                                     │
                              │                                     │
                              │           ✨                        │
                              │       (sparkles icon)               │
                              │                                     │
                              │     No pending actions              │
                              │                                     │
                              │  Actions will appear here when      │
                              │  policies match emails              │
                              │                                     │
                              │                                     │
                              └────────────────────────────────────┘
```

## Action Type Badges

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  [Add Label]          Blue badge                            │
│  [Archive]            Purple badge                          │
│  [Move]               Indigo badge                          │
│  [Unsubscribe]        Orange badge                          │
│  [Create Event]       Green badge                           │
│  [Create Task]        Teal badge                            │
│  [Block Sender]       Red badge                             │
│  [Quarantine]         Yellow badge                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Confidence Progress Bars

```
High Confidence (>80%):
████████████████████░░ 85%    ← Green tint

Medium Confidence (50-80%):
████████████░░░░░░░░░░ 60%    ← Blue tint

Low Confidence (<50%):
██████░░░░░░░░░░░░░░░░ 30%    ← Gray tint
```

## Expandable Rationale

**Collapsed:**
```
┌─────────────────────────────────────────────┐
│ ▶ Explain                                   │
└─────────────────────────────────────────────┘
```

**Expanded:**
```
┌─────────────────────────────────────────────┐
│ ▼ Explain                                   │
│                                             │
│   This email appears to be an expired       │
│   promotional offer. The subject mentions   │
│   "sale ends today" and the expires_at      │
│   timestamp is in the past.                 │
│                                             │
│   Reasons:                                  │
│   • Category matches "promotions"           │
│   • Expires timestamp is 2025-10-11         │
│   • Current time is after expiry            │
│   • Policy confidence threshold met (70%)   │
│                                             │
└─────────────────────────────────────────────┘
```

## Approve Flow

### 1. User clicks "Approve"

```
┌─────────────────────────────────────────────┐
│ [⏳ Processing...]    [Reject]              │
│         ↑                                   │
│   Button disabled during execution          │
└─────────────────────────────────────────────┘
```

### 2. Screenshot captured

```javascript
const canvas = await html2canvas(document.body, {
  allowTaint: true,
  useCORS: true,
  scale: 0.5 // Reduced size
})
const screenshotDataUrl = canvas.toDataURL("image/png")
// → "data:image/png;base64,iVBORw0KGgoAAAA..."
```

### 3. Toast notification

```
┌─────────────────────────────────────────────┐
│  ✅ Action approved                         │
│  Archive executed successfully              │
└─────────────────────────────────────────────┘
```

### 4. Action removed from tray

The action card disappears from the list. Badge count decrements.

## Reject Flow

### 1. User clicks "Reject"

```
┌─────────────────────────────────────────────┐
│ [Approve]    [⏳ Processing...]             │
│                      ↑                      │
│                Button disabled              │
└─────────────────────────────────────────────┘
```

### 2. Toast notification

```
┌─────────────────────────────────────────────┐
│  🚫 Action rejected                         │
│  Action has been dismissed                  │
└─────────────────────────────────────────────┘
```

### 3. Action removed from tray

The action card disappears. Audit trail records rejection as "noop".

## Responsive Behavior

### Desktop (>420px available)
- Tray slides in from right
- Backdrop covers remaining screen
- Tray is 420px wide

### Mobile (<420px available)
- Tray covers full screen
- Still slides in from right
- Close button in header

## Color Scheme (Dark Mode)

```
Background:       #171717 (neutral-900)
Cards:            #262626 (neutral-800/50)
Borders:          #404040 (neutral-700)
Text (primary):   #fafafa (neutral-100)
Text (secondary): #a3a3a3 (neutral-400)
Text (tertiary):  #737373 (neutral-500)

Approve button:   #16a34a (green-600)
Reject button:    Outline with neutral-700

Progress bar bg:  #404040 (neutral-700)
Progress bar fg:  #3b82f6 (blue-500)
```

## Interaction States

### Hover States
- Buttons: Subtle background color change
- Expand/collapse: Text color lightens
- Action cards: No hover effect (not clickable)

### Loading States
- Refresh button: Icon spins
- Approve/Reject: Button text changes to "Processing..."
- Entire tray: Skeleton loader (optional)

### Error States
- Toast notification with red background
- Action remains in tray
- Error message in toast description

## Keyboard Shortcuts (Future)

```
Esc         → Close tray
↑/↓         → Navigate actions
Enter       → Approve selected
Delete      → Reject selected
Space       → Toggle explanation
R           → Refresh
```

## Animations

### Tray Slide-In
```css
transition: transform 300ms ease-out
from: translateX(100%)
to: translateX(0)
```

### Backdrop Fade
```css
transition: opacity 200ms ease-out
from: opacity(0)
to: opacity(0.5)
```

### Action Card Remove
```css
transition: opacity 200ms, height 200ms
from: opacity(1) height(auto)
to: opacity(0) height(0)
```

### Progress Bar Fill
```css
transition: width 500ms ease-out
```

## Accessibility

- **Focus Management:** Focus trapped in tray when open
- **Keyboard Navigation:** Tab through actions, Enter to approve
- **Screen Reader:** aria-label on all buttons
- **Color Contrast:** WCAG AA compliant (4.5:1 minimum)
- **Reduced Motion:** Respects prefers-reduced-motion

## Example User Journey

1. **User logs in**
   - Badge shows "3" pending actions
   - Sparkles icon pulses gently (optional)

2. **User clicks "Actions" button**
   - Tray slides in smoothly
   - Shows 3 action cards
   - First card expanded by default

3. **User reviews first action**
   - Reads email subject: "Job Application: Software Engineer"
   - Sees action: "Add Label"
   - Checks confidence: 75%
   - Expands rationale: "Matches job keywords"

4. **User approves action**
   - Clicks "Approve" button
   - Screenshot captured (barely noticeable)
   - Toast: "✅ Action approved"
   - Card disappears, badge shows "2"

5. **User reviews second action**
   - Expired promo email
   - Action: "Archive"
   - Confidence: 85%

6. **User rejects action**
   - Clicks "Reject" button
   - Toast: "🚫 Action rejected"
   - Card disappears, badge shows "1"

7. **User closes tray**
   - Clicks X button or backdrop
   - Tray slides out
   - Badge still shows "1" for remaining action

## Tips for Users

**Getting Started:**
1. Click "Actions" button to see pending actions
2. Review each action's details and confidence
3. Click "Explain" to understand why it was proposed
4. Approve or reject based on your judgment

**Best Practices:**
- Review high-confidence actions (>80%) quickly
- Scrutinize low-confidence actions (<50%)
- Check rationale for unfamiliar actions
- Approve in batches for efficiency

**Keyboard Users:**
- Tab through actions
- Space to expand/collapse
- Enter to approve
- Esc to close tray

**Understanding Confidence:**
- 80-100%: Very likely correct
- 50-80%: Likely correct, review recommended
- <50%: Uncertain, careful review needed

## Troubleshooting

**Tray won't open:**
- Check browser console for errors
- Verify API endpoint is accessible
- Check CORS configuration

**Actions not loading:**
- Check network tab for failed requests
- Verify Docker services are running
- Check API logs: `docker logs infra-api-1`

**Screenshot capture fails:**
- Check console for html2canvas errors
- Verify html2canvas is installed
- Screenshot failure is non-blocking (action still executes)

**Badge count wrong:**
- Wait 30s for next poll
- Click refresh button in tray
- Check `/api/actions/tray` endpoint

## Future Enhancements

**Planned:**
- [ ] "Always do this" button (create policy from action)
- [ ] Bulk approve/reject
- [ ] Action history view
- [ ] Policy testing UI
- [ ] Real-time SSE updates (no polling)
- [ ] Action scheduling (execute at specific time)

**Nice to Have:**
- [ ] Dark/light mode toggle
- [ ] Compact view mode
- [ ] Action undo (within 5 seconds)
- [ ] Action search/filter
- [ ] Export actions as CSV
- [ ] Action templates

---

**This UI is designed to be:**
- **Fast** - Smooth animations, optimistic updates
- **Clear** - Color-coded badges, confidence bars
- **Trustworthy** - Detailed rationale, screenshot audit
- **Efficient** - Quick approve/reject, keyboard shortcuts
- **Beautiful** - Modern design, thoughtful spacing

Enjoy your agentic email assistant! 🎉
