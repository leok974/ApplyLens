"""
Knowledge Updater Agent - Phase 3 PR3

Reads BigQuery data marts and generates Elasticsearch configuration diffs.
Practical use case: Keep ES synonyms and routing rules in sync with warehouse data.
"""

from typing import Any, Dict, List

from ..providers.factory import get_provider_factory
from ..utils.approvals import Approvals
from ..utils.artifacts import artifacts_store


class KnowledgeUpdaterAgent:
    """
    Update knowledge base (Elasticsearch) from data warehouse (BigQuery).

    Workflow:
    1. Query BigQuery marts for configuration data (synonyms, routing rules)
    2. Fetch current Elasticsearch configuration
    3. Generate diff (added, removed, unchanged)
    4. (Optional) Apply changes to Elasticsearch with approval
    5. Write diff artifacts for review

    Use cases:
    - Sync synonyms from product taxonomy mart
    - Update routing rules from classification models
    - Refresh stop words from NLP analysis

    Safety:
    - Dry-run mode by default
    - Apply requires approval gate
    - Generates diffs before any changes
    """

    NAME = "knowledge_update"

    def __init__(self, provider_factory=None):
        """Initialize with provider factory."""
        self.factory = provider_factory or get_provider_factory()

    def describe(self) -> Dict[str, Any]:
        """Return agent description."""
        return {
            "name": self.NAME,
            "description": "Update Elasticsearch knowledge base from BigQuery data marts",
            "capabilities": [
                "Query BigQuery for configuration data",
                "Fetch current Elasticsearch settings",
                "Generate configuration diffs",
                "Apply updates with approval",
                "Write diff artifacts",
            ],
            "safe_by_default": True,
            "requires_approval": ["apply_changes"],
        }

    def plan(self, objective: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create execution plan."""
        config_type = params.get(
            "config_type", "synonyms"
        )  # synonyms, routing_rules, etc.
        mart_table = params.get("mart_table", "knowledge.synonyms")
        apply_changes = params.get("apply_changes", False)

        steps = [
            f"1. Query BigQuery mart: {mart_table}",
            "2. Fetch current Elasticsearch configuration",
            "3. Generate diff (added, removed, unchanged)",
        ]

        if apply_changes:
            steps.append("4. Apply changes to Elasticsearch (requires approval)")

        steps.append(f"5. Write diff artifact: {config_type}.diff.json")

        return {
            "agent": self.NAME,
            "objective": objective,
            "steps": steps,
            "tools": ["bigquery", "elasticsearch"],
            "config_type": config_type,
            "mart_table": mart_table,
            "apply_changes": apply_changes,
        }

    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute knowledge update.

        Returns:
            Dict with diff results and artifacts
        """
        dry_run = plan.get("dry_run", True)
        config_type = plan.get("config_type", "synonyms")
        mart_table = plan.get("mart_table", "knowledge.synonyms")
        apply_changes = plan.get("apply_changes", False)

        ops_count = 0

        # Get providers
        bq = self.factory.bigquery()
        es = self.factory.es()

        # Query BigQuery for new configuration
        if config_type == "synonyms":
            query = f"""
                SELECT DISTINCT
                    term,
                    synonym_group
                FROM `{mart_table}`
                WHERE active = TRUE
                ORDER BY term
            """
        elif config_type == "routing_rules":
            query = f"""
                SELECT DISTINCT
                    pattern,
                    label,
                    priority
                FROM `{mart_table}`
                WHERE active = TRUE
                ORDER BY priority DESC
            """
        else:
            raise ValueError(f"Unsupported config_type: {config_type}")

        new_config_rows = bq.query_rows(query)
        ops_count += 1

        # Convert to configuration format
        new_config = self._rows_to_config(config_type, new_config_rows)

        # Fetch current Elasticsearch configuration
        current_config = self._fetch_es_config(es, config_type)
        ops_count += 1

        # Generate diff
        diff = self._generate_diff(current_config, new_config)

        # Apply changes if requested and approved
        applied = False
        if apply_changes and not dry_run:
            # Check approval
            context = {
                "added_count": len(diff["added"]),
                "removed_count": len(diff["removed"]),
                "config_type": config_type,
            }

            if Approvals.allow(agent_name=self.NAME, action="apply", context=context):
                # Would call es.update_config(config_type, new_config) here
                applied = True
                ops_count += 1
            else:
                # Approval denied (Phase 3: apply is moderate-risk, should be allowed)
                # In practice, large changes would be denied
                pass

        # Write diff artifact
        diff_artifact = {
            "config_type": config_type,
            "mart_table": mart_table,
            "timestamp": plan.get("started_at", ""),
            "diff": diff,
            "applied": applied,
            "dry_run": dry_run,
        }

        artifact_path = f"{config_type}.diff.json"
        artifacts_store.write_json(artifact_path, diff_artifact, agent_name=self.NAME)

        # Generate summary report
        report = self._generate_report(config_type, diff, applied, dry_run)
        report_path = f"{config_type}.diff.md"
        artifacts_store.write(report_path, report, agent_name=self.NAME)

        return {
            "config_type": config_type,
            "added_count": len(diff["added"]),
            "removed_count": len(diff["removed"]),
            "unchanged_count": len(diff["unchanged"]),
            "applied": applied,
            "artifacts": {"diff_json": artifact_path, "diff_report": report_path},
            "ops_count": ops_count,
            "dry_run": dry_run,
        }

    def _rows_to_config(self, config_type: str, rows: List[Dict]) -> List[Dict]:
        """Convert BQ rows to configuration format."""
        if config_type == "synonyms":
            # Group by synonym_group
            groups = {}
            for row in rows:
                group = row.get("synonym_group", "default")
                if group not in groups:
                    groups[group] = []
                groups[group].append(row.get("term", ""))

            # Convert to ES synonyms format: "term1, term2, term3"
            return [
                {"group": group, "terms": ", ".join(sorted(terms))}
                for group, terms in groups.items()
            ]

        elif config_type == "routing_rules":
            return [
                {
                    "pattern": row.get("pattern"),
                    "label": row.get("label"),
                    "priority": row.get("priority", 0),
                }
                for row in rows
            ]

        return []

    def _fetch_es_config(self, es, config_type: str) -> List[Dict]:
        """Fetch current Elasticsearch configuration."""
        # In reality, would call es.get_settings(index, config_type)
        # For now, return empty config (mock)
        return []

    def _generate_diff(self, current: List[Dict], new: List[Dict]) -> Dict[str, List]:
        """Generate diff between current and new configuration."""
        # Convert to sets for comparison
        current_set = {self._config_key(item) for item in current}
        new_set = {self._config_key(item) for item in new}

        added_keys = new_set - current_set
        removed_keys = current_set - new_set
        unchanged_keys = current_set & new_set

        # Map back to full items
        added = [item for item in new if self._config_key(item) in added_keys]
        removed = [item for item in current if self._config_key(item) in removed_keys]
        unchanged = [item for item in new if self._config_key(item) in unchanged_keys]

        return {"added": added, "removed": removed, "unchanged": unchanged}

    def _config_key(self, item: Dict) -> str:
        """Generate unique key for config item."""
        if "group" in item:
            return f"group:{item['group']}"
        elif "pattern" in item:
            return f"pattern:{item['pattern']}"
        return str(item)

    def _generate_report(
        self, config_type: str, diff: Dict[str, List], applied: bool, dry_run: bool
    ) -> str:
        """Generate markdown diff report."""
        report = []
        report.append(f"# Knowledge Update Report: {config_type}\n")
        report.append(f"**Mode**: {'DRY RUN' if dry_run else 'LIVE'}\n")
        report.append(f"**Applied**: {'Yes' if applied else 'No'}\n\n")

        report.append("## Summary\n")
        report.append(f"- **Added**: {len(diff['added'])} items\n")
        report.append(f"- **Removed**: {len(diff['removed'])} items\n")
        report.append(f"- **Unchanged**: {len(diff['unchanged'])} items\n\n")

        if len(diff["added"]) > 0:
            report.append("## Added Items\n")
            for item in diff["added"][:10]:  # Show max 10
                report.append(f"- `{item}`\n")
            if len(diff["added"]) > 10:
                report.append(f"- ... and {len(diff['added']) - 10} more\n")
            report.append("\n")

        if len(diff["removed"]) > 0:
            report.append("## Removed Items\n")
            for item in diff["removed"][:10]:  # Show max 10
                report.append(f"- `{item}`\n")
            if len(diff["removed"]) > 10:
                report.append(f"- ... and {len(diff['removed']) - 10} more\n")
            report.append("\n")

        if not applied and not dry_run:
            report.append("## Note\n")
            report.append(
                "Changes were not applied. Approval may be required for large updates.\n"
            )

        return "".join(report)


def register(registry):
    """Register Knowledge Updater Agent."""
    agent = KnowledgeUpdaterAgent()

    def handler(plan: Dict[str, Any]) -> Dict[str, Any]:
        return agent.execute(plan)

    registry.register(agent.NAME, handler)
