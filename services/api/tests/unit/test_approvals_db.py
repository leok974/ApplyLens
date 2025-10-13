"""
Unit tests for approvals database helpers.

These tests mock the database connection to verify the approval
workflow functions work correctly without needing a real database.
"""

import json
from unittest.mock import Mock, patch

import pytest


class TestApprovalsBulkInsert:
    """Tests for approvals_bulk_insert function."""

    def test_bulk_insert_single_row(self, monkeypatch):
        """Test inserting a single approval record."""
        # Mock SessionLocal
        mock_db = Mock()
        mock_execute = Mock()
        mock_db.execute = mock_execute
        mock_db.commit = Mock()
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        # Patch before import
        monkeypatch.setattr("app.db.SessionLocal", mock_session_local)
        from app.db import approvals_bulk_insert

        rows = [
            {
                "email_id": "e1",
                "action": "archive",
                "policy_id": "p1",
                "confidence": 0.9,
                "rationale": "expired",
                "params": {"x": 1},
            }
        ]

        approvals_bulk_insert(rows)

        # Verify execute was called once
        assert mock_execute.call_count == 1

        # Verify commit was called
        mock_db.commit.assert_called_once()

        # Verify close was called
        mock_db.close.assert_called_once()

    def test_bulk_insert_multiple_rows(self, monkeypatch):
        """Test inserting multiple approval records."""
        mock_db = Mock()
        mock_execute = Mock()
        mock_db.execute = mock_execute
        mock_db.commit = Mock()
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        with patch("app.db.SessionLocal", mock_session_local):
            from app.db import approvals_bulk_insert

            rows = [
                {
                    "email_id": f"e{i}",
                    "action": "archive",
                    "policy_id": "p1",
                    "confidence": 0.9,
                }
                for i in range(5)
            ]

            approvals_bulk_insert(rows)

            # Verify execute was called 5 times
            assert mock_execute.call_count == 5

            # Verify commit was called
            mock_db.commit.assert_called_once()

    def test_bulk_insert_with_optional_fields(self, monkeypatch):
        """Test inserting rows with optional rationale and params."""
        mock_db = Mock()
        mock_execute = Mock()
        mock_db.execute = mock_execute
        mock_db.commit = Mock()
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        with patch("app.db.SessionLocal", mock_session_local):
            from app.db import approvals_bulk_insert

            rows = [
                {
                    "email_id": "e1",
                    "action": "archive",
                    "policy_id": "p1",
                    "confidence": 0.9,
                    # No rationale or params
                }
            ]

            approvals_bulk_insert(rows)

            # Should not raise error
            assert mock_execute.call_count == 1

    def test_bulk_insert_rollback_on_error(self, monkeypatch):
        """Test that errors trigger rollback."""
        mock_db = Mock()
        mock_db.execute = Mock(side_effect=Exception("DB error"))
        mock_db.rollback = Mock()
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        with patch("app.db.SessionLocal", mock_session_local):
            from app.db import approvals_bulk_insert

            rows = [
                {
                    "email_id": "e1",
                    "action": "archive",
                    "policy_id": "p1",
                    "confidence": 0.9,
                }
            ]

            with pytest.raises(Exception):
                approvals_bulk_insert(rows)

            # Verify rollback was called
            mock_db.rollback.assert_called_once()


class TestApprovalsGet:
    """Tests for approvals_get function."""

    def test_get_proposed_status(self, monkeypatch):
        """Test retrieving proposed approvals."""
        # Mock result
        mock_row = (
            1,
            "e1",
            "archive",
            "p1",
            0.9,
            "expired",
            '{"x":1}',
            "proposed",
            "2025-10-10T00:00:00Z",
        )

        mock_result = Mock()
        mock_result.keys = Mock(
            return_value=[
                "id",
                "email_id",
                "action",
                "policy_id",
                "confidence",
                "rationale",
                "params",
                "status",
                "created_at",
            ]
        )
        mock_result.__iter__ = Mock(return_value=iter([mock_row]))

        mock_db = Mock()
        mock_db.execute = Mock(return_value=mock_result)
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        with patch("app.db.SessionLocal", mock_session_local):
            from app.db import approvals_get

            results = approvals_get(status="proposed", limit=200)

            assert len(results) == 1
            assert results[0]["email_id"] == "e1"
            assert results[0]["action"] == "archive"
            assert results[0]["status"] == "proposed"

    def test_get_custom_limit(self, monkeypatch):
        """Test custom limit parameter."""
        mock_result = Mock()
        mock_result.keys = Mock(
            return_value=[
                "id",
                "email_id",
                "action",
                "policy_id",
                "confidence",
                "rationale",
                "params",
                "status",
                "created_at",
            ]
        )
        mock_result.__iter__ = Mock(return_value=iter([]))

        mock_db = Mock()
        mock_db.execute = Mock(return_value=mock_result)
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        with patch("app.db.SessionLocal", mock_session_local):
            from app.db import approvals_get

            approvals_get(status="proposed", limit=50)

            # Verify the execute call included the limit
            call_args = mock_db.execute.call_args
            assert call_args[0][1]["limit"] == 50

    def test_get_empty_results(self, monkeypatch):
        """Test retrieving when no approvals exist."""
        mock_result = Mock()
        mock_result.keys = Mock(
            return_value=[
                "id",
                "email_id",
                "action",
                "policy_id",
                "confidence",
                "rationale",
                "params",
                "status",
                "created_at",
            ]
        )
        mock_result.__iter__ = Mock(return_value=iter([]))

        mock_db = Mock()
        mock_db.execute = Mock(return_value=mock_result)
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        with patch("app.db.SessionLocal", mock_session_local):
            from app.db import approvals_get

            results = approvals_get(status="proposed")

            assert len(results) == 0


class TestApprovalsUpdateStatus:
    """Tests for approvals_update_status function."""

    def test_update_single_id(self, monkeypatch):
        """Test updating status for a single approval."""
        mock_db = Mock()
        mock_db.execute = Mock()
        mock_db.commit = Mock()
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        with patch("app.db.SessionLocal", mock_session_local):
            from app.db import approvals_update_status

            approvals_update_status([1], "approved")

            # Verify execute was called
            mock_db.execute.assert_called_once()

            # Verify commit was called
            mock_db.commit.assert_called_once()

    def test_update_multiple_ids(self, monkeypatch):
        """Test updating status for multiple approvals."""
        mock_db = Mock()
        mock_db.execute = Mock()
        mock_db.commit = Mock()
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        with patch("app.db.SessionLocal", mock_session_local):
            from app.db import approvals_update_status

            approvals_update_status([1, 2, 3, 4, 5], "rejected")

            # Verify execute was called once (bulk update)
            mock_db.execute.assert_called_once()

            # Verify the IDs were passed
            call_args = mock_db.execute.call_args
            assert call_args[0][1]["ids"] == [1, 2, 3, 4, 5]
            assert call_args[0][1]["status"] == "rejected"

    def test_update_rollback_on_error(self, monkeypatch):
        """Test rollback on update error."""
        mock_db = Mock()
        mock_db.execute = Mock(side_effect=Exception("DB error"))
        mock_db.rollback = Mock()
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        with patch("app.db.SessionLocal", mock_session_local):
            from app.db import approvals_update_status

            with pytest.raises(Exception):
                approvals_update_status([1], "approved")

            # Verify rollback was called
            mock_db.rollback.assert_called_once()


class TestJSONHandling:
    """Tests for JSON/JSONB parameter handling."""

    def test_params_serialization(self, monkeypatch):
        """Test that params are properly JSON-serialized."""
        mock_db = Mock()

        captured_params = []

        def capture_execute(query, params):
            captured_params.append(params)

        mock_db.execute = capture_execute
        mock_db.commit = Mock()
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        with patch("app.db.SessionLocal", mock_session_local):
            from app.db import approvals_bulk_insert

            rows = [
                {
                    "email_id": "e1",
                    "action": "archive",
                    "policy_id": "p1",
                    "confidence": 0.9,
                    "params": {"nested": {"key": "value"}, "array": [1, 2, 3]},
                }
            ]

            approvals_bulk_insert(rows)

            # Verify params were JSON-serialized
            assert len(captured_params) == 1
            params_value = captured_params[0]["params"]
            # Should be a JSON string
            assert isinstance(params_value, str)
            # Should be parseable back to dict
            parsed = json.loads(params_value)
            assert parsed["nested"]["key"] == "value"
            assert parsed["array"] == [1, 2, 3]
