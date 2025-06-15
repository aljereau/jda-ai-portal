"""
Unit tests for Block 4 Project Tracking Integration functionality.
Tests project status, phase advancement, milestone management, and project lifecycle.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.proposal_service import ProposalService, ProposalServiceError
from app.models.proposal import (
    Proposal, ProjectTracker, ProposalAuditLog,
    ProjectPhaseEnum, ProposalStatusEnum, AuditActionEnum
)
from app.models.user import User, UserRole


class TestProposalServiceBlock4:
    """Test class for Block 4 project tracking functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def proposal_service(self, mock_db):
        """Create proposal service instance."""
        return ProposalService(mock_db)

    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        return User(
            id=1,
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role=UserRole.PROJECT_MANAGER
        )

    @pytest.fixture
    def sample_proposal(self, sample_user):
        """Create sample proposal for testing."""
        return Proposal(
            id=1,
            project_name="Test Project",
            client_name="Test Client",
            phase=ProjectPhaseEnum.EXPLORATORY,
            status=ProposalStatusEnum.DRAFT,
            created_by=sample_user.id,
            share_token="test-share-token-123"
        )

    @pytest.fixture
    def sample_project_tracker(self, sample_proposal, sample_user):
        """Create sample project tracker for testing."""
        return ProjectTracker(
            id=1,
            proposal_id=sample_proposal.id,
            project_name=sample_proposal.project_name,
            client_name=sample_proposal.client_name,
            current_phase=ProjectPhaseEnum.EXPLORATORY,
            exploratory_completed=False,
            discovery_completed=False,
            development_completed=False,
            deployment_completed=False,
            created_by=sample_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    def test_get_detailed_project_status_success(self, proposal_service, mock_db, sample_proposal, sample_project_tracker):
        """Test successful retrieval of detailed project status."""
        # Setup
        proposal_service.get_proposal = Mock(return_value=sample_proposal)
        proposal_service.get_project_tracker = Mock(return_value=sample_project_tracker)
        proposal_service._get_phase_milestones = Mock(return_value=[
            {"name": "Initial Client Meeting", "description": "Conduct discovery meeting with client"},
            {"name": "Requirements Gathering", "description": "Document initial requirements and scope"}
        ])

        # Execute
        result = proposal_service.get_detailed_project_status(1)

        # Verify
        assert result["proposal_id"] == 1
        assert result["project_name"] == "Test Project"
        assert result["client_name"] == "Test Client"
        assert result["current_phase"] == "exploratory"
        assert result["next_phase"] == "exploratory"  # Since exploratory not completed
        assert result["progress_percentage"] == 0.0  # No phases completed
        assert len(result["phases"]) == 4
        assert result["phases"]["exploratory"]["is_current"] is True
        assert result["phases"]["exploratory"]["completed"] is False
        assert len(result["milestones"]) == 2

    def test_get_detailed_project_status_proposal_not_found(self, proposal_service, mock_db):
        """Test project status retrieval when proposal not found."""
        # Setup
        proposal_service.get_proposal = Mock(return_value=None)

        # Execute & Verify
        with pytest.raises(ProposalServiceError, match="Proposal 999 not found"):
            proposal_service.get_detailed_project_status(999)

    def test_get_detailed_project_status_tracker_not_found(self, proposal_service, mock_db, sample_proposal):
        """Test project status retrieval when tracker not found."""
        # Setup
        proposal_service.get_proposal = Mock(return_value=sample_proposal)
        proposal_service.get_project_tracker = Mock(return_value=None)

        # Execute & Verify
        with pytest.raises(ProposalServiceError, match="Project tracker not found"):
            proposal_service.get_detailed_project_status(1)

    def test_advance_project_phase_exploratory_to_discovery(self, proposal_service, mock_db, sample_proposal, sample_project_tracker):
        """Test advancing project from exploratory to discovery phase."""
        # Setup
        proposal_service.get_project_tracker = Mock(return_value=sample_project_tracker)
        proposal_service.get_proposal = Mock(return_value=sample_proposal)
        proposal_service.get_detailed_project_status = Mock(return_value={"status": "updated"})
        proposal_service._log_audit_action = Mock()
        mock_db.commit.return_value = None

        # Execute
        result = proposal_service.advance_project_phase(1, "Exploratory phase completed", 1)

        # Verify
        assert sample_project_tracker.exploratory_completed is True
        assert sample_project_tracker.current_phase == ProjectPhaseEnum.DISCOVERY
        assert sample_proposal.phase == ProjectPhaseEnum.DISCOVERY
        mock_db.commit.assert_called_once()
        proposal_service._log_audit_action.assert_called_once()

    def test_advance_project_phase_development_to_deployment(self, proposal_service, mock_db, sample_proposal):
        """Test advancing project from development to deployment phase."""
        # Setup
        tracker = ProjectTracker(
            id=1,
            proposal_id=1,
            project_name="Test Project",
            client_name="Test Client",
            current_phase=ProjectPhaseEnum.DEVELOPMENT,
            exploratory_completed=True,
            discovery_completed=True,
            development_completed=False,
            deployment_completed=False,
            created_by=1
        )
        
        proposal_service.get_project_tracker = Mock(return_value=tracker)
        proposal_service.get_proposal = Mock(return_value=sample_proposal)
        proposal_service.get_detailed_project_status = Mock(return_value={"status": "updated"})
        proposal_service._log_audit_action = Mock()
        mock_db.commit.return_value = None

        # Execute
        result = proposal_service.advance_project_phase(1, "Development phase completed", 1)

        # Verify
        assert tracker.development_completed is True
        assert tracker.current_phase == ProjectPhaseEnum.DEPLOYMENT
        assert sample_proposal.phase == ProjectPhaseEnum.DEPLOYMENT

    def test_advance_project_phase_deployment_completion(self, proposal_service, mock_db, sample_proposal):
        """Test completing the final deployment phase."""
        # Setup
        tracker = ProjectTracker(
            id=1,
            proposal_id=1,
            project_name="Test Project",
            client_name="Test Client",
            current_phase=ProjectPhaseEnum.DEPLOYMENT,
            exploratory_completed=True,
            discovery_completed=True,
            development_completed=True,
            deployment_completed=False,
            created_by=1
        )
        
        proposal_service.get_project_tracker = Mock(return_value=tracker)
        proposal_service.get_proposal = Mock(return_value=sample_proposal)
        proposal_service.get_detailed_project_status = Mock(return_value={"status": "completed"})
        proposal_service._log_audit_action = Mock()
        mock_db.commit.return_value = None

        # Execute
        result = proposal_service.advance_project_phase(1, "Project completed", 1)

        # Verify
        assert tracker.deployment_completed is True
        assert tracker.actual_completion is not None
        # Phase should remain deployment when project is complete

    def test_advance_project_phase_tracker_not_found(self, proposal_service, mock_db):
        """Test phase advancement when tracker not found."""
        # Setup
        proposal_service.get_project_tracker = Mock(return_value=None)

        # Execute & Verify
        with pytest.raises(ProposalServiceError, match="Project tracker not found"):
            proposal_service.advance_project_phase(1)

    def test_update_project_milestone_success(self, proposal_service, mock_db, sample_project_tracker):
        """Test successful milestone update."""
        # Setup
        proposal_service.get_project_tracker = Mock(return_value=sample_project_tracker)
        proposal_service._log_audit_action = Mock()
        proposal_service._get_phase_milestones = Mock(return_value=[
            {"name": "Initial Client Meeting", "description": "Conduct discovery meeting"},
            {"name": "Requirements Gathering", "description": "Document requirements"}
        ])
        proposal_service._calculate_milestone_impact = Mock(return_value={
            "milestone_progress": 1.0,
            "phase_milestone_count": 2,
            "estimated_phase_impact": 50.0
        })

        # Execute
        result = proposal_service.update_project_milestone(
            1, "Initial Client Meeting", "completed", "Meeting went well", 1
        )

        # Verify
        assert result["proposal_id"] == 1
        assert result["milestone"]["milestone_name"] == "Initial Client Meeting"
        assert result["milestone"]["status"] == "completed"
        assert result["milestone"]["notes"] == "Meeting went well"
        assert result["current_phase"] == "exploratory"
        assert result["project_name"] == "Test Project"
        proposal_service._log_audit_action.assert_called_once()

    def test_update_project_milestone_invalid_status(self, proposal_service, mock_db, sample_project_tracker):
        """Test milestone update with invalid status."""
        # Setup
        proposal_service.get_project_tracker = Mock(return_value=sample_project_tracker)

        # Execute & Verify
        with pytest.raises(ProposalServiceError, match="Invalid milestone status: invalid_status"):
            proposal_service.update_project_milestone(1, "Test Milestone", "invalid_status")

    def test_update_project_milestone_tracker_not_found(self, proposal_service, mock_db):
        """Test milestone update when tracker not found."""
        # Setup
        proposal_service.get_project_tracker = Mock(return_value=None)

        # Execute & Verify
        with pytest.raises(ProposalServiceError, match="Project tracker not found"):
            proposal_service.update_project_milestone(1, "Test Milestone", "completed")

    def test_get_phase_milestones_exploratory(self, proposal_service):
        """Test getting milestones for exploratory phase."""
        # Execute
        milestones = proposal_service._get_phase_milestones("exploratory")

        # Verify
        assert len(milestones) == 4
        assert milestones[0]["name"] == "Initial Client Meeting"
        assert milestones[1]["name"] == "Requirements Gathering"
        assert milestones[2]["name"] == "Feasibility Assessment"
        assert milestones[3]["name"] == "Proposal Creation"

    def test_get_phase_milestones_discovery(self, proposal_service):
        """Test getting milestones for discovery phase."""
        # Execute
        milestones = proposal_service._get_phase_milestones("discovery")

        # Verify
        assert len(milestones) == 4
        assert milestones[0]["name"] == "Detailed Requirements"
        assert milestones[1]["name"] == "Architecture Design"
        assert milestones[2]["name"] == "Technology Stack Selection"
        assert milestones[3]["name"] == "Project Planning"

    def test_get_phase_milestones_development(self, proposal_service):
        """Test getting milestones for development phase."""
        # Execute
        milestones = proposal_service._get_phase_milestones("development")

        # Verify
        assert len(milestones) == 4
        assert milestones[0]["name"] == "Development Environment Setup"
        assert milestones[1]["name"] == "Core Functionality Implementation"
        assert milestones[2]["name"] == "Integration Testing"
        assert milestones[3]["name"] == "User Acceptance Testing"

    def test_get_phase_milestones_deployment(self, proposal_service):
        """Test getting milestones for deployment phase."""
        # Execute
        milestones = proposal_service._get_phase_milestones("deployment")

        # Verify
        assert len(milestones) == 4
        assert milestones[0]["name"] == "Production Environment Setup"
        assert milestones[1]["name"] == "System Deployment"
        assert milestones[2]["name"] == "Go-Live Support"
        assert milestones[3]["name"] == "Project Handover"

    def test_get_phase_milestones_unknown_phase(self, proposal_service):
        """Test getting milestones for unknown phase."""
        # Execute
        milestones = proposal_service._get_phase_milestones("unknown_phase")

        # Verify
        assert milestones == []

    @pytest.mark.parametrize("milestone_status,expected_weight", [
        ("not_started", 0),
        ("in_progress", 0.5),
        ("completed", 1.0),
        ("blocked", -0.2)
    ])
    def test_calculate_milestone_impact(self, proposal_service, milestone_status, expected_weight):
        """Test milestone impact calculation for different statuses."""
        # Setup
        phase_milestones = [
            {"name": "Milestone 1", "description": "First milestone"},
            {"name": "Milestone 2", "description": "Second milestone"}
        ]

        # Execute
        impact = proposal_service._calculate_milestone_impact(
            "Test Milestone", milestone_status, phase_milestones
        )

        # Verify
        assert impact["milestone_progress"] == expected_weight
        assert impact["phase_milestone_count"] == 2
        assert impact["estimated_phase_impact"] == (expected_weight / 2) * 100

    def test_project_progress_calculation(self, proposal_service, mock_db, sample_proposal):
        """Test project progress calculation with multiple completed phases."""
        # Setup
        tracker = ProjectTracker(
            id=1,
            proposal_id=1,
            project_name="Test Project",
            client_name="Test Client",
            current_phase=ProjectPhaseEnum.DEVELOPMENT,
            exploratory_completed=True,
            discovery_completed=True,
            development_completed=False,
            deployment_completed=False,
            created_by=1
        )
        
        proposal_service.get_proposal = Mock(return_value=sample_proposal)
        proposal_service.get_project_tracker = Mock(return_value=tracker)
        proposal_service._get_phase_milestones = Mock(return_value=[])

        # Execute
        result = proposal_service.get_detailed_project_status(1)

        # Verify
        assert result["progress_percentage"] == 50.0  # 2 out of 4 phases completed
        assert result["next_phase"] == "development"  # Current phase not completed yet
        assert result["phases"]["exploratory"]["completed"] is True
        assert result["phases"]["discovery"]["completed"] is True
        assert result["phases"]["development"]["completed"] is False
        assert result["phases"]["development"]["is_current"] is True

    def test_error_handling_database_failure(self, proposal_service, mock_db):
        """Test error handling when database operations fail."""
        # Setup
        mock_db.commit.side_effect = Exception("Database error")
        proposal_service.get_project_tracker = Mock(return_value=Mock())

        # Execute & Verify
        with pytest.raises(ProposalServiceError, match="Failed to advance project phase"):
            proposal_service.advance_project_phase(1, performed_by=1)

    def test_audit_logging_for_phase_advancement(self, proposal_service, mock_db, sample_project_tracker):
        """Test that audit logging works correctly for phase advancement."""
        # Setup
        proposal_service.get_project_tracker = Mock(return_value=sample_project_tracker)
        proposal_service.get_proposal = Mock(return_value=Mock())
        proposal_service.get_detailed_project_status = Mock(return_value={})
        proposal_service._log_audit_action = Mock()
        mock_db.commit.return_value = None

        # Execute
        proposal_service.advance_project_phase(1, "Phase completed successfully", 1)

        # Verify audit logging
        proposal_service._log_audit_action.assert_called_once()
        call_args = proposal_service._log_audit_action.call_args
        assert call_args[0][0] == 1  # proposal_id
        assert call_args[0][1] == AuditActionEnum.STATUS_CHANGED  # action
        assert call_args[0][2] == 1  # performed_by
        assert "Advanced project from exploratory to discovery" in call_args[0][3]  # description

    def test_milestone_status_validation(self, proposal_service, mock_db, sample_project_tracker):
        """Test validation of milestone status values."""
        # Setup
        proposal_service.get_project_tracker = Mock(return_value=sample_project_tracker)

        # Test valid statuses
        valid_statuses = ["not_started", "in_progress", "completed", "blocked"]
        for status in valid_statuses:
            proposal_service._log_audit_action = Mock()
            proposal_service._get_phase_milestones = Mock(return_value=[])
            proposal_service._calculate_milestone_impact = Mock(return_value={})
            
            # Should not raise exception
            result = proposal_service.update_project_milestone(1, "Test", status)
            assert result["milestone"]["status"] == status

        # Test invalid status
        with pytest.raises(ProposalServiceError, match="Invalid milestone status"):
            proposal_service.update_project_milestone(1, "Test", "invalid_status") 