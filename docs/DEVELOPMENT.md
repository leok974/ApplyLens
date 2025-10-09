# Development Guide

## Setup

1. Install dependencies
2. Configure environment variables
3. Run the development server

## Testing

### Telemetry + Behavior Learning (dev)
1. Ensure backend runs on `http://127.0.0.1:8001` and `ANALYTICS_ENABLED=true`.
2. Add `data-section="..."` to each major section and include:
   - `src/lib/behavior-tracker.js`
   - `src/lib/apply-learned-layout.js`
3. Click around locally, then:
   ```bash
   curl -X POST http://127.0.0.1:8001/agent/analyze/behavior
   curl http://127.0.0.1:8001/agent/layout
   ```
4. Run tests:
   ```bash
   pytest -q tests/test_metrics_learning.py
   npx playwright test tests/e2e/behavior-analytics.spec.ts --project=chromium
   ```

### Nightly Learning Job
- GitHub Actions workflow `behavior-learning-nightly.yml` runs daily at ~02:30 ET.
- It executes `scripts/analyze_behavior.py` which reads JSONL in `./data/analytics/`, updates `weights.json` if needed, and commits changes back to the repo.
- View your current metrics at `/metrics.html`.

### Privileged Panel Access
The Behavior Metrics dashboard is embedded under the privileged Admin panel.

- The guard is checked via `isPrivilegedUIEnabled()` in `src/lib/devGuard.ts`.
- To enable locally, use your existing unlock flow (e.g., query param, localStorage, or hotkey) as defined in `devGuard`.
- When unlocked, **AdminToolsPanel** renders the **Behavior Metrics** section with an iframe to `/metrics.html`.

## Contributing

[Your contributing guidelines]
