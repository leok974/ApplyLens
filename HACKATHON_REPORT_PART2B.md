# ApplyLens Architecture & Hackathon Readiness Report (Part 2B)

**Continued from HACKATHON_REPORT_PART2A.md**

---

## 6) Frontend (apps/web)

### Tech Stack

**Core Framework:**
- React 18.3.1 (hooks, concurrent features)
- TypeScript 5.5.4 (strict mode)
- Vite 5.4.8 (build tool, HMR)
- React Router 6.26.2 (client-side routing)

**UI Components:**
- Radix UI primitives (@radix-ui/* - 15 packages)
- shadcn/ui component library (customized)
- Tailwind CSS 4.1.14 (utility-first)
- class-variance-authority (component variants)
- lucide-react (icon library, 545 icons)

**State & Data:**
- No global state management (React Context + hooks)
- Fetch API for HTTP requests
- Local storage for preferences
- EventSource for SSE streams

**Testing:**
- Playwright 1.56.0 (E2E tests)
- 52 test specs covering critical flows
- Visual regression testing with screenshots

### Key Pages & Routes

**Application Structure:**
```
/                        → Redirect to /web/
/web/                    → Inbox (default landing page)
/web/inbox               → Email inbox with filters
/web/search              → Advanced search interface
/web/tracker             → Application tracking kanban
/web/chat                → Conversational inbox assistant
/web/settings            → User settings
/web/settings/security   → Security policies configuration
/web/policy-studio       → Policy management (admin)
```

**Route Configuration** (`apps/web/src/main.tsx`):
```typescript
<Router>
  <Routes>
    <Route path="/" element={<Navigate to="/web/" />} />
    <Route path="/web/" element={<InboxPolished />} />
    <Route path="/web/inbox" element={<InboxPolished />} />
    <Route path="/web/search" element={<Search />} />
    <Route path="/web/tracker" element={<Tracker />} />
    <Route path="/web/chat" element={<ChatPage />} />
    <Route path="/web/settings" element={<Settings />} />
    <Route path="/web/settings/security" element={<SettingsSecurity />} />
    <Route path="/web/policy-studio" element={<PolicyStudio />} />
  </Routes>
</Router>
```

### Major Components

**Inbox Components** (`apps/web/src/pages/InboxPolished.tsx`):
- `EmailList`: Virtualized email list with infinite scroll
- `EmailCard`: Individual email preview with risk badges
- `FilterBar`: Label filters (interview, offer, rejection, etc.)
- `SearchBar`: Quick search with autocomplete
- `SyncButton`: Manual Gmail sync trigger
- `RiskBadge`: Color-coded risk indicators (green/amber/red)

**Application Tracker** (`apps/web/src/pages/Tracker.tsx`):
- `KanbanBoard`: Drag-and-drop application tracking
- `ApplicationCard`: Job application with company, role, status
- `StatusColumn`: Swimlanes (Applied → Interview → Offer → Accepted/Rejected)
- `AddApplicationDialog`: Create new application
- `NotesEditor`: Rich text notes with auto-save

**Search Interface** (`apps/web/src/pages/Search.tsx`):
- `AdvancedFilters`: Date range, risk score, category, sender domain
- `SearchResults`: Highlighted snippets with relevance scores
- `FacetedSearch`: Category facets, risk distribution
- `SavedSearches`: Bookmark frequent queries

**Chat Assistant** (`apps/web/src/pages/ChatPage.tsx` + `components/MailChat.tsx`):
- `ChatHistory`: Message thread with user/assistant bubbles
- `ChatInput`: Natural language command input
- `CitationsList`: Clickable email citations
- `ActionButtons`: Execute suggested actions (archive, unsubscribe)
- `TypingIndicator`: Real-time response feedback

**Policy Studio** (`apps/web/src/pages/PolicyStudio.tsx`):
- `PolicyBundleList`: Version history with semantic versioning
- `PolicyEditor`: JSON schema editor with validation
- `SimulationPanel`: What-if testing sandbox
- `CanaryControls`: Deploy, promote, rollback controls
- `DiffViewer`: Side-by-side policy comparison

**Security Settings** (`apps/web/src/pages/SettingsSecurity.tsx`):
- `QuarantineQueue`: Review quarantined emails
- `RiskThresholds`: Configure auto-quarantine levels
- `BlocklistManager`: Add/remove blocked domains
- `SecurityEvents`: Audit log of security actions

### Component Examples

**RiskBadge Component:**
```typescript
// apps/web/src/components/RiskBadge.tsx
interface RiskBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
}

export function RiskBadge({ score, size = 'md' }: RiskBadgeProps) {
  const variant = 
    score >= 70 ? 'destructive' :  // Red - High risk
    score >= 40 ? 'warning' :       // Amber - Medium risk
    'default';                      // Green - Low risk
  
  return (
    <Badge variant={variant} className={cn('font-mono', sizes[size])}>
      {score}
    </Badge>
  );
}
```

**Email Card Component:**
```typescript
// apps/web/src/components/EmailCard.tsx
export function EmailCard({ email }: { email: Email }) {
  return (
    <Card className="hover:bg-accent/50 transition-colors">
      <CardHeader className="flex flex-row items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold truncate">{email.subject}</h3>
            {email.quarantined && <Badge variant="destructive">Quarantined</Badge>}
          </div>
          <p className="text-sm text-muted-foreground truncate">{email.sender}</p>
        </div>
        <RiskBadge score={email.risk_score} />
      </CardHeader>
      <CardContent>
        <p className="text-sm line-clamp-2">{email.snippet}</p>
        <div className="flex gap-2 mt-2">
          {email.labels.map(label => (
            <Badge key={label} variant="outline">{label}</Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

### Design System

**Theme Configuration** (`apps/web/tailwind.config.ts`):
```typescript
theme: {
  extend: {
    colors: {
      // Semantic color tokens
      background: "hsl(var(--background))",
      foreground: "hsl(var(--foreground))",
      card: "hsl(var(--card))",
      primary: "hsl(var(--primary))",
      secondary: "hsl(var(--secondary))",
      muted: "hsl(var(--muted))",
      accent: "hsl(var(--accent))",
      destructive: "hsl(var(--destructive))",
      // Status colors
      success: "hsl(142 76% 36%)",
      warning: "hsl(38 92% 50%)",
      info: "hsl(199 89% 48%)"
    }
  }
}
```

**Dark Theme Support:**
- CSS variables in `apps/web/src/index.css`
- `next-themes` package for theme switching
- All components use semantic tokens (no hardcoded colors)
- Automatic OS preference detection

**Typography:**
- Font: Inter (variable weight)
- Scale: text-xs → text-sm → text-base → text-lg → text-xl → text-2xl
- Line heights: leading-tight, leading-normal, leading-relaxed

**Spacing:**
- Base unit: 0.25rem (4px)
- Scale: p-1 (4px) → p-2 (8px) → p-4 (16px) → p-6 (24px) → p-8 (32px)
- Container max-width: 1280px

### State Management

**No Global State Library:**
- React Context for theme, user session
- Component-local state with useState
- URL state via React Router (search params)
- Server state fetched on-demand (no caching)

**Data Fetching Pattern:**
```typescript
// apps/web/src/hooks/useEmails.ts
export function useEmails(filters: EmailFilters) {
  const [emails, setEmails] = useState<Email[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    async function fetchEmails() {
      setLoading(true);
      const params = new URLSearchParams({
        q: filters.query,
        label_filter: filters.labels.join(','),
        limit: String(filters.limit)
      });
      
      const response = await fetch(`/api/search?${params}`);
      const data = await response.json();
      setEmails(data.hits);
      setLoading(false);
    }
    
    fetchEmails();
  }, [filters]);
  
  return { emails, loading };
}
```

**Form State:**
- Controlled components with useState
- Form validation with Zod schemas
- Error states displayed inline
- Optimistic updates for better UX

### Route Structure

**File Organization:**
```
apps/web/src/
├── main.tsx              # App entry point, router setup
├── App.tsx               # Root component, theme provider
├── pages/                # Route components
│   ├── Inbox.tsx
│   ├── InboxPolished.tsx
│   ├── Search.tsx
│   ├── Tracker.tsx
│   ├── ChatPage.tsx
│   ├── Settings.tsx
│   ├── SettingsSecurity.tsx
│   └── PolicyStudio.tsx
├── components/           # Reusable components
│   ├── ui/              # shadcn/ui base components
│   ├── EmailCard.tsx
│   ├── RiskBadge.tsx
│   ├── FilterBar.tsx
│   ├── MailChat.tsx
│   └── policy/          # Policy management components
├── hooks/               # Custom React hooks
│   ├── useEmails.ts
│   ├── useSearch.ts
│   └── useTheme.ts
├── lib/                 # Utilities
│   ├── utils.ts         # Helper functions
│   ├── api.ts           # API client
│   └── chatClient.ts    # Chat API wrapper
└── types/               # TypeScript types
    └── index.ts         # Shared type definitions
```

**Dynamic Imports:**
- Code splitting by route
- Lazy loading heavy components
- Suspense boundaries for loading states

### Feature Flags

**Configuration** (`apps/web/src/config/features.ts`):
```typescript
export const features = {
  chatEnabled: true,
  policyStudioEnabled: true,
  warehouseMetrics: Boolean(import.meta.env.VITE_USE_WAREHOUSE),
  sseEnabled: true
};
```

**Usage:**
```typescript
{features.chatEnabled && (
  <NavigationMenuItem>
    <Link to="/web/chat">Chat</Link>
  </NavigationMenuItem>
)}
```

---

## 7) Security, Privacy & Compliance

### CSP (Content Security Policy)

**Nginx Configuration** (all 3 configs updated):
```nginx
# infra/nginx/conf.d/applylens.prod.conf
add_header Content-Security-Policy "upgrade-insecure-requests" always;
```

**Effect:**
- Forces all HTTP requests to HTTPS
- Prevents mixed content warnings
- Browser automatically upgrades insecure requests

**Additional Headers:**
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### HTTPS & SSL

**Production Setup:**
- Cloudflare Tunnel handles SSL termination
- Automatic certificate management
- TLS 1.3 enforced
- HSTS enabled via Cloudflare

**Local Development:**
- HTTP only (no SSL)
- CORS configured for localhost origins

### Email Risk Scoring Pipeline

**Multi-Signal Analysis** (`services/api/app/security/analyzer.py`):

**1. Email Authentication (30 points max)**
```python
# DMARC verification
if dmarc_result == "fail":
    signals.append(RiskSignal("DMARC_FAIL", "high", 15))

# SPF verification
if spf_result in ["softfail", "fail"]:
    points = 10 if spf_result == "softfail" else 15
    signals.append(RiskSignal("SPF_FAIL", "medium" if spf_result == "softfail" else "high", points))

# DKIM verification
if dkim_result == "fail":
    signals.append(RiskSignal("DKIM_FAIL", "medium", 10))
```

**2. URL Mismatch Detection (40 points max)**
```python
# Extract URLs from body text
urls = extract_urls(body_text)

for display_text, actual_url in urls:
    if display_text != actual_url:
        # Phishing indicator
        signals.append(RiskSignal("URL_MISMATCH", "high", 20))
    
    # Check for suspicious TLDs
    tld = extract_tld(actual_url)
    if tld in SUSPICIOUS_TLDS:  # .tk, .ml, .ga, .cf, .gq
        signals.append(RiskSignal("SUSPICIOUS_TLD", "medium", 15))
```

**3. Domain Reputation (20 points max)**
```python
sender_domain = extract_domain(from_email)

# Check blocklist
if blocklists.is_blocklisted(sender_domain):
    signals.append(RiskSignal("BLOCKLISTED", "critical", 20))

# Check domain age
if domain_first_seen_days_ago is not None and domain_first_seen_days_ago < 30:
    signals.append(RiskSignal("NEW_DOMAIN", "medium", 10))
```

**4. Content Analysis (10 points max)**
```python
# Urgency language
if any(phrase in body_text.lower() for phrase in URGENT_PHRASES):
    # "verify now", "account suspended", "immediate action"
    signals.append(RiskSignal("URGENT_LANGUAGE", "low", 5))

# Suspicious attachments
for attachment in attachments:
    ext = attachment.get("filename", "").split(".")[-1].lower()
    if ext in DANGEROUS_EXTENSIONS:  # .exe, .scr, .bat, .com
        signals.append(RiskSignal("SUSPICIOUS_ATTACHMENT", "high", 10))
```

**Scoring Thresholds:**
- **0-39**: Low risk (green badge)
- **40-69**: Medium risk (amber badge, flag only)
- **70-100**: High risk (red badge, auto-quarantine)

### Quarantine Workflow

**Automatic Quarantine:**
```python
# services/api/app/security/analyzer.py
def analyze(...) -> RiskAnalysis:
    risk_score = sum(signal.points for signal in signals)
    quarantined = risk_score >= 70
    
    return RiskAnalysis(
        risk_score=risk_score,
        signals=signals,
        quarantined=quarantined
    )
```

**User Review Flow:**
1. User sees quarantined emails in inbox (red badge)
2. Click to expand evidence panel (shows all signals)
3. Options:
   - **Release**: Mark as safe, update risk score
   - **Keep Quarantined**: Leave as-is
   - **Permanent Block**: Add sender to blocklist

**Bulk Actions:**
```http
POST /security/bulk/release
Body: {"email_ids": [123, 456, 789]}
Response: {"status": "ok", "released": 3}
```

### Approval Workflows (HMAC Signatures)

**Signature Generation** (`services/api/app/utils/signing.py`):
```python
import hmac
import hashlib

HMAC_SECRET = os.getenv("HMAC_SECRET", "dev-secret-key")

def sign_approval(approval_data: dict) -> str:
    """Generate HMAC-SHA256 signature for approval request."""
    message = json.dumps(approval_data, sort_keys=True)
    signature = hmac.new(
        HMAC_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"hmac-sha256:{signature}"

def verify_signature(approval_data: dict, signature: str) -> bool:
    """Verify HMAC signature matches approval data."""
    expected = sign_approval(approval_data)
    return hmac.compare_digest(expected, signature)
```

**Usage in Approval Flow:**
```python
# Create approval request
approval = ApprovalRequest(
    agent="knowledge_update",
    action="apply_changes",
    params={"changes_count": 150}
)
approval.signature = sign_approval(approval.to_dict())
db.add(approval)
db.commit()

# Verify before execution
if not verify_signature(approval.to_dict(), approval.signature):
    raise HTTPException(400, "Invalid signature - data may have been tampered")
```

### Policy Enforcement

**Policy Engine** (`services/api/app/policy/engine.py`):
```python
def evaluate(agent: str, action: str, params: dict) -> PolicyDecision:
    """Evaluate policies by priority, deny overrides allow."""
    rules = db.query(PolicyRule).filter_by(
        agent=agent, action=action
    ).order_by(PolicyRule.priority.desc()).all()
    
    for rule in rules:
        if matches_conditions(rule.conditions, params):
            if rule.effect == "deny":
                return PolicyDecision("denied", reason=rule.reason)
            elif rule.effect == "allow":
                return PolicyDecision("allowed", reason=rule.reason)
    
    # Default: allow if no rules match
    return PolicyDecision("allowed", reason="No matching rules")
```

**Budget Enforcement:**
```python
def check_budget(agent: str, budget: Budget, used: Budget) -> bool:
    """Enforce resource limits."""
    if used.ms > budget.ms:
        raise BudgetExceeded(f"Time limit exceeded: {used.ms}ms > {budget.ms}ms")
    if used.ops > budget.ops:
        raise BudgetExceeded(f"Operation limit exceeded: {used.ops} > {budget.ops}")
    if used.cost_cents > budget.cost_cents:
        raise BudgetExceeded(f"Cost limit exceeded: ${used.cost_cents/100} > ${budget.cost_cents/100}")
```

### Cookie Policies

**Session Cookies:**
- `session_id`: Encrypted session token (HttpOnly, Secure, SameSite=Lax)
- `user_email`: Plain text for client-side display (no sensitive data)
- Max age: 7 days
- Refresh on activity

**CSRF Protection:**
- State parameter in OAuth flow (random token)
- SameSite cookie attribute prevents cross-site attacks
- No CSRF tokens needed (stateless API with cookies)

### Audit Logs

**Agent Execution Log** (`services/api/app/models.py`):
```python
class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), unique=True)
    agent = Column(String(50), nullable=False)
    objective = Column(Text)
    params = Column(JSONB)
    status = Column(String(20))  # pending, running, completed, failed
    result = Column(JSONB)
    budget_used = Column(JSONB)  # {"ms": 1234, "ops": 5, "cost_cents": 12}
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
```

**Security Event Log** (`services/api/app/routers/security.py`):
```python
GET /security/events?limit=100
Response: [
  {
    "timestamp": "2025-10-18T10:30:00Z",
    "event_type": "email_quarantined",
    "email_id": 123,
    "risk_score": 75,
    "signals": ["DMARC_FAIL", "URL_MISMATCH"]
  },
  {
    "timestamp": "2025-10-18T10:35:00Z",
    "event_type": "email_released",
    "email_id": 123,
    "reviewer": "admin@applylens.com"
  }
]
```

**Policy Change Log** (`services/api/app/models_policy.py`):
```python
class PolicyBundle(Base):
    __tablename__ = "policy_bundles"
    
    id = Column(Integer, primary_key=True)
    version = Column(String(16), unique=True)  # Semantic versioning
    description = Column(Text)
    rules = Column(JSONB, nullable=False)
    state = Column(String(20), default="draft")
    signature = Column(Text)  # HMAC signature
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255))
    activated_at = Column(DateTime)
    activated_by = Column(String(255))
```

### Encryption

**OAuth Tokens:**
- Stored in PostgreSQL `oauth_state` table
- **TODO**: Implement field-level encryption (currently plain text)
- Tokens never exposed in API responses (server-side only)

**HMAC Secrets:**
- `HMAC_SECRET` environment variable
- Used for approval request signatures
- Rotated manually (no automatic rotation yet)

**At-Rest Encryption:**
- PostgreSQL: Relies on disk encryption (OS-level)
- Elasticsearch: No field-level encryption
- Secrets mounted as read-only volumes

### Privacy Considerations

**Data Collection:**
- Email metadata: sender, subject, date, labels (stored)
- Email body: Full text stored for search (not encrypted)
- OAuth tokens: Access/refresh tokens (plain text - needs encryption)
- User actions: Approval decisions, policy changes (audit logs)

**Data Retention:**
- Emails: Indefinite (no auto-deletion)
- Agent runs: Indefinite (audit trail)
- OAuth sessions: 7 days (refresh token valid longer)

**GDPR Compliance:**
- **TODO**: Implement right to erasure (delete all user data)
- **TODO**: Data export endpoint (download all data)
- No data shared with third parties (except Google for OAuth)
- User controls quarantine decisions

**Gmail API Permissions:**
- `gmail.readonly`: Read-only access (cannot send/delete)
- `userinfo.email`: User identification
- Tokens can be revoked by user at any time

---

**Continued in HACKATHON_REPORT_PART2C.md**
