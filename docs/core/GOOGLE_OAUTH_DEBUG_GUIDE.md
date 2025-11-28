# ApplyLens – Google OAuth Debugging Guide

This document explains how to debug and verify the **Google OAuth** configuration for ApplyLens in production
(e.g. when `/auth/google/login` or `/api/auth/google/login` returns `{"detail": "Google OAuth not configured"}`).

It also defines guardrails to prevent this class of outage from happening again.

---

## 0. Guardrails & Invariants ✅

These are the **non-negotiables** for ApplyLens Google OAuth:

1. **Use the `APPLYLENS_` prefix for AgentSettings**

   The backend uses an `AgentSettings` Pydantic settings class with an `env_prefix` of `APPLYLENS_`.
   That means the **canonical env vars** are:

   ```env
   APPLYLENS_GOOGLE_CLIENT_ID=...
   APPLYLENS_GOOGLE_CLIENT_SECRET=...
   APPLYLENS_OAUTH_REDIRECT_URI=https://applylens.app/api/auth/google/callback
   APPLYLENS_GMAIL_OAUTH_SECRETS_PATH=/secrets/google.json
   APPLYLENS_GMAIL_OAUTH_TOKEN_PATH=/secrets/google-token.json
   ```

   Unprefixed envs (e.g. `GOOGLE_CLIENT_ID`) will **not** be read by `AgentSettings`.

   You can keep unprefixed vars for other parts of the app if needed, but do not rely on them for the OAuth agent.

2. **Never assume "env is set" → "settings sees it"**

   Always verify via `agent_settings` (see Section 2).

   **Guardrail:** when changing env names or prefixes, update this doc and add/adjust tests.

3. **Avoid logging secrets**

   When printing settings for debugging, only log whether secrets are set, not the full value (truncate or use "SET").

4. **Contract test: `/auth/google/login` must redirect**

   In a prod-like environment with valid `APPLYLENS_*` vars set, `/auth/google/login` should return 302/307 to Google.

   Keep at least one automated test (pytest or a small smoke script) that asserts this behavior.

5. **File paths must be container paths**

   Any credentials file path must use the container path (e.g. `/secrets/google.json`), not the host path (`D:\...`).

---

## 1. TL;DR – Quick Checklist

When Google login is broken but the API is healthy, check these in order:

1. **API is running and reachable**

   ```bash
   curl -i http://localhost:8003/healthz
   # Expect: HTTP/1.1 200 OK
   ```

2. **Nginx routing is correct**

   ```nginx
   # in applylens.prod.conf

   location = /api/auth/google/login {
       proxy_pass http://applylens-api:8000/auth/google/login;
   }

   location = /api/auth/google/callback {
       proxy_pass http://applylens-api:8000/auth/google/callback;
   }
   ```

3. **AgentSettings actually sees the Google env vars**
   (via `agent_settings`, not just `docker env` – see section 2).

4. **The guard condition that raises "Google OAuth not configured" is satisfied.**

5. **Redirect URI matches what's configured in Google Cloud Console.**

---

## 2. Inspect `agent_settings` inside the API container

The error "Google OAuth not configured" means the backend's config guard decided something is missing.

To see what the app **really** thinks is configured, run this from the host:

```powershell
docker exec -it applylens-api-prod python - << 'PY'
from app.config import agent_settings  # AgentSettings instance

fields = [
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "OAUTH_REDIRECT_URI",
    "GMAIL_OAUTH_SECRETS_PATH",
    "GMAIL_OAUTH_TOKEN_PATH",
]

for name in fields:
    val = getattr(agent_settings, name, None)
    if name == "GOOGLE_CLIENT_SECRET" and val:
        val = "SET"  # do not print secret
    print(f"{name:24} -> {val!r}")
PY
```

**Interpret the output:**

- `None` or `''` → that field is effectively missing.
- `"SET"` for `GOOGLE_CLIENT_SECRET` → secret is present.
- Paths like `GMAIL_OAUTH_SECRETS_PATH` must be valid container paths (e.g. `/secrets/google.json`).

**Guardrail:** Always use `agent_settings`, not a generic `settings` object, for OAuth config checks.

---

## 3. Confirm the `APPLYLENS_` env prefix

`AgentSettings` is a Pydantic `BaseSettings` with an `env_prefix` of `APPLYLENS_`.
That means:

- Field `GOOGLE_CLIENT_ID` → reads from env `APPLYLENS_GOOGLE_CLIENT_ID`
- Field `GOOGLE_CLIENT_SECRET` → reads from `APPLYLENS_GOOGLE_CLIENT_SECRET`
- Field `OAUTH_REDIRECT_URI` → reads from `APPLYLENS_OAUTH_REDIRECT_URI`
- Field `GMAIL_OAUTH_SECRETS_PATH` → reads from `APPLYLENS_GMAIL_OAUTH_SECRETS_PATH`
- Field `GMAIL_OAUTH_TOKEN_PATH` → reads from `APPLYLENS_GMAIL_OAUTH_TOKEN_PATH`

You can verify the prefix quickly:

```powershell
docker exec applylens-api-prod python - << 'PY'
from app.config import AgentSettings
import inspect

print(inspect.getsource(AgentSettings)[:1000])
PY
```

Look for a docstring or inner `Config` / `model_config` mentioning `env_prefix = "APPLYLENS_"`.

**Guardrail:** If you ever change the `env_prefix`, you must:

1. Update this doc.
2. Update `.env.prod`.
3. Add/update tests that assert the new mapping.

---

## 4. Align `.env.prod` with what `AgentSettings` expects

### Canonical production envs (container perspective)

In `infra/.env.prod`, you should have:

```env
# AgentSettings (env_prefix="APPLYLENS_")
APPLYLENS_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
APPLYLENS_GOOGLE_CLIENT_SECRET=your-super-secret
APPLYLENS_OAUTH_REDIRECT_URI=https://applylens.app/api/auth/google/callback

# If you use local token/credentials files
APPLYLENS_GMAIL_OAUTH_SECRETS_PATH=/secrets/google.json
APPLYLENS_GMAIL_OAUTH_TOKEN_PATH=/secrets/google-token.json
```

And in the Docker run / Compose definition:

```powershell
-v D:\ApplyLens\infra\secrets:/secrets:ro
```

This ensures that:

- `/secrets/google.json` and `/secrets/google-token.json` exist inside the container.
- `agent_settings.GMAIL_OAUTH_SECRETS_PATH` and `.GMAIL_OAUTH_TOKEN_PATH` point to valid files.

You can keep unprefixed vars (e.g. `GOOGLE_CLIENT_ID`) if other components need them, but `AgentSettings` relies on the `APPLYLENS_` versions.

### After editing `.env.prod`, restart the API:

```powershell
docker rm -f applylens-api-prod

docker run -d `
  --name applylens-api-prod `
  --restart unless-stopped `
  --network applylens_applylens-prod `
  --env-file .env.prod `
  -p 8003:8000 `
  -v D:\ApplyLens\infra\secrets:/secrets:ro `
  leoklemet/applylens-api:0.6.0-phase5-fixed `
  uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then rerun the `agent_settings` inspection (Section 2) and confirm all fields are non-empty / correct.

---

## 5. Verify behavior locally and via nginx

### Direct to API (bypassing nginx / tunnel):

```bash
curl -i http://localhost:8003/auth/google/login
```

**Expected:**

- `HTTP/1.1 302 Found` or `307 Temporary Redirect`
- `Location: https://accounts.google.com/...`
  with the correct client, scopes, and redirect URI.

### Through nginx + Cloudflare:

```bash
curl -i https://applylens.app/api/auth/google/login
```

**Expected:** same 302/307 + `Location` header to Google.

When both are good, the "Connect Gmail" button in ApplyLens should redirect to Google's consent screen.

**Guardrail:** add a small smoke test or CI job that asserts `/auth/google/login` returns a redirect when `APPLYLENS_*` envs are present.

---

## 6. Common pitfalls

1. **Using unprefixed env vars only**

   Setting `GOOGLE_CLIENT_ID` but not `APPLYLENS_GOOGLE_CLIENT_ID` means `agent_settings.GOOGLE_CLIENT_ID` will be `None`.

   **Fix:** always set the `APPLYLENS_`-prefixed versions.

2. **File paths using host paths**

   `D:\ApplyLens\infra\secrets\google.json` will not work inside the container.

   Use `/secrets/google.json` and mount the host directory to `/secrets`.

3. **Redirect URI mismatch with Google Cloud Console**

   `APPLYLENS_OAUTH_REDIRECT_URI` must match exactly what's in:

   **Google Cloud Console** → APIs & Services → Credentials → OAuth 2.0 Client IDs → Authorized redirect URIs

   For prod ApplyLens this should be:

   ```
   https://applylens.app/api/auth/google/callback
   ```

4. **Secrets printed to logs**

   Never log full client secrets or tokens.

   Use `"SET"`, or a truncated version, in debug prints.

---

## 7. Optional: add more explicit misconfiguration logs

To make future debugging easier, you can wrap the config guard with explicit logging (without leaking secrets), for example:

```python
import logging
from fastapi import HTTPException, status
from app.config import agent_settings

logger = logging.getLogger(__name__)

def ensure_google_oauth_configured() -> None:
    problems = []
    if not agent_settings.GOOGLE_CLIENT_ID:
        problems.append("missing GOOGLE_CLIENT_ID")
    if not agent_settings.GOOGLE_CLIENT_SECRET:
        problems.append("missing GOOGLE_CLIENT_SECRET")
    if not agent_settings.OAUTH_REDIRECT_URI:
        problems.append("missing OAUTH_REDIRECT_URI")
    if not agent_settings.GMAIL_OAUTH_SECRETS_PATH:
        problems.append("missing GMAIL_OAUTH_SECRETS_PATH")
    if not agent_settings.GMAIL_OAUTH_TOKEN_PATH:
        problems.append("missing GMAIL_OAUTH_TOKEN_PATH")

    if problems:
        logger.error("Google OAuth misconfigured: %s", ", ".join(problems))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth not configured",
        )
```

Then check:

```powershell
docker logs applylens-api-prod | Select-String "Google OAuth misconfigured"
```

for a clear explanation of what's wrong.

---

## 8. Minimal "Is OAuth actually configured?" checklist

Use this mini checklist whenever you see "Google OAuth not configured":

- [ ] `curl http://localhost:8003/healthz` → 200
- [ ] `curl http://localhost:8003/auth/google/login` → 302/307 to `accounts.google.com`
- [ ] `curl https://applylens.app/api/auth/google/login` → 302/307 to `accounts.google.com`
- [ ] `agent_settings.GOOGLE_CLIENT_ID` non-empty
- [ ] `agent_settings.GOOGLE_CLIENT_SECRET` is "SET" in debug output
- [ ] `agent_settings.OAUTH_REDIRECT_URI` matches Google Console redirect URI
- [ ] `agent_settings.GMAIL_OAUTH_SECRETS_PATH` and `GMAIL_OAUTH_TOKEN_PATH` are valid container paths
- [ ] `APPLYLENS_*` envs present in `.env.prod` and match `AgentSettings` expectations

If all of the above are ✅, ApplyLens Google OAuth should be fully functional in production.
