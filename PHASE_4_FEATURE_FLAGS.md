# Phase 4 AI Feature Flags

## Overview

Feature flags allow you to control which Phase 4 AI features are visible in the UI. This enables:
- **Progressive rollout**: Enable features for testing without affecting production
- **A/B testing**: Show features to specific user segments
- **Emergency rollback**: Quickly disable features if issues arise
- **Environment-specific configuration**: Different settings for dev, staging, production

## Available Flags

| Flag | Purpose | Default (Dev) | Default (Prod) |
|------|---------|---------------|----------------|
| `VITE_FEATURE_SUMMARIZE` | Email thread summarization with Ollama | ✅ `1` | ❌ `0` |
| `VITE_FEATURE_RISK_BADGE` | Smart risk scoring with security signals | ✅ `1` | ❌ `0` |
| `VITE_FEATURE_RAG_SEARCH` | RAG-powered semantic search | ✅ `1` | ❌ `0` |
| `VITE_DEMO_MODE` | Demo mode indicator and seeded data | ✅ `1` | ❌ `0` |

## Configuration Files

### Development (.env.local)
```bash
# Local development with all features enabled
VITE_API_BASE=http://localhost:8003
VITE_FEATURE_SUMMARIZE=1
VITE_FEATURE_RISK_BADGE=1
VITE_FEATURE_RAG_SEARCH=1
VITE_DEMO_MODE=1
```

### Docker (.env.docker)
```bash
# Docker environment with features disabled by default
VITE_API_BASE=http://api:8003
VITE_FEATURE_SUMMARIZE=0
VITE_FEATURE_RISK_BADGE=0
VITE_FEATURE_RAG_SEARCH=0
VITE_DEMO_MODE=0
```

### Production (.env.production)
```bash
# Production with features disabled until ready
VITE_API_BASE=https://api.applylens.io
VITE_FEATURE_SUMMARIZE=0
VITE_FEATURE_RISK_BADGE=0
VITE_FEATURE_RAG_SEARCH=0
VITE_DEMO_MODE=0
```

## Usage in Components

### Import the flags helper
```tsx
import { FLAGS } from '@/lib/flags';
```

### Conditional rendering
```tsx
export default function EmailDetail({ email }) {
  return (
    <div>
      <EmailHeader email={email} />
      
      {/* Only show if flag is enabled */}
      {FLAGS.SUMMARIZE && (
        <SummaryCard threadId={email.thread_id} />
      )}
      
      {FLAGS.RISK_BADGE && (
        <RiskPopover messageId={email.id} />
      )}
      
      <EmailBody email={email} />
    </div>
  );
}
```

### Helper functions
```tsx
import { FLAGS, hasAnyAIFeatures, getEnabledFeatures } from '@/lib/flags';

// Check if any AI features are enabled
if (hasAnyAIFeatures()) {
  console.log('AI features available');
}

// Get list of enabled feature names
const features = getEnabledFeatures();
// Example output: ['Summarize', 'Risk Badge', 'Demo Mode']
```

## Testing

### Unit/Integration Tests
```tsx
// Mock flags in tests
jest.mock('@/lib/flags', () => ({
  FLAGS: {
    SUMMARIZE: true,
    RISK_BADGE: false,
    RAG_SEARCH: true,
    DEMO_MODE: false,
  },
}));

test('shows summary when flag enabled', () => {
  render(<EmailDetail email={mockEmail} />);
  expect(screen.getByTestId('summary-card')).toBeInTheDocument();
});
```

### Playwright E2E Tests
```tsx
test('features hidden when flags disabled', async ({ page }) => {
  // Simulate flags at runtime
  await page.addInitScript(() => {
    (window as any).import = {
      meta: {
        env: {
          VITE_FEATURE_SUMMARIZE: '0',
          VITE_FEATURE_RISK_BADGE: '0',
          VITE_FEATURE_RAG_SEARCH: '0',
        },
      },
    };
  });
  
  await page.goto('/demo-ai');
  await expect(page.getByTestId('summary-card')).toHaveCount(0);
});
```

Run the flag tests:
```bash
cd apps/web
npx playwright test ai-flags.spec.ts
```

## Rollout Strategy

### Phase 1: Internal Testing
```bash
# .env.local (developers only)
VITE_FEATURE_SUMMARIZE=1
VITE_FEATURE_RISK_BADGE=1
VITE_FEATURE_RAG_SEARCH=1
```

### Phase 2: Staging/Beta
```bash
# .env.docker (staging environment)
VITE_FEATURE_SUMMARIZE=1  # Ready for testing
VITE_FEATURE_RISK_BADGE=1  # Ready for testing
VITE_FEATURE_RAG_SEARCH=0  # Still in development
```

### Phase 3: Gradual Production Rollout
```bash
# .env.production - Week 1
VITE_FEATURE_SUMMARIZE=1  # Enable first feature
VITE_FEATURE_RISK_BADGE=0  # Wait for user feedback
VITE_FEATURE_RAG_SEARCH=0

# .env.production - Week 2
VITE_FEATURE_SUMMARIZE=1
VITE_FEATURE_RISK_BADGE=1  # Enable second feature
VITE_FEATURE_RAG_SEARCH=0

# .env.production - Week 3
VITE_FEATURE_SUMMARIZE=1
VITE_FEATURE_RISK_BADGE=1
VITE_FEATURE_RAG_SEARCH=1  # Enable all features
```

## Emergency Rollback

If an issue is discovered in production:

1. **Quick disable** - Update environment variable:
   ```bash
   # Disable problematic feature immediately
   VITE_FEATURE_SUMMARIZE=0
   ```

2. **Redeploy** or **Restart** the web service:
   ```bash
   docker-compose restart web
   ```

3. **Investigate** the issue while users are unaffected

4. **Re-enable** once fixed and tested

## Best Practices

### ✅ Do:
- Keep flags disabled in production until thoroughly tested
- Use meaningful flag names that describe the feature
- Document why a flag exists and when it can be removed
- Test both enabled and disabled states
- Use flags for gradual rollouts
- Remove flags after features are stable (avoid flag debt)

### ❌ Don't:
- Use flags for permanent configuration (use config files instead)
- Create too many nested flag conditions (hard to reason about)
- Forget to test the disabled state
- Leave old flags in code after features are stable
- Use flags for business logic (only for UI visibility)

## Monitoring

Track feature flag usage:

```tsx
// Track when features are used
import { FLAGS } from '@/lib/flags';

if (FLAGS.SUMMARIZE) {
  analytics.track('feature_available', { feature: 'summarize' });
}

// Track actual usage
const handleSummarize = () => {
  analytics.track('feature_used', { feature: 'summarize' });
  // ... summarize logic
};
```

## Future Enhancements

Potential improvements:
- [ ] User-specific flags (enable for beta testers)
- [ ] Percentage-based rollouts (show to 10% of users)
- [ ] Time-based flags (enable during specific hours)
- [ ] Remote flag management (LaunchDarkly, Split.io)
- [ ] Flag override UI for admins

## File Structure

```
apps/web/
├── .env.example          # Example configuration
├── .env.local            # Local development (git-ignored)
├── .env.docker           # Docker environment
├── .env.production       # Production environment
├── src/
│   ├── lib/
│   │   └── flags.ts      # Feature flag definitions
│   ├── pages/
│   │   └── DemoAI.tsx    # Uses FLAGS
│   └── components/
│       ├── ai/
│       │   └── SummaryCard.tsx
│       ├── security/
│       │   └── RiskPopover.tsx
│       └── rag/
│           └── RagResults.tsx
└── tests/
    └── ai-flags.spec.ts  # Flag behavior tests
```

## Troubleshooting

### Feature not showing despite flag being enabled

1. **Check environment file**:
   ```bash
   cat .env.local
   # Verify VITE_FEATURE_SUMMARIZE=1
   ```

2. **Restart dev server** (Vite needs restart for env changes):
   ```bash
   npm run dev
   ```

3. **Clear browser cache** or hard refresh (Ctrl+Shift+R)

4. **Check browser console** for import errors

### Flag changes not taking effect

Vite only reads `.env` files at build/startup time. You must:
- **Development**: Restart `npm run dev`
- **Production**: Rebuild with `npm run build`
- **Docker**: Rebuild image with `docker-compose build web`

### Tests failing with flag mismatches

Ensure test environment matches expected flag state:
```tsx
// Set flags explicitly in test setup
process.env.VITE_FEATURE_SUMMARIZE = '1';
```

## Related Documentation

- [PHASE_4_FRONTEND_INTEGRATION.md](./PHASE_4_FRONTEND_INTEGRATION.md) - Component integration guide
- [PHASE_4_TEST_RESULTS.md](./PHASE_4_TEST_RESULTS.md) - Backend test results
- [INFRASTRUCTURE_STATUS.md](./INFRASTRUCTURE_STATUS.md) - System architecture

---

**Status**: ✅ Feature flags implemented and ready for use

**Last Updated**: October 20, 2025
