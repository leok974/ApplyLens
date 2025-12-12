# CEO Walkthrough: ApplyLens Demo Script

**Purpose:** Executive demo guide for showcasing ApplyLens (screen-share friendly)

---

## 30-Second Opener

**Problem:** Job search creates inbox chaos and repetitive form filling. Candidates waste time tracking opportunities across email, spreadsheets, and memory.

**Solution:** ApplyLens is an AI copilot that triages job-related emails, tracks applications, and helps generate/auto-fill ATS answers using your resume profile.

**Impact:** It reduces busywork and helps you move faster while staying organized—focusing effort on high-fit opportunities instead of manual data entry.

---

## Demo Flow (7–10 minutes)

1. **Today** (2 min) — Daily command center (wow)
2. **Opportunities** (2 min) — Prioritization + role matching (value)
3. **Companion Extension** (3 min) — Scan → Generate → Preview → Autofill (hero)
4. **Settings → Resume** (2 min) — "How it works" source-of-truth profile

**Optional if asked:** Inbox, Search, Tracker, Security, Policy Studio

**Fast path (5 min):** Today → Companion → Opportunities

---

## Quick Reference One-Liners (use while screen sharing)

* **Today:** "Daily command center—AI surfaces follow-ups, interviews, deadlines."
* **Opportunities:** "AI scores roles vs my resume so I focus on high-fit jobs."
* **Companion:** "Scans the form, generates tailored answers, previewable + editable, then autofills."
* **Settings/Resume:** "Upload once → structured profile powers matching + autofill."
* **Inbox:** "Gmail threads labeled so you don't miss interviews."
* **Search:** "Find any recruiter/role instantly across months of emails."
* **Tracker:** "Pipeline view applied → interview → offer."

---

# Page Cheat Sheets

## 1) Today (`/today`)

**Purpose:** AI triage dashboard that groups email threads by intent (follow-ups, interviews, unsubscribe, etc.).

**Show:**

* Intent cards / action buckets
* A couple thread previews
* "This is what I need to do today" framing

**Value line:**
"Instead of scanning dozens of emails, the AI surfaces what needs action. It's like an assistant that reads your inbox and highlights the important stuff."

**(Optional tech note)**
Backend example: `POST /api/v2/agent/today` (agent analyzes recent window, returns summaries + threads)

---

## 2) Opportunities (`/opportunities`)

**Purpose:** Job tracking + role matching so you spend time on the best-fit roles.

**Show:**

* Buckets (Perfect / Strong / Possible / Skip)
* A role details view with "reasoning / matched skills" if available
* Batch scoring button if it's stable

**Value line:**
"Applying blindly wastes time. This helps prioritize roles where I'm strongest."

**(Optional tech note)**

* `GET /api/opportunities/list`
* `POST /api/agent/role-match` (single) / `/batch` (batch)

---

## 3) Companion Extension (`/extension/*`)

**Purpose:** Extension that scans ATS forms and generates tailored answers grounded in your resume profile.

**Show (best order):**

1. Open a job application page
2. **Scan Form** (field extraction)
3. **Generate Answers**
4. Show **preview/edit**
5. **Autofill** (user-driven)

**Value line (hero moment):**
"Instead of drafting answers from scratch, I scan → generate → review → autofill. It reduces repetitive work while keeping quality high because I can edit before submitting."

**(Optional tech note)**

* `GET /api/extension/profile/me`
* `POST /api/extension/generate-form-answers` → returns `{field_id: answer}` map
* `POST /api/extension/applications` → logs/submits tracking

---

## 4) Settings → Resume (`/settings`)

**Purpose:** Resume upload + profile extraction that becomes the "source of truth" for the whole system.

**Show:**

* Upload area
* "Parsed/Active" status
* Extracted skills/roles/projects
* Switching active resume version (if you have it)

**Value line:**
"Upload once → structured profile powers matching + extension autofill. Update the resume and everything downstream stays current."

**(Optional tech note)**

* `POST /api/resume/upload` (extracts structured profile)
* `GET /api/resume/current` / `GET /api/resume/all` / `POST /api/resume/activate/{id}`

---

# Optional Pages (only if asked)

## Inbox (`/inbox`)

**Purpose:** Gmail-integrated thread browser with AI labels + quick actions.
**Value line:** "Interview invites and time-sensitive threads are labeled so nothing gets missed."

## Search (`/search`)

**Purpose:** Elasticsearch-powered retrieval across email history.
**Value line:** "Find any recruiter thread or role instantly—even if you don't remember exact keywords."

## Tracker (`/tracker`)

**Purpose:** Pipeline view (Applied → Interview → Offer).
**Value line:** "At-a-glance visibility into the whole pipeline."

## Settings → Security (`/settings/security`)

**Purpose:** OAuth/session status, reconnect/revoke controls.
**Value line:** "OAuth-based access, no password storage, revoke anytime."

## Policy Studio (`/policy-studio`)

**Purpose:** Advanced guardrails/rules.
**Value line:** "Extensible automation with controls—not a black box."

---

# Technical Architecture (1-minute version)

* **Frontend:** React + TypeScript + Tailwind + shadcn/ui
* **Backend:** FastAPI (Python)
* **Data:** PostgreSQL (source of truth) + Elasticsearch (search)
* **AI:** LLM used for resume parsing, form answers, and role matching (with careful prompting + guardrails)
* **Auth:** Gmail OAuth 2.0 + session cookies
* **Extension:** Chrome MV3 (content scripts + sidepanel)

**Data Flow (tell it like this):**
Resume → structured profile → powers matching + autofill
Gmail → normalized threads → searchable + triaged → actions + tracking

---

# Backup Plan (if something breaks)

* **If Gmail OAuth fails:** Use pre-seeded/demo data; narrate "in prod you connect Gmail in ~30 seconds."
* **If Extension fails:** Show a short video/screenshot + show the API response (JSON) as proof.
* **If LLM is slow:** Narrate what it's doing; optionally pre-generate one example in advance.

---

# CEO FAQ (safe answers)

**How accurate is matching?**
"It's a hybrid approach: heuristics + LLM scoring + user feedback. The goal is useful prioritization, not perfect prediction."

**What if the AI generates wrong answers?**
"User stays in control—everything is previewable and editable before autofill."

**How do you handle privacy?**
"OAuth-based Gmail access; no password storage. Users can revoke access and delete data. I'm conservative with sensitive data handling."

**How do you keep costs reasonable?**
"LLM calls are the variable cost. I reduce cost with caching, batching, and using smaller models when possible."

---

# 7-Minute Verbatim Demo Script

**[Open `/today`]**
"ApplyLens turns job search chaos into a daily action list."

**[Point to Today buckets]**
"This shows what matters: follow-ups, interviews, and time-sensitive threads—my command center."

**[Go to `/opportunities`]**
"This prioritizes roles against my resume profile so I focus on high-fit jobs."

**[Open job app + Companion]**
"This is the hero feature. I scan the form and job context… generate tailored answers grounded in my profile… preview/edit… then autofill. It reduces repetitive work without going autopilot."

**[Go to Settings → Resume]**
"This is the source of truth. Upload once → structured profile powers matching + autofill. Updating it keeps everything downstream current."

**Close:**
"The point isn't to mass-apply—it's to reduce repetitive work and stay organized so you apply to the right roles with high quality."
