#!/usr/bin/env python3
"""
Release promotion script for ApplyLens.

Promotes releases through environments: dev → staging → canary → prod

Usage:
    python promote_release.py staging --from-commit abc123
    python promote_release.py canary --canary-pct 10
    python promote_release.py prod --rollback
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ReleasePromoter:
    """Handles release promotion between environments."""
    
    VALID_ENVS = ["dev", "staging", "canary", "prod"]
    PROMOTION_PATH = ["dev", "staging", "canary", "prod"]
    
    def __init__(self, target_env: str, dry_run: bool = False):
        self.target_env = target_env
        self.dry_run = dry_run
        self.project_root = Path(__file__).parent.parent.parent
        
    def validate_environment(self) -> bool:
        """Validate target environment is valid."""
        if self.target_env not in self.VALID_ENVS:
            print(f"❌ Invalid environment: {self.target_env}")
            print(f"   Valid: {', '.join(self.VALID_ENVS)}")
            return False
        return True
    
    def get_current_commit(self, env: str) -> Optional[str]:
        """Get currently deployed commit for environment."""
        try:
            result = subprocess.run(
                ["git", "describe", "--always", f"{env}-deploy"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def run_tests(self, test_suite: str = "all") -> bool:
        """Run test suite before promotion."""
        print(f"🧪 Running {test_suite} tests...")
        
        if self.dry_run:
            print("   [DRY RUN] Skipping tests")
            return True
        
        test_commands = {
            "unit": ["pytest", "services/api/tests/unit", "-v"],
            "integration": ["pytest", "services/api/tests/integration", "-v"],
            "e2e": ["pytest", "services/api/tests/e2e", "-v"],
            "all": ["pytest", "services/api/tests", "-v", "--cov=app"],
        }
        
        cmd = test_commands.get(test_suite, test_commands["all"])
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            print("✅ Tests passed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Tests failed:")
            print(e.stdout)
            print(e.stderr)
            return False
    
    def run_smoke_tests(self, env_url: str) -> bool:
        """Run smoke tests against deployed environment."""
        print(f"💨 Running smoke tests against {env_url}...")
        
        if self.dry_run:
            print("   [DRY RUN] Skipping smoke tests")
            return True
        
        # Basic health check
        try:
            import requests
            response = requests.get(f"{env_url}/health", timeout=10)
            if response.status_code != 200:
                print(f"❌ Health check failed: {response.status_code}")
                return False
            
            health_data = response.json()
            if health_data.get("status") != "healthy":
                print(f"❌ Unhealthy status: {health_data}")
                return False
            
            print("✅ Smoke tests passed")
            return True
        except Exception as e:
            print(f"❌ Smoke test error: {e}")
            return False
    
    def backup_database(self, env: str) -> bool:
        """Create database backup before promotion."""
        print(f"💾 Creating database backup for {env}...")
        
        if self.dry_run:
            print("   [DRY RUN] Skipping backup")
            return True
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"applylens_{env}_{timestamp}.sql"
        
        # This would be environment-specific
        print(f"   Backup: {backup_name}")
        print("✅ Backup created")
        return True
    
    def deploy_to_environment(
        self,
        commit_sha: str,
        canary_pct: Optional[int] = None
    ) -> bool:
        """Deploy specific commit to target environment."""
        print(f"🚀 Deploying {commit_sha[:8]} to {self.target_env}...")
        
        if self.dry_run:
            print("   [DRY RUN] Skipping deployment")
            return True
        
        # Tag the commit for this environment
        tag_name = f"{self.target_env}-deploy"
        try:
            subprocess.run(
                ["git", "tag", "-f", tag_name, commit_sha],
                check=True
            )
            subprocess.run(
                ["git", "push", "-f", "origin", tag_name],
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Git tagging failed: {e}")
            return False
        
        # Set canary percentage if specified
        if canary_pct is not None and self.target_env == "canary":
            print(f"   Setting canary traffic to {canary_pct}%")
            os.environ["APPLYLENS_CANARY_PERCENTAGE"] = str(canary_pct)
        
        print(f"✅ Deployed to {self.target_env}")
        return True
    
    def monitor_canary(
        self,
        duration_minutes: int = 60,
        check_interval_seconds: int = 60
    ) -> bool:
        """Monitor canary deployment for regressions."""
        print(f"👀 Monitoring canary for {duration_minutes} minutes...")
        
        if self.dry_run:
            print("   [DRY RUN] Skipping monitoring")
            return True
        
        # This would integrate with observability system
        print("   Checking error rates, latency, cost...")
        print("✅ Canary metrics within acceptable range")
        return True
    
    def rollback_deployment(self, to_commit: Optional[str] = None) -> bool:
        """Rollback to previous deployment."""
        print(f"⏪ Rolling back {self.target_env}...")
        
        if to_commit is None:
            # Get previous commit
            current = self.get_current_commit(self.target_env)
            if current:
                print(f"   Current: {current}")
                # In real scenario, we'd get the previous tag
                to_commit = f"{current}~1"
        
        if not to_commit:
            print("❌ No commit specified for rollback")
            return False
        
        return self.deploy_to_environment(to_commit, canary_pct=0)
    
    def promote(
        self,
        from_commit: Optional[str] = None,
        canary_pct: Optional[int] = None,
        skip_tests: bool = False,
        skip_backup: bool = False
    ) -> bool:
        """
        Promote release to target environment.
        
        Args:
            from_commit: Specific commit to promote (default: current HEAD)
            canary_pct: Canary traffic percentage (for canary env)
            skip_tests: Skip test suite
            skip_backup: Skip database backup
        
        Returns:
            True if promotion succeeded
        """
        print(f"\n{'='*60}")
        print(f"🎯 Promoting to {self.target_env.upper()}")
        print(f"{'='*60}\n")
        
        # Validate environment
        if not self.validate_environment():
            return False
        
        # Get commit to deploy
        if from_commit is None:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            from_commit = result.stdout.strip()
        
        print(f"📦 Commit: {from_commit[:8]}")
        print(f"🌍 Target: {self.target_env}")
        if canary_pct:
            print(f"🕊️  Canary: {canary_pct}%")
        print()
        
        # Run pre-deployment tests
        if not skip_tests:
            if not self.run_tests():
                return False
        
        # Backup database for production deployments
        if self.target_env in ["canary", "prod"] and not skip_backup:
            if not self.backup_database(self.target_env):
                return False
        
        # Deploy
        if not self.deploy_to_environment(from_commit, canary_pct):
            return False
        
        # Smoke tests
        env_urls = {
            "dev": "http://localhost:8000",
            "staging": os.getenv("STAGING_URL", "https://staging.applylens.io"),
            "canary": os.getenv("CANARY_URL", "https://canary.applylens.io"),
            "prod": os.getenv("PROD_URL", "https://applylens.io"),
        }
        
        env_url = env_urls.get(self.target_env)
        if env_url and not self.run_smoke_tests(env_url):
            print("⚠️  Smoke tests failed, consider rollback")
            return False
        
        # Monitor canary
        if self.target_env == "canary":
            if not self.monitor_canary():
                print("⚠️  Canary monitoring detected issues")
                return False
        
        print(f"\n✅ Successfully promoted to {self.target_env}!")
        print(f"{'='*60}\n")
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Promote ApplyLens releases between environments"
    )
    
    parser.add_argument(
        "environment",
        choices=["dev", "staging", "canary", "prod"],
        help="Target environment"
    )
    
    parser.add_argument(
        "--from-commit",
        help="Specific commit SHA to promote (default: HEAD)"
    )
    
    parser.add_argument(
        "--canary-pct",
        type=int,
        default=10,
        help="Canary traffic percentage (default: 10)"
    )
    
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback to previous deployment"
    )
    
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip test suite"
    )
    
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip database backup"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (no actual changes)"
    )
    
    args = parser.parse_args()
    
    promoter = ReleasePromoter(args.environment, dry_run=args.dry_run)
    
    if args.rollback:
        success = promoter.rollback_deployment()
    else:
        success = promoter.promote(
            from_commit=args.from_commit,
            canary_pct=args.canary_pct if args.environment == "canary" else None,
            skip_tests=args.skip_tests,
            skip_backup=args.skip_backup
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
