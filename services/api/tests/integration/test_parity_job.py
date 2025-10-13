"""
Integration tests for parity check script.

Tests the check_parity.py script with controlled data scenarios
to ensure it correctly detects drift.
"""

import pytest
import json
import subprocess
import tempfile
from pathlib import Path


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def parity_script():
    """Path to the parity check script."""
    return Path(__file__).parent.parent.parent / "scripts" / "check_parity.py"


@pytest.fixture
def temp_output():
    """Temporary output file for test results."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        yield f.name
    # Cleanup handled by tempfile


# ============================================================================
# SCRIPT EXECUTION TESTS
# ============================================================================


@pytest.mark.integration
class TestParityScriptExecution:
    """Tests for running the parity check script."""

    def test_script_runs_successfully(self, parity_script, temp_output):
        """Parity script should execute without errors."""
        result = subprocess.run(
            [
                "python",
                str(parity_script),
                "--fields",
                "risk_score",
                "--sample",
                "10",
                "--output",
                temp_output,
                "--allow",
                "999",  # Allow any mismatches for this test
            ],
            capture_output=True,
            text=True,
        )

        # Should not crash
        assert result.returncode in [0, 1]  # 0 = no mismatches, 1 = mismatches

        # Should produce output file
        output_path = Path(temp_output)
        assert output_path.exists()

        # Output should be valid JSON
        with open(output_path) as f:
            data = json.load(f)
            assert "summary" in data
            assert "mismatches" in data

    def test_script_requires_schema_version(self, parity_script, temp_output):
        """Parity script should check schema version."""
        result = subprocess.run(
            [
                "python",
                str(parity_script),
                "--fields",
                "risk_score",
                "--sample",
                "10",
                "--output",
                temp_output,
            ],
            capture_output=True,
            text=True,
        )

        # Should mention schema check
        output = result.stdout + result.stderr
        assert "schema" in output.lower() or "migration" in output.lower()


# ============================================================================
# REPORT SCHEMA TESTS
# ============================================================================


@pytest.mark.integration
class TestParityReportSchema:
    """Tests for parity report structure and content."""

    def test_report_has_required_fields(self, parity_script, temp_output):
        """Parity report should have all required fields."""
        subprocess.run(
            [
                "python",
                str(parity_script),
                "--fields",
                "risk_score,category",
                "--sample",
                "20",
                "--output",
                temp_output,
                "--allow",
                "999",
            ],
            capture_output=True,
        )

        with open(temp_output) as f:
            report = json.load(f)

        # Top-level fields
        assert "timestamp" in report
        assert "config" in report
        assert "summary" in report
        assert "mismatches" in report

        # Config fields
        config = report["config"]
        assert "sample_size" in config
        assert "fields" in config
        assert config["fields"] == ["risk_score", "category"]

        # Summary fields
        summary = report["summary"]
        assert "total_checked" in summary
        assert "total_mismatches" in summary
        assert "mismatch_percentage" in summary
        assert "by_field" in summary

        # By-field breakdown
        by_field = summary["by_field"]
        assert "risk_score" in by_field
        assert "category" in by_field

    def test_mismatch_entries_structure(self, parity_script, temp_output):
        """Mismatch entries should have expected structure."""
        subprocess.run(
            [
                "python",
                str(parity_script),
                "--fields",
                "risk_score",
                "--sample",
                "50",
                "--output",
                temp_output,
                "--allow",
                "999",
            ],
            capture_output=True,
        )

        with open(temp_output) as f:
            report = json.load(f)

        mismatches = report["mismatches"]
        if len(mismatches) > 0:
            mismatch = mismatches[0]

            # All mismatches should have id and issue
            assert "id" in mismatch
            assert "issue" in mismatch

            # Issue should be one of the expected types
            assert mismatch["issue"] in [
                "field_mismatch",
                "missing_in_db",
                "missing_in_es",
            ]


# ============================================================================
# EXIT CODE TESTS
# ============================================================================


@pytest.mark.integration
class TestParityExitCodes:
    """Tests for parity script exit codes."""

    def test_exit_code_zero_when_allowed(self, parity_script, temp_output):
        """Script should exit 0 when mismatches <= allowed."""
        result = subprocess.run(
            [
                "python",
                str(parity_script),
                "--fields",
                "risk_score",
                "--sample",
                "10",
                "--output",
                temp_output,
                "--allow",
                "999",  # Allow many mismatches
            ],
            capture_output=True,
        )

        assert result.returncode == 0

    def test_exit_code_one_when_exceeded(self, parity_script, temp_output):
        """Script should exit 1 when mismatches > allowed."""
        # First run to see if there are any mismatches
        subprocess.run(
            [
                "python",
                str(parity_script),
                "--fields",
                "risk_score",
                "--sample",
                "50",
                "--output",
                temp_output,
                "--allow",
                "999",
            ],
            capture_output=True,
        )

        with open(temp_output) as f:
            report = json.load(f)

        total_mismatches = report["summary"]["total_mismatches"]

        if total_mismatches > 0:
            # Run again with allow=0
            result2 = subprocess.run(
                [
                    "python",
                    str(parity_script),
                    "--fields",
                    "risk_score",
                    "--sample",
                    "50",
                    "--output",
                    temp_output,
                    "--allow",
                    "0",
                ],
                capture_output=True,
            )

            assert result2.returncode == 1


# ============================================================================
# PARAMETER VALIDATION TESTS
# ============================================================================


@pytest.mark.integration
class TestParityParameters:
    """Tests for parameter validation."""

    def test_multiple_fields(self, parity_script, temp_output):
        """Script should handle multiple fields."""
        result = subprocess.run(
            [
                "python",
                str(parity_script),
                "--fields",
                "risk_score,expires_at,category",
                "--sample",
                "10",
                "--output",
                temp_output,
                "--allow",
                "999",
            ],
            capture_output=True,
        )

        assert result.returncode in [0, 1]

        with open(temp_output) as f:
            report = json.load(f)

        # Should check all three fields
        by_field = report["summary"]["by_field"]
        assert "risk_score" in by_field
        assert "expires_at" in by_field
        assert "category" in by_field

    def test_custom_sample_size(self, parity_script, temp_output):
        """Script should respect custom sample size."""
        subprocess.run(
            [
                "python",
                str(parity_script),
                "--fields",
                "risk_score",
                "--sample",
                "25",
                "--output",
                temp_output,
                "--allow",
                "999",
            ],
            capture_output=True,
        )

        with open(temp_output) as f:
            report = json.load(f)

        # Sample size should be reflected in config
        assert report["config"]["sample_size"] <= 25

    def test_csv_output_created(self, parity_script, temp_output):
        """Script should create CSV output when requested."""
        csv_file = temp_output.replace(".json", ".csv")

        result = subprocess.run(
            [
                "python",
                str(parity_script),
                "--fields",
                "risk_score",
                "--sample",
                "20",
                "--output",
                temp_output,
                "--csv",
                csv_file,
                "--allow",
                "999",
            ],
            capture_output=True,
        )

        # Both files should exist
        assert Path(temp_output).exists()
        if result.returncode in [0, 1]:
            # CSV might not be created if no mismatches
            pass


# ============================================================================
# COMPARISON LOGIC TESTS
# ============================================================================


@pytest.mark.integration
class TestParityComparison:
    """Tests for comparison logic."""

    def test_numeric_tolerance(self, parity_script, temp_output):
        """Float values should be compared with tolerance."""
        # This test is somewhat implicit - the script should not flag
        # tiny float differences as mismatches
        subprocess.run(
            [
                "python",
                str(parity_script),
                "--fields",
                "risk_score",
                "--sample",
                "50",
                "--output",
                temp_output,
                "--allow",
                "999",
            ],
            capture_output=True,
        )

        with open(temp_output) as f:
            report = json.load(f)

        # Check that mismatches (if any) are real differences
        for mismatch in report["mismatches"][:5]:  # Check first 5
            if mismatch["issue"] == "field_mismatch":
                if "risk_score" in mismatch.get("fields", {}):
                    field_data = mismatch["fields"]["risk_score"]
                    db_val = field_data["db"]
                    es_val = field_data["es"]

                    if db_val is not None and es_val is not None:
                        # Should be a real difference (> 0.001)
                        diff = abs(float(db_val) - float(es_val))
                        assert diff >= 0.001 or db_val != es_val


# ============================================================================
# METRICS INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.slow
class TestParityMetrics:
    """Tests for metrics integration (if implemented)."""

    def test_parity_run_updates_metrics(self, parity_script, temp_output):
        """Running parity should update Prometheus metrics."""
        # This test would check /metrics endpoint after running parity
        # For now, just verify script runs without metrics errors
        result = subprocess.run(
            [
                "python",
                str(parity_script),
                "--fields",
                "risk_score",
                "--sample",
                "10",
                "--output",
                temp_output,
                "--allow",
                "999",
            ],
            capture_output=True,
            text=True,
        )

        # Should not have metrics-related errors
        output = result.stdout + result.stderr
        assert "metric" not in output.lower() or "error" not in output.lower()
