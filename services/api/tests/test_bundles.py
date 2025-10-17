"""Tests for config bundle management.

Tests:
- Bundle creation from trained models
- Proposal workflow
- Approval and rejection
- Apply with canary
- Rollback
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

from app.active.bundles import BundleManager
from app.models import RuntimeSetting, AgentApproval


class TestBundleManager:
    """Test config bundle management."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def sample_bundle(self):
        """Sample config bundle."""
        return {
            "agent": "inbox_triage",
            "version": "v1",
            "created_at": datetime.utcnow().isoformat(),
            "training_count": 100,
            "accuracy": 0.85,
            "thresholds": {
                "risk_score_threshold": 65.0,
                "spf_dkim_weight": 1.5
            }
        }
    
    def test_create_bundle(self, mock_db):
        """Should create bundle from training."""
        manager = BundleManager(mock_db)
        
        sample_bundle = {
            "agent": "inbox_triage",
            "accuracy": 0.85,
            "thresholds": {"risk_score_threshold": 65.0}
        }
        
        with patch('app.active.bundles.HeuristicTrainer') as mock_trainer_class:
            mock_trainer = Mock()
            mock_trainer.train_for_agent.return_value = sample_bundle
            mock_trainer_class.return_value = mock_trainer
            
            bundle = manager.create_bundle("inbox_triage", min_examples=50)
        
        assert bundle is not None
        assert "bundle_id" in bundle
        assert bundle["status"] == "pending"
        assert bundle["agent"] == "inbox_triage"
        assert mock_db.add.called
        assert mock_db.commit.called
    
    def test_create_bundle_insufficient_data(self, mock_db):
        """Should return None if insufficient data."""
        manager = BundleManager(mock_db)
        
        with patch('app.active.bundles.HeuristicTrainer') as mock_trainer_class:
            mock_trainer = Mock()
            mock_trainer.train_for_agent.return_value = None
            mock_trainer_class.return_value = mock_trainer
            
            bundle = manager.create_bundle("inbox_triage")
        
        assert bundle is None
    
    def test_propose_bundle(self, mock_db, sample_bundle):
        """Should create approval request for bundle."""
        manager = BundleManager(mock_db)
        
        # Mock bundle loading
        with patch.object(manager, '_load_bundle') as mock_load:
            mock_load.return_value = sample_bundle
            
            with patch.object(manager, '_load_active_bundle') as mock_load_active:
                mock_load_active.return_value = None  # No current bundle
                
                with patch('app.active.bundles.HeuristicTrainer') as mock_trainer_class:
                    mock_trainer = Mock()
                    mock_trainer.generate_diff.return_value = {"type": "initial"}
                    mock_trainer_class.return_value = mock_trainer
                    
                    approval_id = manager.propose_bundle("inbox_triage", "bundle_123", proposer="admin")
        
        assert mock_db.add.called
        assert mock_db.commit.called
    
    def test_approve_bundle(self, mock_db):
        """Should approve pending bundle."""
        manager = BundleManager(mock_db)
        
        # Mock approval
        approval = Mock(spec=AgentApproval)
        approval.id = "approval-123"
        approval.status = "pending"
        approval.agent = "inbox_triage"
        approval.context = {"bundle_id": "bundle_123"}
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = approval
        
        manager.approve_bundle("approval-123", approver="admin", rationale="Looks good")
        
        assert approval.status == "approved"
        assert approval.approved_by == "admin"
        assert approval.rationale == "Looks good"
        assert mock_db.commit.called
    
    def test_approve_bundle_not_pending(self, mock_db):
        """Should reject approval of non-pending bundle."""
        manager = BundleManager(mock_db)
        
        approval = Mock(spec=AgentApproval)
        approval.status = "approved"
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = approval
        
        with pytest.raises(ValueError, match="not pending"):
            manager.approve_bundle("approval-123", approver="admin")
    
    def test_apply_approved_bundle(self, mock_db, sample_bundle):
        """Should apply approved bundle."""
        manager = BundleManager(mock_db)
        
        # Mock approval
        approval = Mock(spec=AgentApproval)
        approval.id = "approval-123"
        approval.status = "approved"
        approval.agent = "inbox_triage"
        approval.context = {
            "bundle_id": "bundle_123",
            "bundle": sample_bundle
        }
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = approval
        
        with patch.object(manager, '_backup_active_bundle'):
            with patch.object(manager, '_apply_bundle'):
                manager.apply_approved_bundle("approval-123")
        
        assert mock_db.commit.called
        assert "applied_at" in approval.context
    
    def test_apply_approved_bundle_with_canary(self, mock_db, sample_bundle):
        """Should apply bundle as canary."""
        manager = BundleManager(mock_db)
        
        approval = Mock(spec=AgentApproval)
        approval.status = "approved"
        approval.agent = "inbox_triage"
        approval.context = {
            "bundle_id": "bundle_123",
            "bundle": sample_bundle
        }
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = approval
        
        with patch.object(manager, '_backup_active_bundle'):
            with patch.object(manager, '_apply_as_canary'):
                manager.apply_approved_bundle("approval-123", canary_percent=10)
        
        assert approval.context["canary_percent"] == 10
    
    def test_rollback_bundle(self, mock_db, sample_bundle):
        """Should rollback to backup config."""
        manager = BundleManager(mock_db)
        
        with patch.object(manager, '_load_backup_bundle') as mock_load_backup:
            mock_load_backup.return_value = sample_bundle
            
            with patch.object(manager, '_apply_bundle') as mock_apply:
                manager.rollback_bundle("inbox_triage")
        
        assert mock_apply.called
    
    def test_rollback_bundle_no_backup(self, mock_db):
        """Should raise error if no backup."""
        manager = BundleManager(mock_db)
        
        with patch.object(manager, '_load_backup_bundle') as mock_load_backup:
            mock_load_backup.return_value = None
            
            with pytest.raises(ValueError, match="No backup"):
                manager.rollback_bundle("inbox_triage")
    
    def test_list_pending_approvals(self, mock_db):
        """Should list all pending approvals."""
        manager = BundleManager(mock_db)
        
        # Mock approvals
        approval1 = Mock(spec=AgentApproval)
        approval1.id = "approval-1"
        approval1.agent = "inbox_triage"
        approval1.context = {"bundle_id": "bundle_123", "diff": {}}
        approval1.requested_by = "admin"
        approval1.created_at = datetime.utcnow()
        
        approval2 = Mock(spec=AgentApproval)
        approval2.id = "approval-2"
        approval2.agent = "insights_writer"
        approval2.context = {"bundle_id": "bundle_456", "diff": {}}
        approval2.requested_by = "system"
        approval2.created_at = datetime.utcnow()
        
        query_mock = Mock()
        query_mock.filter_by.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [approval1, approval2]
        
        mock_db.query.return_value = query_mock
        
        approvals = manager.list_pending_approvals()
        
        assert len(approvals) == 2
        assert approvals[0]["id"] == "approval-1"
        assert approvals[0]["agent"] == "inbox_triage"
