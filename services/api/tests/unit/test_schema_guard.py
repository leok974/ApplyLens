"""
Test schema guard integration in backfill scripts.

This test verifies that the schema guard correctly prevents scripts
from running when the database schema is outdated.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.utils.schema_guard import (
    check_column_exists,
    require_columns,
    require_min_migration,
)


class TestSchemaGuard:
    """Tests for schema_guard module."""

    def test_require_min_migration_passes_when_current_ge_required(self, monkeypatch):
        """Test that require_min_migration passes when DB version >= required."""
        # Mock get_current_migration to return a version >= required
        monkeypatch.setattr(
            "app.utils.schema_guard.get_current_migration",
            lambda: "0009_add_emails_category",
        )

        # Should not raise
        require_min_migration("0008_approvals_proposed")
        require_min_migration("0009_add_emails_category")

    def test_require_min_migration_fails_when_current_lt_required(self, monkeypatch):
        """Test that require_min_migration raises when DB version < required."""
        # Mock get_current_migration to return old version
        monkeypatch.setattr(
            "app.utils.schema_guard.get_current_migration",
            lambda: "0008_approvals_proposed",
        )

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Database schema is too old"):
            require_min_migration("0009_add_emails_category")

    def test_require_min_migration_fails_when_version_unknown(self, monkeypatch):
        """Test that require_min_migration raises when version cannot be determined."""
        # Mock get_current_migration to return None
        monkeypatch.setattr(
            "app.utils.schema_guard.get_current_migration", lambda: None
        )

        # Should raise RuntimeError
        with pytest.raises(
            RuntimeError, match="Cannot determine database migration version"
        ):
            require_min_migration("0009_add_emails_category")

    def test_check_column_exists_returns_true_when_exists(self, monkeypatch):
        """Test that check_column_exists returns True for existing column."""
        # Mock inspect to return columns including 'category'
        mock_inspector = MagicMock()
        mock_inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "subject"},
            {"name": "category"},
        ]

        with patch("app.utils.schema_guard.inspect", return_value=mock_inspector):
            result = check_column_exists("emails", "category")
            assert result is True

    def test_check_column_exists_returns_false_when_missing(self, monkeypatch):
        """Test that check_column_exists returns False for missing column."""
        # Mock inspect to return columns without 'category'
        mock_inspector = MagicMock()
        mock_inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "subject"},
        ]

        with patch("app.utils.schema_guard.inspect", return_value=mock_inspector):
            result = check_column_exists("emails", "category")
            assert result is False

    def test_require_columns_passes_when_all_exist(self, monkeypatch):
        """Test that require_columns passes when all columns exist."""
        # Mock check_column_exists to always return True
        monkeypatch.setattr(
            "app.utils.schema_guard.check_column_exists", lambda table, col: True
        )

        # Should not raise
        require_columns("emails", "category", "risk_score", "expires_at")

    def test_require_columns_fails_when_any_missing(self, monkeypatch):
        """Test that require_columns raises when any column is missing."""

        # Mock check_column_exists to return False for 'risk_score'
        def mock_check(table, col):
            return col != "risk_score"

        monkeypatch.setattr("app.utils.schema_guard.check_column_exists", mock_check)

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Missing required columns"):
            require_columns("emails", "category", "risk_score", "expires_at")


class TestBackfillScriptIntegration:
    """Integration tests for backfill scripts using schema guard."""

    def test_backfill_script_checks_schema_on_startup(self, monkeypatch):
        """Test that backfill_bill_dates.py checks schema before running."""
        # This is more of a documentation test - the actual check is in the script
        # We verify the pattern is correct

        # Mock get_current_migration
        monkeypatch.setattr(
            "app.utils.schema_guard.get_current_migration",
            lambda: "0009_add_emails_category",
        )

        # This is the pattern used in backfill_bill_dates.py
        try:
            require_min_migration("0009_add_emails_category", "emails.category column")
            schema_check_passed = True
        except RuntimeError:
            schema_check_passed = False

        assert schema_check_passed is True

    def test_backfill_script_exits_on_old_schema(self, monkeypatch):
        """Test that backfill script would exit on old schema."""
        # Mock old version
        monkeypatch.setattr(
            "app.utils.schema_guard.get_current_migration",
            lambda: "0008_approvals_proposed",
        )

        # This is the pattern used in backfill_bill_dates.py
        try:
            require_min_migration("0009_add_emails_category", "emails.category column")
            schema_check_passed = True
        except RuntimeError as e:
            schema_check_passed = False
            error_message = str(e)

        assert schema_check_passed is False
        assert "Database schema is too old" in error_message
        assert "0009_add_emails_category" in error_message
