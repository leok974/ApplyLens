# Phase 5.4 Progress Report - PRs 1-2 Complete

## ✅ Completed: Incident Tracking & Auto-Issue Creation

### PR1: Invariant Watcher & Incident Model (Commit: aee5848)
**Status: Committed**

#### Components
- **Models** (`app/models_incident.py`): Incident & IncidentAction with 5-state lifecycle
- **Watcher** (`app/intervene/watcher.py`): Background service detecting failures
- **Router** (`app/routers/incidents.py`): REST API with 11 endpoints
- **Migration** (`alembic/versions/0016_incidents.py`): Database schema
- **Tests** (`tests/test_incident_lifecycle.py`): 13 comprehensive tests
- **Integration**: Scheduler job running every 15 minutes

#### Features
- Deduplication (max 1 open incident per key)
- Rate limiting (max 3 incidents/hour per key)
- Severity mapping (priority → sev1-4)
- State machine (open → ack → mitigate → resolve → close)
- 3 incident kinds: invariant, budget, planner

**Lines Added**: ~1,257

---

### PR2: Issue Openers (GitHub/GitLab/Jira) (Commit: 130a564)
**Status: Committed**

#### Components
- **Adapters** (`app/intervene/adapters/`):
  * `base.py`: Abstract interface + factory pattern (186 lines)
  * `github.py`: GitHub REST API v3 (174 lines)
  * `gitlab.py`: GitLab REST API v4 (171 lines)
  * `jira.py`: Jira REST API v3 with ADF format (203 lines)
  
- **Templates** (`app/intervene/templates/`):
  * `templates.py`: Mustache-style renderer (146 lines)
  * `invariant_failure.md`: Eval failure template (58 lines)
  * `budget_exceeded.md`: Budget overrun template (68 lines)
  * `planner_regression.md`: Canary regression template (95 lines)
  
- **Integration** (`app/intervene/watcher.py`):
  * `_create_external_issue()`: Auto-creates issues on incident creation
  * Config loading from RuntimeSettings
  * Graceful degradation if not configured
  
- **Tests**:
  * `test_issue_adapters.py`: 15 tests for all adapters
  * `test_templates.py`: 18 tests for template engine
  * `test_watcher_integration.py`: 6 integration tests

#### Features
- Factory pattern for adapter registration
- Priority mapping (P0-P4, sev1-4 → provider-specific)
- Mustache syntax: `{{var}}`, `{{#section}}`, `{{^inverted}}`
- Nested value access: `{{details.metric.value}}`
- JSON serialization for complex types
- Auto-labeling (severity + kind tags)
- Connection testing before creating issues
- Error handling (no crashes on API failures)

**Lines Added**: ~2,096

---

## Configuration Required

Add to `settings/config.yaml` or RuntimeSettings:

```yaml
interventions:
  enabled: true
  issue_provider:
    provider: github  # or gitlab, jira
    config:
      # GitHub
      token: ${GITHUB_TOKEN}
      owner: leok974
      repo: ApplyLens
      
      # GitLab
      # token: ${GITLAB_TOKEN}
      # project_id: group/project
      
      # Jira
      # base_url: https://company.atlassian.net
      # email: oncall@company.com
      # api_token: ${JIRA_TOKEN}
      # project_key: PROD
```

Create RuntimeSetting in database:
```python
from app.models_runtime import RuntimeSettings

setting = RuntimeSettings(
    key="interventions.issue_provider",
    value={
        "provider": "github",
        "config": {
            "token": "ghp_...",
            "owner": "leok974",
            "repo": "ApplyLens"
        }
    }
)
db.add(setting)
db.commit()
```

---

## Testing

Run all tests:
```bash
cd services/api
pytest tests/test_incident_lifecycle.py -v
pytest tests/test_issue_adapters.py -v
pytest tests/test_templates.py -v
pytest tests/test_watcher_integration.py -v
```

Expected: **52 tests passing** (13 + 15 + 18 + 6)

---

## What's Working

1. **Incident Detection**: Watcher checks invariants/budgets/planners every 15 min
2. **Deduplication**: Won't create duplicate incidents
3. **Rate Limiting**: Max 3 incidents/hour per key
4. **External Issues**: Auto-creates GitHub/GitLab/Jira issues with rendered templates
5. **REST API**: Full CRUD + state transitions
6. **Templates**: Dynamic markdown with mustache syntax

---

## Next Steps: PR3 - Remediation Playbooks

### Components to Build
1. **Typed Actions** (`app/intervene/actions/`):
   - `base.py`: AbstractAction with dry_run mode
   - `dbt.py`: RerunDbtAction (task_id, models)
   - `elastic.py`: RefreshSynonymsAction (index_name)
   - `planner.py`: RollbackPlannerAction (to_version)
   - `traffic.py`: ReducePlannerSplitAction (percentage)
   
2. **Executor** (`app/intervene/executor.py`):
   - `PlaybookExecutor` class
   - Dry-run simulation
   - Approval integration (Phase 4)
   - Action status tracking
   
3. **Router** (`app/routers/playbooks.py`):
   - `POST /api/incidents/:id/actions` - List available actions
   - `POST /api/incidents/:id/actions/:action/dry-run` - Preview changes
   - `POST /api/incidents/:id/actions/:action/apply` - Execute with approval
   
4. **Tests**:
   - `test_actions.py`: Unit tests for each action type
   - `test_executor.py`: Dry-run and execution tests
   - `test_playbook_approval.py`: Integration with approval gates

### Design Goals
- Type-safe action definitions (Pydantic models)
- Dry-run must show exact changes before apply
- Require approval for sev1/sev2 actions
- Track action history in IncidentAction table
- Rollback capability for reversible actions

### Example Action

```python
from app.intervene.actions.base import AbstractAction

class RerunDbtAction(AbstractAction):
    """Re-run dbt models that failed."""
    
    task_id: int
    models: List[str]
    full_refresh: bool = False
    
    def validate(self) -> bool:
        # Check task exists
        # Check models exist in manifest
        return True
    
    def dry_run(self) -> Dict[str, Any]:
        # Return: which models would run, estimated cost
        return {
            "models": self.models,
            "estimated_runtime": "5m",
            "estimated_cost": "$0.50"
        }
    
    def execute(self) -> Dict[str, Any]:
        # Actually trigger dbt run
        # Return: run_id, logs_url, status
        pass
```

---

## Remaining PRs (PR4-7)

- **PR4**: SSE Notifications + Web Panel (React UI for incidents)
- **PR5**: Gate Bridges (connect Phase 5 eval gates to incidents)
- **PR6**: CI & Mocks (mock providers, golden tests)
- **PR7**: Docs & Runbooks (INTERVENTIONS_GUIDE.md, PLAYBOOKS.md)

**Overall Phase 5.4 Progress**: 2 of 7 PRs complete (28%)

---

## Commits
- `aee5848`: PR1 - Invariant Watcher & Incident Model
- `130a564`: PR2 - Issue Openers (GitHub/GitLab/Jira) + Templates

**Total Phase 5.4 Lines**: ~3,353 lines added across 21 files
