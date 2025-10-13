# Security UI - Quick Start Guide

## For Frontend Developers

### Using the Components

#### 1. Display Risk Badge in Email List

```typescript
import { RiskBadge } from "@/components/security/RiskBadge";

// In your email list item component:
<div className="email-item">
  <span>{email.subject}</span>
  {email.risk_score !== undefined && (
    <RiskBadge score={email.risk_score} quarantined={email.quarantined} />
  )}
</div>
```

#### 2. Add Security Panel to Email Details

```typescript
import { SecurityPanel } from "@/components/security/SecurityPanel";

// In your email details view:
<div className="email-details">
  <h1>{email.subject}</h1>
  <div>{email.body}</div>
  
  {email.risk_score !== undefined && (
    <SecurityPanel
      emailId={email.id}
      riskScore={email.risk_score}
      quarantined={email.quarantined}
      flags={email.flags}
      onRefresh={() => {
        // Refetch email data after rescan
        refetchEmail(email.id);
      }}
    />
  )}
</div>
```

#### 3. Add Security Settings Page

Already implemented at `/settings/security` route!

```typescript
// Just navigate users to:
<Link to="/settings/security">Security Settings</Link>
```

---

## For Backend Developers

### Required API Endpoints

#### 1. Email Security Data (ALREADY IMPLEMENTED ✅)

Your email API responses should include:

```json
{
  "id": "123",
  "subject": "Important Email",
  "from": "sender@example.com",
  "risk_score": 55,
  "quarantined": false,
  "flags": [
    {
      "signal": "DMARC_FAIL",
      "evidence": "auth=fail",
      "weight": 25
    },
    {
      "signal": "SPF_FAIL",
      "evidence": "ip=1.2.3.4",
      "weight": 15
    }
  ]
}
```

**Endpoints that should return this:**
- `GET /api/search/` → Array of emails with security data
- `GET /api/emails/` → Array of emails with security data
- `GET /api/search/by_id/{id}` → Single email with security data

#### 2. Rescan Endpoint (ALREADY IMPLEMENTED ✅)

```python
@router.post("/security/rescan/{email_id}")
def rescan_email(email_id: str, db: Session = Depends(get_db)):
    """Re-analyze email security."""
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Run security analysis
    analyzer = get_security_analyzer()
    result = analyzer.analyze(...)
    
    # Update database
    email.risk_score = result.risk_score
    email.flags = [f.dict() for f in result.flags]
    email.quarantined = result.quarantined
    db.commit()
    
    return {
        "status": "ok",
        "email_id": email_id,
        "risk_score": result.risk_score,
        "quarantined": result.quarantined,
        "flags": result.flags
    }
```

#### 3. Security Stats Endpoint (ALREADY IMPLEMENTED ✅)

```python
@router.get("/security/stats")
def get_security_stats(db: Session = Depends(get_db)):
    """Get aggregate security statistics."""
    quarantined = db.query(func.count(Email.id)).filter(Email.quarantined == True).scalar() or 0
    average_risk = db.query(func.avg(Email.risk_score)).filter(Email.risk_score.isnot(None)).scalar()
    average_risk = float(average_risk) if average_risk is not None else 0.0
    high_risk = db.query(func.count(Email.id)).filter(Email.risk_score >= 50).scalar() or 0
    
    return {
        "total_quarantined": quarantined,
        "average_risk_score": average_risk,
        "high_risk_count": high_risk
    }
```

#### 4. Policy Endpoints (TODO - NEEDS IMPLEMENTATION ⚠️)

**GET /api/policy/security**

```python
@router.get("/policy/security")
def get_security_policies(db: Session = Depends(get_db)):
    """Fetch security policy configuration."""
    # Option 1: Fetch from database
    policy = db.query(SecurityPolicy).first()
    if not policy:
        # Return defaults
        return {
            "autoQuarantineHighRisk": True,
            "autoArchiveExpiredPromos": True,
            "autoUnsubscribeInactive": {
                "enabled": False,
                "threshold": 10
            }
        }
    
    return {
        "autoQuarantineHighRisk": policy.auto_quarantine_high_risk,
        "autoArchiveExpiredPromos": policy.auto_archive_expired_promos,
        "autoUnsubscribeInactive": {
            "enabled": policy.auto_unsubscribe_enabled,
            "threshold": policy.auto_unsubscribe_threshold
        }
    }
```

**PUT /api/policy/security**

```python
@router.put("/policy/security")
def save_security_policies(
    policies: SecurityPoliciesInput,
    db: Session = Depends(get_db)
):
    """Save security policy configuration."""
    policy = db.query(SecurityPolicy).first()
    if not policy:
        policy = SecurityPolicy()
        db.add(policy)
    
    policy.auto_quarantine_high_risk = policies.autoQuarantineHighRisk
    policy.auto_archive_expired_promos = policies.autoArchiveExpiredPromos
    policy.auto_unsubscribe_enabled = policies.autoUnsubscribeInactive.enabled
    policy.auto_unsubscribe_threshold = policies.autoUnsubscribeInactive.threshold
    
    db.commit()
    
    # Optional: Trigger background job to apply policies
    # apply_policies_to_existing_emails.delay()
    
    return {"status": "ok"}
```

**Create the Pydantic models:**

```python
from pydantic import BaseModel

class AutoUnsubscribeConfig(BaseModel):
    enabled: bool
    threshold: int

class SecurityPoliciesInput(BaseModel):
    autoQuarantineHighRisk: bool
    autoArchiveExpiredPromos: bool
    autoUnsubscribeInactive: AutoUnsubscribeConfig
```

**Create the database model:**

```python
# In alembic migration or models.py
class SecurityPolicy(Base):
    __tablename__ = "security_policies"
    
    id = Column(Integer, primary_key=True)
    auto_quarantine_high_risk = Column(Boolean, default=True)
    auto_archive_expired_promos = Column(Boolean, default=True)
    auto_unsubscribe_enabled = Column(Boolean, default=False)
    auto_unsubscribe_threshold = Column(Integer, default=10)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## Testing

### Run E2E Tests

```bash
cd apps/web
pnpm exec playwright test tests/security-ui.spec.ts
```

### Manual Testing Checklist

1. **Email List**
   - [ ] Open `/search` or `/inbox-polished`
   - [ ] Verify risk badges appear on emails with `risk_score`
   - [ ] Check badge colors (red ≥80, amber 40-79, green <40)

2. **Email Details**
   - [ ] Click on an email
   - [ ] Security panel should appear (if email has risk_score)
   - [ ] Click "Why flagged?" → Evidence modal opens
   - [ ] Click "Rescan" → Loading state → Success toast

3. **Security Settings**
   - [ ] Navigate to `/settings/security`
   - [ ] Toggle switches work
   - [ ] Number input for threshold works
   - [ ] Save button triggers toast

4. **Dark Mode**
   - [ ] Toggle dark mode
   - [ ] All colors display correctly
   - [ ] Badges are readable
   - [ ] Modals have proper contrast

---

## Common Issues & Solutions

### Issue: Risk badges not showing

**Solution:** Make sure your API returns `risk_score` in the email object:

```typescript
// Check in browser console:
console.log(email.risk_score); // Should be a number
```

### Issue: SecurityPanel not appearing

**Cause:** SecurityPanel only renders if `risk_score !== undefined`

**Solution:** Ensure API includes `risk_score` field (can be 0)

### Issue: Rescan button doesn't work

**Possible causes:**
1. API endpoint not implemented
2. CORS issues (use `credentials: "include"`)
3. Email ID format mismatch (string vs number)

**Debug:**
```typescript
// Check network tab in browser DevTools
// POST /api/security/rescan/{id} should return 200
```

### Issue: Policy save fails with 404

**Cause:** Backend policy endpoints not implemented yet

**Solution:** Implement the endpoints above or use frontend with defaults (already handled gracefully)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                    │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  EmailList    │  │ EmailDetails │  │   Settings   │ │
│  │  (RiskBadge)  │  │ (Security    │  │   Security   │ │
│  │               │  │  Panel)      │  │  (Policy     │ │
│  │               │  │              │  │   Panel)     │ │
│  └───────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│          │                 │                  │          │
│          └─────────────────┴──────────────────┘          │
│                            │                             │
│                    ┌───────▼────────┐                    │
│                    │  securityApi   │                    │
│                    │  - rescan()    │                    │
│                    │  - getStats()  │                    │
│                    │  - getPolicies│                    │
│                    └───────┬────────┘                    │
└────────────────────────────┼──────────────────────────────┘
                             │
                             │ HTTP/JSON
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                     │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │          /api/security/* endpoints                  │ │
│  │  - POST /rescan/{id}  ✅                           │ │
│  │  - GET /stats         ✅                           │ │
│  ├────────────────────────────────────────────────────┤ │
│  │          /api/policy/* endpoints                    │ │
│  │  - GET /security      ⚠️ TODO                      │ │
│  │  - PUT /security      ⚠️ TODO                      │ │
│  └───────────────┬────────────────────────────────────┘ │
│                  │                                        │
│          ┌───────▼─────────┐                            │
│          │ EmailRiskAnalyzer│                            │
│          │ - analyze()      │                            │
│          │ - 12 detections  │                            │
│          └───────┬──────────┘                            │
│                  │                                        │
└──────────────────┼─────────────────────────────────────┘
                   │
                   ▼
         ┌──────────────────┐
         │   PostgreSQL DB   │
         │  - emails table   │
         │    * risk_score   │
         │    * quarantined  │
         │    * flags (JSONB)│
         └───────────────────┘
```

---

## Performance Tips

### 1. Optimize Large Lists

If you have 1000+ emails with risk badges:

```typescript
import { memo } from 'react';

// Memoize the EmailRow component
export const EmailRow = memo(function EmailRow(props) {
  // ... component code
});
```

### 2. Lazy Load Evidence Modal

Already implemented! The modal only mounts when opened.

### 3. Cache Policy Data

```typescript
// In PolicyPanel component, add localStorage cache:
React.useEffect(() => {
  const cached = localStorage.getItem('security-policies');
  if (cached) {
    setPol(JSON.parse(cached));
  }
  getPolicies().then(p => {
    setPol(p);
    localStorage.setItem('security-policies', JSON.stringify(p));
  });
}, []);
```

### 4. Debounce Policy Input

```typescript
import { useDebouncedCallback } from 'use-debounce';

const debouncedSave = useDebouncedCallback(
  () => savePolicies(pol),
  1000
);
```

---

## Customization Examples

### Change Risk Level Thresholds

Edit `RiskBadge.tsx`:

```typescript
// Change from 80/40 to 70/30:
const level = score >= 70 ? "high" : score >= 30 ? "med" : "low";
```

### Add More Policy Options

Edit `PolicyPanel.tsx`:

```typescript
// Add new toggle:
<div className="flex items-center justify-between">
  <Label htmlFor="autoBlockSuspicious">Auto-block suspicious senders</Label>
  <Switch id="autoBlockSuspicious" checked={pol.autoBlockSuspicious}
          onCheckedChange={(v)=>update("autoBlockSuspicious", v)} />
</div>
```

Update types in `security.ts`:

```typescript
export type SecurityPolicies = {
  autoQuarantineHighRisk: boolean;
  autoArchiveExpiredPromos: boolean;
  autoUnsubscribeInactive: { enabled: boolean; threshold: number };
  autoBlockSuspicious: boolean; // New!
};
```

### Change Badge Colors

Edit `RiskBadge.tsx`:

```typescript
// Use your brand colors:
const color =
  level === "high" ? "bg-purple-500/20 text-purple-300 border-purple-600/40" :
  level === "med"  ? "bg-blue-500/20 text-blue-300 border-blue-600/40" :
                     "bg-green-500/20 text-green-300 border-green-600/40";
```

---

## Next Steps

1. ✅ Security UI is ready to use!
2. ⚠️ Implement policy backend endpoints (optional, has defaults)
3. 🚀 Deploy to production
4. 📊 Monitor user feedback
5. 🔄 Iterate based on usage patterns

For questions, see `SECURITY_UI_IMPLEMENTATION.md` for full documentation.
