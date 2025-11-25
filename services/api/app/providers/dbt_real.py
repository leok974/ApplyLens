"""Real dbt provider implementation.

Executes dbt commands via subprocess and parses artifacts.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..schemas.tools import DbtRunResult


class DbtProvider:
    """Real dbt provider.

    Executes dbt via subprocess and captures run results.
    Requires dbt CLI to be installed and accessible.
    """

    def __init__(
        self,
        cmd: str = "dbt",
        project_dir: str | None = None,
        profiles_dir: str | None = None,
    ):
        """Initialize dbt provider.

        Args:
            cmd: dbt command (default: "dbt")
            project_dir: Path to dbt project
            profiles_dir: Path to profiles directory
        """
        self.cmd = cmd
        self.project_dir = project_dir or os.getenv("DBT_PROJECT_DIR", "analytics/dbt")
        self.profiles_dir = profiles_dir or os.getenv("DBT_PROFILES_DIR")

    def run(self, target: str = "prod", models: str | None = None) -> "DbtRunResult":
        """Run dbt models.

        Args:
            target: dbt target environment
            models: Model selector (e.g., "tag:daily", "mart:*")

        Returns:
            Run result with success status and timing
        """
        from ..schemas.tools import DbtRunResult

        t0 = time.time()

        # Build command
        cmd_parts = [self.cmd, "run", "--target", target]

        if models:
            cmd_parts.extend(["--select", models])

        if self.profiles_dir:
            cmd_parts.extend(["--profiles-dir", self.profiles_dir])

        # Execute
        try:
            result = subprocess.run(
                cmd_parts,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            success = result.returncode == 0
            elapsed = time.time() - t0

            # Try to parse artifacts
            artifacts_path = None
            try:
                artifacts_file = Path(self.project_dir) / "target" / "run_results.json"
                if artifacts_file.exists():
                    with open(artifacts_file) as f:
                        json.load(f)
                        artifacts_path = str(artifacts_file)
            except Exception:
                pass

            return DbtRunResult(
                success=success, elapsed_sec=elapsed, artifacts_path=artifacts_path
            )

        except subprocess.TimeoutExpired:
            elapsed = time.time() - t0
            return DbtRunResult(success=False, elapsed_sec=elapsed, artifacts_path=None)
        except Exception as e:
            elapsed = time.time() - t0
            raise RuntimeError(f"dbt run failed: {e}")
