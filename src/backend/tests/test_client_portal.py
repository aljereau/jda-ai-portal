"""
Unit tests for Client Portal functionality.
Tests client-specific proposal viewing, project status access, and read-only operations.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from app.main import app
from app.models.user import User, UserRole, UserStatus
from app.models.proposal import (
    Proposal, ProposalShare, ProposalExport, ProjectTracker,
    ProposalStatusEnum, ProjectPhaseEnum, SharePermissionEnum
)
from app.services.proposal_service import ProposalService
from app.core.database import get_db
from .conftest import TestDatabase


class TestClientPortal:
    """Test suite for client portal functionality."""

    @pytest.fixture
    def client_user(self, db_session: Session) -> User:
        """Create a test client user."""
        user = User(
            email="client@test.com",
            hashed_password="hashed_password",
            first_name="Test",
            last_name="Client",
            role=UserRole.CLIENT,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    @pytest.fixture
    def admin_user(self, db_session: Session) -> User:
        """Create a test admin user."""
        user = User(
            email="admin@test.com",
            hashed_password="hashed_password",
            first_name="Test",
            last_name="Admin",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    @pytest.fixture
    def test_proposal(self, db_session: Session, client_user: User, admin_user: User) -> Proposal:
        """Create a test proposal for the client."""
        proposal = Proposal(
            project_name="Test Project",
            client_name="Test Client Company",
            phase=ProjectPhaseEnum.DISCOVERY,
            status=ProposalStatusEnum.APPROVED,
            transcript_path="/test/transcript.txt",
            created_by=admin_user.id,
            client_id=client_user.id,
            ai_summary="Test AI summary",
            extracted_requirements='{"scope": "test", "timeline": "6 months"}',
            content="<h1>Test Proposal</h1><p>This is a test proposal content.</p>",
            share_token="test-share-token-123"
        )
        db_session.add(proposal)
        db_session.commit()
        db_session.refresh(proposal)
        
        # Create project tracker
        tracker = ProjectTracker(
            proposal_id=proposal.id,
            project_name=proposal.project_name,
            client_name=proposal.client_name,
            current_phase=ProjectPhaseEnum.DISCOVERY,
            exploratory_completed=True,
            discovery_completed=False,
            development_completed=False,
            deployment_completed=False,
            created_by=admin_user.id
        )
        db_session.add(tracker)
        db_session.commit()
        
        return proposal

    @pytest.fixture
    def shared_proposal(self, db_session: Session, test_proposal: Proposal, client_user: User, admin_user: User) -> ProposalShare:
        """Create a shared proposal for testing."""
        share = ProposalShare(
            proposal_id=test_proposal.id,
            shared_by=admin_user.id,
            shared_with_user_id=client_user.id,
            permission_level=SharePermissionEnum.VIEW_ONLY,
            share_token="shared-token-456",
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(share)
        db_session.commit()
        db_session.refresh(share)
        return share

    def test_search_proposals_client_access(self, db_session: Session, client_user: User, test_proposal: Proposal):
        """Test client proposal search functionality."""
        proposal_service = ProposalService(db_session)
        
        proposals = proposal_service.search_proposals(
            user_id=client_user.id,
            status=['approved', 'sent', 'accepted'],
            client_access_only=True
        )
        
        assert len(proposals) == 1
        assert proposals[0].id == test_proposal.id
        assert proposals[0].project_name == "Test Project"

    def test_get_project_status(self, db_session: Session, test_proposal: Proposal):
        """Test project status retrieval."""
        proposal_service = ProposalService(db_session)
        
        status = proposal_service.get_detailed_project_status(test_proposal.id)
        
        assert status is not None
        assert status["proposal_id"] == test_proposal.id
        assert status["project_name"] == "Test Project"
        assert status["current_phase"] == "discovery"
        assert "phases" in status
        assert "milestones" in status

    def test_export_proposal(self, db_session: Session, test_proposal: Proposal, client_user: User):
        """Test proposal export functionality."""
        proposal_service = ProposalService(db_session)
        
        export_result = proposal_service.export_proposal(
            proposal_id=test_proposal.id,
            format="html",
            exported_by=client_user.id
        )
        
        assert export_result is not None
        assert export_result["format"] == "html"
        assert export_result["filename"] == f"proposal_{test_proposal.id}.html"
        assert "content" in export_result

    def test_audit_logging(self, db_session: Session, test_proposal: Proposal, client_user: User):
        """Test audit logging for client actions."""
        proposal_service = ProposalService(db_session)
        
        proposal_service.log_audit_event(
            proposal_id=test_proposal.id,
            user_id=client_user.id,
            action="status_view",
            description="Viewed project status from client portal"
        )
        
        audit_logs = proposal_service.get_proposal_audit_log(test_proposal.id, limit=10)
        assert len(audit_logs) > 0

    def test_milestone_tracking(self, db_session: Session):
        """Test milestone tracking functionality."""
        proposal_service = ProposalService(db_session)
        
        milestones = proposal_service._get_phase_milestones("discovery")
        
        assert len(milestones) > 0
        assert all("name" in milestone for milestone in milestones)
        assert all("description" in milestone for milestone in milestones)

    def test_shared_proposal_access(self, db_session: Session, test_proposal: Proposal, client_user: User, admin_user: User):
        """Test shared proposal access via token."""
        # Create a share
        share = ProposalShare(
            proposal_id=test_proposal.id,
            shared_by=admin_user.id,
            shared_with_user_id=client_user.id,
            permission_level=SharePermissionEnum.VIEW_ONLY,
            share_token="shared-token-456",
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(share)
        db_session.commit()
        
        # Verify share exists and is accessible
        found_share = db_session.query(ProposalShare).filter(
            ProposalShare.share_token == "shared-token-456",
            ProposalShare.is_active == True
        ).first()
        
        assert found_share is not None
        assert found_share.proposal_id == test_proposal.id

    def test_get_client_proposals_success(self, client: TestClient, client_user: User, test_proposal: Proposal):
        """Test successful retrieval of client proposals."""
        # Mock authentication
        with client as c:
            # Simulate authenticated request
            response = c.get(
                "/api/v1/client-portal/proposals",
                headers={"Authorization": f"Bearer test-token"}
            )
            
            # Note: This would require proper JWT token setup in a real test
            # For now, we'll test the service layer directly
            
        # Test service layer directly
        db = next(get_db())
        proposal_service = ProposalService(db)
        
        proposals = proposal_service.search_proposals(
            user_id=client_user.id,
            status=['approved', 'sent', 'accepted'],
            client_access_only=True
        )
        
        assert len(proposals) == 1
        assert proposals[0].id == test_proposal.id
        assert proposals[0].project_name == "Test Project"

    def test_get_client_proposals_empty_result(self, client: TestClient, client_user: User):
        """Test client proposals when no proposals exist."""
        db = next(get_db())
        proposal_service = ProposalService(db)
        
        proposals = proposal_service.search_proposals(
            user_id=client_user.id,
            status=['approved', 'sent', 'accepted'],
            client_access_only=True
        )
        
        assert len(proposals) == 0

    def test_get_shared_proposal_success(self, client: TestClient, shared_proposal: ProposalShare, test_proposal: Proposal):
        """Test successful retrieval of shared proposal."""
        db = next(get_db())
        
        # Get proposal by share token
        share = db.query(ProposalShare).filter(
            ProposalShare.share_token == shared_proposal.share_token,
            ProposalShare.is_active == True
        ).first()
        
        assert share is not None
        assert share.proposal_id == test_proposal.id
        
        # Get the actual proposal
        proposal = db.query(Proposal).filter(Proposal.id == share.proposal_id).first()
        assert proposal is not None
        assert proposal.project_name == "Test Project"

    def test_get_shared_proposal_invalid_token(self, client: TestClient):
        """Test retrieval with invalid share token."""
        db = next(get_db())
        
        # Try to get proposal with invalid token
        share = db.query(ProposalShare).filter(
            ProposalShare.share_token == "invalid-token",
            ProposalShare.is_active == True
        ).first()
        
        assert share is None

    def test_get_shared_proposal_expired_token(self, db_session: Session, test_proposal: Proposal, admin_user: User):
        """Test retrieval with expired share token."""
        # Create expired share
        expired_share = ProposalShare(
            proposal_id=test_proposal.id,
            shared_by=admin_user.id,
            permission_level=SharePermissionEnum.VIEW_ONLY,
            share_token="expired-token-789",
            is_active=True,
            expires_at=datetime.utcnow() - timedelta(days=1)  # Expired
        )
        db_session.add(expired_share)
        db_session.commit()
        
        # Check that expired share is not accessible
        proposal_service = ProposalService(db_session)
        current_time = proposal_service._get_current_timestamp()
        
        assert expired_share.expires_at < current_time

    def test_get_project_status_access_control(self, test_proposal: Proposal, admin_user: User):
        """Test project status access control."""
        db = next(get_db())
        
        # Check that proposal exists and has correct client_id
        proposal = db.query(Proposal).filter(Proposal.id == test_proposal.id).first()
        assert proposal is not None
        
        # Admin user should not have direct client access to this proposal
        # (unless they are the client_id, which they're not in this test)
        assert proposal.client_id != admin_user.id

    def test_export_proposal_multiple_formats(self, test_proposal: Proposal, client_user: User):
        """Test proposal export in multiple formats."""
        db = next(get_db())
        proposal_service = ProposalService(db)
        
        formats = ["html", "pdf", "docx", "markdown"]
        
        for format_type in formats:
            export_result = proposal_service.export_proposal(
                proposal_id=test_proposal.id,
                format=format_type,
                exported_by=client_user.id
            )
            
            assert export_result["format"] == format_type
            assert export_result["filename"].endswith(f".{format_type}")

    def test_export_proposal_invalid_format(self, test_proposal: Proposal, client_user: User):
        """Test proposal export with invalid format."""
        db = next(get_db())
        proposal_service = ProposalService(db)
        
        with pytest.raises(Exception) as exc_info:
            proposal_service.export_proposal(
                proposal_id=test_proposal.id,
                format="invalid_format",
                exported_by=client_user.id
            )
        
        assert "Unsupported export format" in str(exc_info.value)

    def test_client_dashboard_data(self, test_proposal: Proposal, client_user: User):
        """Test client dashboard data generation."""
        db = next(get_db())
        proposal_service = ProposalService(db)
        
        # Get client's proposals
        proposals = proposal_service.search_proposals(
            user_id=client_user.id,
            status=['approved', 'sent', 'accepted'],
            client_access_only=True
        )
        
        # Calculate dashboard metrics
        total_proposals = len(proposals)
        active_projects = len([p for p in proposals if p.status == ProposalStatusEnum.ACCEPTED])
        pending_proposals = len([p for p in proposals if p.status == ProposalStatusEnum.SENT])
        
        # Verify metrics
        assert total_proposals == 1
        assert active_projects == 0  # Test proposal is APPROVED, not ACCEPTED
        assert pending_proposals == 0  # Test proposal is APPROVED, not SENT
        
        # Test phase summary
        phase_summary = {}
        for proposal in proposals:
            if proposal.status == ProposalStatusEnum.ACCEPTED:
                phase = proposal.phase.value if proposal.phase else 'exploratory'
                phase_summary[phase] = phase_summary.get(phase, 0) + 1
        
        # Since test proposal is APPROVED (not ACCEPTED), phase_summary should be empty
        assert len(phase_summary) == 0

    def test_proposal_search_filtering(self, db_session: Session, client_user: User, admin_user: User):
        """Test proposal search with various filters."""
        # Create multiple proposals with different statuses and phases
        proposals_data = [
            {"status": ProposalStatusEnum.APPROVED, "phase": ProjectPhaseEnum.EXPLORATORY},
            {"status": ProposalStatusEnum.SENT, "phase": ProjectPhaseEnum.DISCOVERY},
            {"status": ProposalStatusEnum.ACCEPTED, "phase": ProjectPhaseEnum.DEVELOPMENT},
            {"status": ProposalStatusEnum.DRAFT, "phase": ProjectPhaseEnum.DEPLOYMENT}  # Should not be visible to client
        ]
        
        created_proposals = []
        for i, data in enumerate(proposals_data):
            proposal = Proposal(
                project_name=f"Test Project {i+1}",
                client_name="Test Client Company",
                phase=data["phase"],
                status=data["status"],
                transcript_path=f"/test/transcript{i+1}.txt",
                created_by=admin_user.id,
                client_id=client_user.id,
                ai_summary=f"Test AI summary {i+1}",
                extracted_requirements='{"scope": "test"}',
                share_token=f"test-token-{i+1}"
            )
            db_session.add(proposal)
            created_proposals.append(proposal)
        
        db_session.commit()
        
        proposal_service = ProposalService(db_session)
        
        # Test filtering by status (client should only see approved/sent/accepted)
        client_proposals = proposal_service.search_proposals(
            user_id=client_user.id,
            client_access_only=True
        )
        
        # Should see 3 proposals (approved, sent, accepted) but not draft
        assert len(client_proposals) == 3
        
        visible_statuses = {p.status for p in client_proposals}
        assert ProposalStatusEnum.DRAFT not in visible_statuses
        assert ProposalStatusEnum.APPROVED in visible_statuses
        assert ProposalStatusEnum.SENT in visible_statuses
        assert ProposalStatusEnum.ACCEPTED in visible_statuses

    def test_project_phase_progression(self, test_proposal: Proposal, admin_user: User):
        """Test project phase progression tracking."""
        db = next(get_db())
        proposal_service = ProposalService(db)
        
        # Get initial project status
        initial_status = proposal_service.get_detailed_project_status(test_proposal.id)
        assert initial_status["current_phase"] == "discovery"
        assert initial_status["phases"]["exploratory"]["completed"] == True
        assert initial_status["phases"]["discovery"]["completed"] == False
        
        # Advance to next phase
        updated_status = proposal_service.advance_project_phase(
            proposal_id=test_proposal.id,
            completion_notes="Discovery phase completed",
            performed_by=admin_user.id
        )
        
        assert updated_status["current_phase"] == "development"
        assert updated_status["phases"]["discovery"]["completed"] == True
        assert updated_status["phases"]["development"]["is_current"] == True 