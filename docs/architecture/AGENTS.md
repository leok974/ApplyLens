# ApplyLens Agents

This repo uses **specialist agents** to keep changes focused, safe, and consistent with ApplyLens' architecture.

> ApplyLens: agentic job inbox + application tracker. Connects to Gmail (read-only OAuth), parses threads, labels risk/suspicion, powers search/suggestions, and tracks applications.

Each agent file under `.github/agents/` describes:

- **Persona** – what the agent is good at.
- **Project knowledge** – relevant folders, stacks, and what it can edit.
- **Commands** – concrete commands it may run.
- **Examples** – good vs bad changes.
- **Boundaries** – ✅ always, ⚠️ ask first, 🚫 never.

Use these files to guide GitHub Copilot Agents or any code assistant.
Pick the **most specific agent** for the task instead of a generalist.

---

## Available agents

### API agent – `api-agent.md`

**Scope:** FastAPI backend and data model.

- `services/api/` (routers, models, schemas).
- Alembic migrations (`services/api/alembic/`).
- Gmail ingest/backfill, risk scoring, applications CRUD, search/suggest endpoints.
- Read-only Gmail OAuth is **strict**: never send/modify mail.

Use when:

- Adding/modifying API routes.
- Changing schemas or serialization.
- Implementing new ingest/backfill logic.
- Wiring backend pieces for new UI features.

---

### Test agent – `test-agent.md`

**Scope:** All testing layers.

- Vitest unit tests (`apps/web/src/tests/*`).
- Playwright e2e (`apps/web/tests/e2e/*`).
- Pytest for API (`services/api/tests/*`).
- Contract tests and mocks for API/UI/search.

Use when:

- Adding tests for new features.
- Stabilizing flaky Playwright specs.
- Creating/adjusting pytest suites or fixtures.
- Writing contract tests between frontend and API.

---

### UI agent – `ui-agent.md`

**Scope:** ApplyLens web UI.

- React + Vite (`apps/web/`).
- Tailwind + shadcn/ui, Sonner toasts.
- Dark-first theme, soft low-contrast surfaces.
- Consistent `data-testid` usage and accessibility.

Use when:

- Adding or polishing UI flows.
- Implementing layouts, theme tweaks, or new components.
- Improving accessibility/legibility controls.

---

### Search agent – `search-agent.md`

**Scope:** Elasticsearch behavior.

- Index mappings and analyzers for `/api/search` and `/api/suggest`.
- Query boosts, decay functions, synonym sets, and typeahead.
- Relevance, ranking, and recall changes.

Use when:

- Tuning search relevance or suggest behavior.
- Adjusting analyzers/tokenizers.
- Adding new fields into search.

---

### Docs agent – `docs-agent.md`

**Scope:** Documentation.

- Runbooks, architecture, security, and deploy docs (`docs/`, `infra/`, etc.).
- Project roadmaps and design notes.
- Keep docs aligned with actual behavior and commands.

Use when:

- Updating docs after changes.
- Writing new runbooks or design overviews.
- Clarifying security or deployment stories.

---

### Dev/deploy agent – `dev-deploy-agent.md`

**Scope:** Dev environment + deployment docs.

- Docker Compose for dev and prod.
- Local dev workflows and smoke tests.
- Safe, incremental deploy diffs.

Use when:

- Improving local dev experience.
- Documenting or proposing deployment steps.
- Adding safe prod verification scripts.

> **Note:** This agent does **not** change Cloudflare Tunnel ingress, prod routing, or secrets without explicit approval.

---

### Security agent – `security-agent.md` (optional specialist)

**Scope:** Security posture and risk analysis.

- Auth flows (high-level), CSRF/cookies, headers.
- Risk scoring heuristics (SPF/DKIM/DMARC, URL checks, attachment rules).
- SSRF guards and blocklists.
- Security docs and UX around risk evidence.

Use when:

- Adding security checks or alerts.
- Improving risk evidence UX/observability.
- Reviewing code for security regressions.

---

## How to use these agents

When creating a new task or asking an assistant:

1. **Choose the right agent**
   - API work → `api-agent.md`
   - Search relevance → `search-agent.md`
   - UI/theme/layout → `ui-agent.md`
   - Tests-only work → `test-agent.md`, etc.

2. **Respect boundaries**
   - Follow the ✅ / ⚠️ / 🚫 rules in each file.
   - Especially **do not**:
     - Change Cloudflare Tunnel routes.
     - Modify OAuth scopes or token storage.
     - Relax risk/security checks.

3. **Prefer small, auditable changes**
   - Clear diffs.
   - Tests updated alongside behavior.
   - Docs updated when behavior changes.

These files are the **source of truth** for what an agent is allowed to do inside ApplyLens.
