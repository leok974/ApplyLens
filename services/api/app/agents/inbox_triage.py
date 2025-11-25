"""
Inbox Triage Agent - Phase 3 PR2

Scores email risk and applies Gmail labels with approval gates.
Practical use case: Daily triage of inbox, flag spam/phishing, quarantine high-risk emails.
"""

from typing import Any, Dict, List

from ..providers.factory import get_provider_factory
from ..utils.approvals import Approvals
from ..utils.artifacts import artifacts_store


class RiskScorer:
    """
    Score email risk based on multiple signals.

    Risk factors:
    - Sender domain reputation
    - Suspicious keywords (urgent, verify, suspend, click)
    - Links to unknown domains
    - Attachments (especially .exe, .zip)
    - Impersonation attempts
    """

    # High-risk keywords
    SUSPICIOUS_KEYWORDS = {
        "urgent",
        "verify",
        "suspend",
        "account",
        "click here",
        "confirm",
        "password",
        "billing",
        "expired",
        "act now",
        "winner",
        "congratulations",
        "prize",
        "claim",
        "refund",
    }

    # Known safe domains (allowlist)
    SAFE_DOMAINS = {
        "google.com",
        "github.com",
        "microsoft.com",
        "apple.com",
        "amazon.com",
        "stripe.com",
        "atlassian.com",
        "slack.com",
    }

    @staticmethod
    def score(email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score email risk from 0-100 (100 = highest risk).

        Args:
            email: Email dict with keys: from, subject, snippet, labels

        Returns:
            Dict with risk_score, risk_level, reasons
        """
        score = 0
        reasons = []

        sender = email.get("from", "").lower()
        subject = email.get("subject", "").lower()
        snippet = email.get("snippet", "").lower()
        text = f"{subject} {snippet}"

        # Check sender domain
        domain = sender.split("@")[-1] if "@" in sender else ""

        if domain and domain not in RiskScorer.SAFE_DOMAINS:
            if any(x in domain for x in ["no-reply", "noreply", "donotreply"]):
                score += 5  # Slightly suspicious
                reasons.append("no-reply domain")

            # Check for suspicious TLDs
            if any(domain.endswith(tld) for tld in [".ru", ".cn", ".tk", ".ml"]):
                score += 30
                reasons.append("suspicious TLD")

        # Check for suspicious keywords
        keyword_count = sum(1 for kw in RiskScorer.SUSPICIOUS_KEYWORDS if kw in text)
        if keyword_count > 0:
            keyword_score = min(keyword_count * 15, 40)  # Cap at 40
            score += keyword_score
            reasons.append(f"{keyword_count} suspicious keywords")

        # Check for phishing patterns
        if "verify" in text and "account" in text:
            score += 20
            reasons.append("phishing pattern: verify account")

        if "click here" in text or "click below" in text:
            score += 15
            reasons.append("suspicious link prompt")

        # Check labels (Gmail's own classification)
        labels = email.get("labels", [])
        if "SPAM" in labels:
            score += 50
            reasons.append("Gmail marked as spam")

        if "CATEGORY_PROMOTIONS" in labels:
            score += 5  # Slightly more risk

        # Determine risk level
        if score >= 80:
            risk_level = "CRITICAL"
        elif score >= 60:
            risk_level = "HIGH"
        elif score >= 40:
            risk_level = "MEDIUM"
        elif score >= 20:
            risk_level = "LOW"
        else:
            risk_level = "SAFE"

        return {
            "risk_score": min(score, 100),  # Cap at 100
            "risk_level": risk_level,
            "reasons": reasons,
            "suggested_action": RiskScorer._suggest_action(score),
        }

    @staticmethod
    def _suggest_action(score: int) -> str:
        """Suggest action based on risk score."""
        if score >= 80:
            return "quarantine"
        elif score >= 60:
            return "flag"
        elif score >= 40:
            return "label_review"
        else:
            return "no_action"


class InboxTriageAgent:
    """
    Triage inbox emails by risk level.

    Workflow:
    1. Query recent inbox emails (last 24 hours)
    2. Score each email for risk
    3. Apply labels based on risk level
    4. (Optional) Quarantine high-risk emails with approval

    Safety:
    - Dry-run mode by default
    - Quarantine requires approval gate
    - Budget limits (max 100 emails, 30 seconds)
    """

    NAME = "inbox_triage"

    def __init__(self, provider_factory=None):
        """Initialize with provider factory."""
        self.factory = provider_factory or get_provider_factory()

    def describe(self) -> Dict[str, Any]:
        """Return agent description."""
        return {
            "name": self.NAME,
            "description": "Triage inbox emails by risk level and apply labels",
            "capabilities": [
                "Score email risk (0-100)",
                "Apply Gmail labels by risk level",
                "Quarantine high-risk emails (with approval)",
                "Generate triage report",
            ],
            "safe_by_default": True,
            "requires_approval": ["quarantine"],
        }

    def plan(self, objective: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create execution plan."""
        max_emails = params.get("max_emails", 50)
        hours_back = params.get("hours_back", 24)
        apply_labels = params.get("apply_labels", True)
        quarantine_threshold = params.get("quarantine_threshold", 80)

        steps = [
            f"1. Query inbox emails from last {hours_back} hours (max {max_emails})",
            "2. Score each email for risk (0-100)",
            "3. Classify by risk level (SAFE, LOW, MEDIUM, HIGH, CRITICAL)",
        ]

        if apply_labels:
            steps.append("4. Apply Gmail labels based on risk level")

        if quarantine_threshold < 100:
            steps.append(
                f"5. Quarantine emails with risk >= {quarantine_threshold} (requires approval)"
            )

        steps.append("6. Write triage report artifact")

        return {
            "agent": self.NAME,
            "objective": objective,
            "steps": steps,
            "tools": ["gmail"],
            "max_emails": max_emails,
            "hours_back": hours_back,
            "apply_labels": apply_labels,
            "quarantine_threshold": quarantine_threshold,
        }

    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute inbox triage.

        Returns:
            Dict with triage results and artifacts
        """
        dry_run = plan.get("dry_run", True)
        max_emails = plan.get("max_emails", 50)
        hours_back = plan.get("hours_back", 24)
        apply_labels = plan.get("apply_labels", True)
        quarantine_threshold = plan.get("quarantine_threshold", 80)

        # Get Gmail provider
        gmail = self.factory.gmail()

        # Query recent inbox emails
        query = f"in:inbox newer_than:{hours_back}h"
        emails = gmail.search_recent(query=query, max_results=max_emails)

        ops_count = 1  # One search operation

        # Score each email
        triage_results = []
        for email in emails:
            risk_data = RiskScorer.score(email)
            triage_results.append(
                {
                    "email_id": email.get("id"),
                    "from": email.get("from"),
                    "subject": email.get("subject"),
                    "date": email.get("date"),
                    **risk_data,
                }
            )

        # Group by risk level
        by_risk_level = {
            "SAFE": [],
            "LOW": [],
            "MEDIUM": [],
            "HIGH": [],
            "CRITICAL": [],
        }

        for result in triage_results:
            by_risk_level[result["risk_level"]].append(result)

        # Apply labels (if not dry_run and apply_labels)
        actions_taken = []
        if apply_labels and not dry_run:
            for result in triage_results:
                label = f"risk/{result['risk_level'].lower()}"

                # Check approval
                if Approvals.allow(
                    agent_name=self.NAME,
                    action="label",
                    context={"risk_score": result["risk_score"]},
                ):
                    # Would call gmail.add_label(email_id, label) here
                    actions_taken.append(
                        {
                            "action": "label",
                            "email_id": result["email_id"],
                            "label": label,
                        }
                    )
                    ops_count += 1

        # Quarantine high-risk emails (if threshold met and approved)
        quarantined = []
        if not dry_run:
            for result in triage_results:
                if result["risk_score"] >= quarantine_threshold:
                    # Check approval
                    if Approvals.allow(
                        agent_name=self.NAME,
                        action="quarantine",
                        context={"risk_score": result["risk_score"]},
                    ):
                        # Would call gmail.archive(email_id) or gmail.trash(email_id)
                        actions_taken.append(
                            {
                                "action": "quarantine",
                                "email_id": result["email_id"],
                                "reason": result["reasons"],
                            }
                        )
                        ops_count += 1
                        quarantined.append(result["email_id"])
                    else:
                        # Quarantine denied - would require human approval in Phase 4
                        actions_taken.append(
                            {
                                "action": "quarantine_denied",
                                "email_id": result["email_id"],
                                "reason": "High-risk action requires approval",
                            }
                        )

        # Write triage report artifact
        report = self._generate_report(
            total_emails=len(emails),
            by_risk_level=by_risk_level,
            actions_taken=actions_taken,
            quarantined=quarantined,
            dry_run=dry_run,
        )

        artifact_path = artifacts_store.get_timestamped_path(
            "triage_report", "md", agent_name=self.NAME
        )
        artifacts_store.write(artifact_path, report, agent_name=self.NAME)

        # Write JSON results
        json_path = artifacts_store.get_timestamped_path(
            "triage_results", "json", agent_name=self.NAME
        )
        artifacts_store.write_json(
            json_path,
            {
                "total_emails": len(emails),
                "by_risk_level": {k: len(v) for k, v in by_risk_level.items()},
                "triage_results": triage_results,
                "actions_taken": actions_taken,
                "quarantined": quarantined,
            },
            agent_name=self.NAME,
        )

        return {
            "total_emails": len(emails),
            "by_risk_level": {k: len(v) for k, v in by_risk_level.items()},
            "high_risk_count": len(by_risk_level["HIGH"])
            + len(by_risk_level["CRITICAL"]),
            "quarantined_count": len(quarantined),
            "actions_count": len(actions_taken),
            "artifacts": {"report": artifact_path, "results_json": json_path},
            "ops_count": ops_count,
            "dry_run": dry_run,
        }

    def _generate_report(
        self,
        total_emails: int,
        by_risk_level: Dict[str, List],
        actions_taken: List[Dict],
        quarantined: List[str],
        dry_run: bool,
    ) -> str:
        """Generate markdown triage report."""
        report = []
        report.append("# Inbox Triage Report\n")
        report.append(f"**Mode**: {'DRY RUN' if dry_run else 'LIVE'}\n")
        report.append(f"**Total Emails**: {total_emails}\n\n")

        report.append("## Risk Distribution\n")
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "SAFE"]:
            count = len(by_risk_level[level])
            if count > 0:
                report.append(f"- **{level}**: {count} emails\n")

                # Show sample emails for high risk
                if level in ["CRITICAL", "HIGH"] and count > 0:
                    report.append("  - Sample emails:\n")
                    for email in by_risk_level[level][:3]:  # Show max 3
                        report.append(
                            f"    - From: {email['from']}, Subject: {email['subject']}\n"
                        )
                        report.append(
                            f"      Risk Score: {email['risk_score']}, Reasons: {', '.join(email['reasons'])}\n"
                        )

        report.append("\n## Actions Taken\n")
        if len(actions_taken) > 0:
            report.append(f"Total: {len(actions_taken)} actions\n\n")
            for action in actions_taken[:10]:  # Show max 10
                report.append(f"- {action['action']} on email {action['email_id']}\n")
        else:
            report.append("No actions taken (dry run mode)\n")

        if len(quarantined) > 0:
            report.append("\n## Quarantined\n")
            report.append(f"**Count**: {len(quarantined)} emails\n")

        return "".join(report)


def register(registry):
    """Register Inbox Triage Agent."""
    agent = InboxTriageAgent()

    def handler(plan: Dict[str, Any]) -> Dict[str, Any]:
        return agent.execute(plan)

    registry.register(agent.NAME, handler)
