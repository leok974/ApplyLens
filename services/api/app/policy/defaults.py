"""
Default safety policies for ApplyLens agents.

These policies implement safe-by-default behavior for Phase 3 agents.
"""

from typing import List
from .schemas import PolicyRule


def get_default_policies() -> List[PolicyRule]:
    """
    Get default safety policies for all agents.
    
    Returns:
        List of PolicyRule objects
    """
    return [
        # ===== Inbox Triage Agent =====
        
        # Allow auto-quarantine for high-risk emails from unknown senders
        PolicyRule(
            id="inbox-triage-auto-quarantine-high-risk",
            agent="inbox_triage",
            action="quarantine",
            conditions={
                "risk_score": 90,  # >= 90
                "sender_known": False
            },
            effect="allow",
            reason="Auto-quarantine high-risk emails (score >= 90) from unknown senders",
            priority=100
        ),
        
        # Require approval for other quarantine attempts
        PolicyRule(
            id="inbox-triage-quarantine-requires-approval",
            agent="inbox_triage",
            action="quarantine",
            conditions={},
            effect="deny",
            reason="Quarantine requires human approval",
            priority=50  # Lower priority, so high-risk allow rule wins when both match
        ),
        
        # Allow labeling without approval
        PolicyRule(
            id="inbox-triage-allow-labeling",
            agent="inbox_triage",
            action="label",
            conditions={},
            effect="allow",
            reason="Email labeling is safe and allowed",
            priority=10
        ),
        
        # ===== Knowledge Updater Agent =====
        
        # Deny large synonym changes in production
        PolicyRule(
            id="knowledge-update-deny-large-changes",
            agent="knowledge_update",
            action="apply",
            conditions={
                "changes_count": 200,  # >= 200
                "config_type": "synonyms"
            },
            effect="deny",
            reason="Large synonym changes (>= 200) require manual review",
            priority=100
        ),
        
        # Deny regex rule additions in production
        PolicyRule(
            id="knowledge-update-deny-regex-rules",
            agent="knowledge_update",
            action="apply",
            conditions={
                "config_type": "routing_rules",
                "has_regex": True
            },
            effect="deny",
            reason="Regex routing rules require manual review for safety",
            priority=100
        ),
        
        # Deny updates during business hours (09:00-17:00 UTC)
        PolicyRule(
            id="knowledge-update-deny-business-hours",
            agent="knowledge_update",
            action="apply",
            conditions={
                "environment": "production",
                "during_business_hours": True
            },
            effect="deny",
            reason="Production updates not allowed during business hours (09:00-17:00 UTC)",
            priority=90
        ),
        
        # Allow small changes in non-production
        PolicyRule(
            id="knowledge-update-allow-small-changes",
            agent="knowledge_update",
            action="apply",
            conditions={},
            effect="allow",
            reason="Small configuration changes are allowed with approval",
            priority=10
        ),
        
        # ===== Insights Writer Agent =====
        
        # Deny report generation for low-volume weeks
        # Agent should set volume_sufficient=False when weekly_volume < 10
        PolicyRule(
            id="insights-writer-deny-insufficient-volume",
            agent="insights_writer",
            action="generate",
            conditions={"volume_sufficient": False},
            effect="deny",
            reason="Insufficient email volume to generate meaningful insights",
            priority=50
        ),
        
        # Allow report generation by default
        PolicyRule(
            id="insights-writer-allow-generate",
            agent="insights_writer",
            action="generate",
            conditions={},
            effect="allow",
            reason="Insights report generation is safe and allowed",
            priority=10
        ),
        
        # ===== Warehouse Health Agent =====
        
        # Allow dbt runs during maintenance window
        PolicyRule(
            id="warehouse-health-allow-dbt-maintenance",
            agent="warehouse_health",
            action="dbt_run",
            conditions={
                "window": "maintenance"
            },
            effect="allow",
            reason="dbt runs allowed during maintenance window",
            priority=100
        ),
        
        # Deny dbt runs outside maintenance in production
        PolicyRule(
            id="warehouse-health-deny-dbt-prod",
            agent="warehouse_health",
            action="dbt_run",
            conditions={
                "environment": "production"
            },
            effect="deny",
            reason="Production dbt runs only allowed during maintenance window",
            priority=90
        ),
        
        # Allow dbt runs in non-production
        PolicyRule(
            id="warehouse-health-allow-dbt-nonprod",
            agent="warehouse_health",
            action="dbt_run",
            conditions={},
            effect="allow",
            reason="dbt runs allowed in non-production environments",
            priority=10
        ),
        
        # ===== Global Read-Only Policies =====
        
        # Always allow read-only operations
        PolicyRule(
            id="global-allow-read-only",
            agent="*",
            action="query",
            conditions={},
            effect="allow",
            reason="Read-only operations are always allowed",
            priority=1000
        ),
        
        PolicyRule(
            id="global-allow-fetch",
            agent="*",
            action="fetch",
            conditions={},
            effect="allow",
            reason="Read-only operations are always allowed",
            priority=1000
        ),
        
        PolicyRule(
            id="global-allow-read",
            agent="*",
            action="read",
            conditions={},
            effect="allow",
            reason="Read-only operations are always allowed",
            priority=1000
        ),
        
        PolicyRule(
            id="global-allow-list",
            agent="*",
            action="list",
            conditions={},
            effect="allow",
            reason="Read-only operations are always allowed",
            priority=1000
        ),
        
        PolicyRule(
            id="global-allow-search",
            agent="*",
            action="search",
            conditions={},
            effect="allow",
            reason="Read-only operations are always allowed",
            priority=1000
        ),
        
        # ===== Global Deny Policies =====
        
        # Always deny destructive operations without approval
        PolicyRule(
            id="global-deny-delete",
            agent="*",
            action="delete",
            conditions={},
            effect="deny",
            reason="Destructive operations require explicit approval",
            priority=900
        ),
        
        PolicyRule(
            id="global-deny-purge",
            agent="*",
            action="purge",
            conditions={},
            effect="deny",
            reason="Destructive operations require explicit approval",
            priority=900
        ),
        
        PolicyRule(
            id="global-deny-drop",
            agent="*",
            action="drop",
            conditions={},
            effect="deny",
            reason="Destructive operations require explicit approval",
            priority=900
        ),
    ]


def get_development_policies() -> List[PolicyRule]:
    """
    Get relaxed policies for development environment.
    
    Returns:
        List of PolicyRule objects
    """
    return [
        # Allow most operations in development
        PolicyRule(
            id="dev-allow-most",
            agent="*",
            action="*",
            conditions={"environment": "development"},
            effect="allow",
            reason="Development environment allows most operations",
            priority=10
        )
    ]
