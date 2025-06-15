"""
Unit tests for team dashboard functionality.
Tests team management, analytics, proposal assignment, and bulk operations.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, UserRole
from app.models.proposal import Proposal, ProposalStatus
from app.services.team_service import TeamService
from app.schemas.team import (
    ProposalAssignment, BulkUpdateOperation, DashboardOverview,
    TeamAnalytics, ProposalAssignmentResponse, BulkUpdateResult
)

client = TestClient(app)


class TestTeamDashboardAPI:
    """Test cases for team dashboard API endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def admin_user(self):
        """Mock admin user."""
        user = Mock(spec=User)
        user.id = "admin_user_id"
        user.email = "admin@test.com"
        user.role = UserRole.ADMIN
        user.full_name = "Admin User"
        user.can_manage_users = True
        return user

    @pytest.fixture
    def project_manager_user(self):
        """Mock project manager user."""
        user = Mock(spec=User)
        user.id = "pm_user_id"
        user.email = "pm@test.com"
        user.role = UserRole.PROJECT_MANAGER
        user.full_name = "Project Manager"
        user.can_manage_users = True
        return user

    @pytest.fixture
    def client_user(self):
        """Mock client user."""
        user = Mock(spec=User)
        user.id = "client_user_id"
        user.email = "client@test.com"
        user.role = UserRole.CLIENT
        user.full_name = "Client User"
        user.can_manage_users = False
        return user

    @pytest.fixture
    def sample_proposals(self):
        """Sample proposal data."""
        proposals = []
        for i in range(5):
            proposal = Mock(spec=Proposal)
            proposal.id = f"proposal_{i}"
            proposal.title = f"Test Proposal {i}"
            proposal.status = ProposalStatus.DRAFT if i % 2 == 0 else ProposalStatus.IN_REVIEW
            proposal.created_at = datetime.utcnow() - timedelta(days=i)
            proposal.updated_at = datetime.utcnow() - timedelta(hours=i)
            proposal.creator_id = "admin_user_id"
            proposal.creator = Mock()
            proposal.creator.full_name = "Admin User"
            proposal.project_tracker = None
            proposals.append(proposal)
        return proposals

    @patch('app.api.v1.team_dashboard.get_current_user')
    @patch('app.api.v1.team_dashboard.get_db')
    def test_get_dashboard_overview_success(self, mock_get_db, mock_get_user, admin_user, mock_db):
        """Test successful dashboard overview retrieval."""
        mock_get_user.return_value = admin_user
        mock_get_db.return_value = mock_db

        with patch('app.api.v1.team_dashboard.TeamService') as mock_service:
            mock_overview = DashboardOverview(
                metrics=[],
                recent_proposals=[],
                team_analytics=TeamAnalytics(
                    total_proposals=10,
                    active_proposals=5,
                    completed_proposals=3,
                    proposals_this_month=2,
                    team_productivity={},
                    proposal_status_distribution={},
                    monthly_trends=[]
                ),
                user_activity=[],
                system_status={}
            )
            mock_service.return_value.get_dashboard_overview.return_value = mock_overview

            response = client.get(
                "/api/v1/team-dashboard/overview",
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data
            assert "team_analytics" in data
            assert data["team_analytics"]["total_proposals"] == 10

    @patch('app.api.v1.team_dashboard.get_current_user')
    @patch('app.api.v1.team_dashboard.get_db')
    def test_get_team_proposals_with_filters(self, mock_get_db, mock_get_user, admin_user, mock_db):
        """Test team proposals retrieval with filters."""
        mock_get_user.return_value = admin_user
        mock_get_db.return_value = mock_db

        with patch('app.api.v1.team_dashboard.TeamService') as mock_service:
            mock_service.return_value.get_team_proposals.return_value = []

            response = client.get(
                "/api/v1/team-dashboard/proposals?status_filter=draft&search=test",
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            mock_service.return_value.get_team_proposals.assert_called_once()

    @patch('app.api.v1.team_dashboard.require_role')
    @patch('app.api.v1.team_dashboard.get_db')
    def test_get_team_analytics_admin_only(self, mock_get_db, mock_require_role, admin_user, mock_db):
        """Test team analytics endpoint requires admin/PM role."""
        mock_require_role.return_value = admin_user
        mock_get_db.return_value = mock_db

        with patch('app.api.v1.team_dashboard.TeamService') as mock_service:
            mock_analytics = TeamAnalytics(
                total_proposals=15,
                active_proposals=8,
                completed_proposals=5,
                proposals_this_month=3,
                team_productivity={},
                proposal_status_distribution={},
                monthly_trends=[]
            )
            mock_service.return_value.get_team_analytics.return_value = mock_analytics

            response = client.get(
                "/api/v1/team-dashboard/analytics",
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_proposals"] == 15

    @patch('app.api.v1.team_dashboard.require_role')
    @patch('app.api.v1.team_dashboard.get_db')
    def test_assign_proposal_success(self, mock_get_db, mock_require_role, admin_user, mock_db):
        """Test successful proposal assignment."""
        mock_require_role.return_value = admin_user
        mock_get_db.return_value = mock_db

        assignment_data = {
            "proposal_id": "proposal_1",
            "user_id": "user_1",
            "notes": "Assignment notes"
        }

        with patch('app.api.v1.team_dashboard.TeamService') as mock_service:
            mock_response = ProposalAssignmentResponse(
                success=True,
                message="Assignment successful",
                assignment_id="assignment_1"
            )
            mock_service.return_value.assign_proposal_to_user.return_value = mock_response

            response = client.post(
                "/api/v1/team-dashboard/assign-proposal",
                json=assignment_data,
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "assignment_id" in data

    @patch('app.api.v1.team_dashboard.require_role')
    @patch('app.api.v1.team_dashboard.get_db')
    def test_bulk_update_proposals(self, mock_get_db, mock_require_role, admin_user, mock_db):
        """Test bulk update of proposals."""
        mock_require_role.return_value = admin_user
        mock_get_db.return_value = mock_db

        bulk_operation = {
            "operation_type": "status_update",
            "proposal_ids": ["proposal_1", "proposal_2"],
            "update_data": {"status": "approved"}
        }

        with patch('app.api.v1.team_dashboard.TeamService') as mock_service:
            mock_result = BulkUpdateResult(
                success=True,
                total_items=2,
                successful_updates=2,
                failed_updates=0,
                errors=[],
                updated_proposals=[]
            )
            mock_service.return_value.bulk_update_proposals.return_value = mock_result

            response = client.post(
                "/api/v1/team-dashboard/bulk-update",
                json=bulk_operation,
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["successful_updates"] == 2

    def test_client_user_cannot_access_analytics(self, client_user):
        """Test that client users cannot access analytics."""
        with patch('app.api.v1.team_dashboard.require_role') as mock_require_role:
            mock_require_role.side_effect = Exception("Insufficient permissions")

            response = client.get(
                "/api/v1/team-dashboard/analytics",
                headers={"Authorization": "Bearer test_token"}
            )

            # The require_role decorator should prevent access
            assert response.status_code != 200


class TestTeamService:
    """Test cases for TeamService business logic."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def team_service(self, mock_db):
        """TeamService instance with mocked database."""
        return TeamService(mock_db)

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        user = Mock(spec=User)
        user.id = "test_user_id"
        user.role = UserRole.ADMIN
        user.full_name = "Test User"
        return user

    def test_get_dashboard_overview_admin(self, team_service, mock_db):
        """Test dashboard overview generation for admin user."""
        # Mock database queries
        mock_db.query.return_value.count.return_value = 10
        mock_db.query.return_value.filter.return_value.count.return_value = 5
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch.object(team_service, '_get_dashboard_metrics') as mock_metrics, \
             patch.object(team_service, '_get_recent_proposals') as mock_recent, \
             patch.object(team_service, 'get_team_analytics') as mock_analytics, \
             patch.object(team_service, '_get_user_activity') as mock_activity, \
             patch.object(team_service, '_get_system_status') as mock_status:

            mock_metrics.return_value = []
            mock_recent.return_value = []
            mock_analytics.return_value = TeamAnalytics(
                total_proposals=10,
                active_proposals=5,
                completed_proposals=3,
                proposals_this_month=2,
                team_productivity={},
                proposal_status_distribution={},
                monthly_trends=[]
            )
            mock_activity.return_value = []
            mock_status.return_value = {}

            overview = team_service.get_dashboard_overview("test_user_id", UserRole.ADMIN)

            assert isinstance(overview, DashboardOverview)
            assert overview.team_analytics.total_proposals == 10

    def test_assign_proposal_to_user_success(self, team_service, mock_db):
        """Test successful proposal assignment."""
        # Mock proposal and users
        mock_proposal = Mock(spec=Proposal)
        mock_proposal.id = "proposal_1"
        mock_proposal.updated_at = datetime.utcnow()

        mock_target_user = Mock(spec=User)
        mock_target_user.id = "target_user_id"
        mock_target_user.role = UserRole.PROJECT_MANAGER
        mock_target_user.full_name = "Target User"

        mock_assigning_user = Mock(spec=User)
        mock_assigning_user.id = "admin_user_id"
        mock_assigning_user.can_manage_users = True

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_proposal, mock_target_user, mock_assigning_user
        ]

        with patch.object(team_service.proposal_service, 'log_audit_event'):
            result = team_service.assign_proposal_to_user(
                proposal_id="proposal_1",
                user_id="target_user_id",
                assigned_by_id="admin_user_id",
                notes="Test assignment"
            )

            assert result.success is True
            assert "successfully assigned" in result.message
            mock_db.commit.assert_called_once()

    def test_assign_proposal_to_client_fails(self, team_service, mock_db):
        """Test that assigning proposal to client user fails."""
        mock_proposal = Mock(spec=Proposal)
        mock_target_user = Mock(spec=User)
        mock_target_user.role = UserRole.CLIENT

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_proposal, mock_target_user
        ]

        result = team_service.assign_proposal_to_user(
            proposal_id="proposal_1",
            user_id="client_user_id",
            assigned_by_id="admin_user_id"
        )

        assert result.success is False
        assert "Cannot assign proposals to client users" in result.message

    def test_bulk_update_proposals_status(self, team_service, mock_db):
        """Test bulk status update of proposals."""
        # Mock proposals
        mock_proposals = []
        for i in range(3):
            proposal = Mock(spec=Proposal)
            proposal.id = f"proposal_{i}"
            proposal.status = ProposalStatus.DRAFT
            proposal.updated_at = datetime.utcnow()
            mock_proposals.append(proposal)

        mock_db.query.return_value.filter.return_value.first.side_effect = mock_proposals

        operation = BulkUpdateOperation(
            operation_type="status_update",
            proposal_ids=["proposal_0", "proposal_1", "proposal_2"],
            update_data={"status": "approved"},
            performed_by_id="admin_user_id"
        )

        with patch.object(team_service.proposal_service, 'log_audit_event'), \
             patch.object(team_service, '_proposal_to_summary') as mock_summary:
            
            mock_summary.return_value = Mock()
            
            result = team_service.bulk_update_proposals(operation)

            assert result.success is True
            assert result.successful_updates == 3
            assert result.failed_updates == 0
            mock_db.commit.assert_called_once()

    def test_get_team_analytics(self, team_service, mock_db):
        """Test team analytics generation."""
        # Mock database counts
        mock_db.query.return_value.count.return_value = 15
        mock_db.query.return_value.filter.return_value.count.return_value = 8

        with patch.object(team_service, '_calculate_average_completion_time') as mock_avg, \
             patch.object(team_service, '_get_team_productivity_metrics') as mock_productivity, \
             patch.object(team_service, '_get_proposal_status_distribution') as mock_status_dist, \
             patch.object(team_service, '_get_monthly_trends') as mock_trends:

            mock_avg.return_value = 15.5
            mock_productivity.return_value = {}
            mock_status_dist.return_value = {"draft": 5, "approved": 3}
            mock_trends.return_value = []

            analytics = team_service.get_team_analytics(UserRole.ADMIN)

            assert isinstance(analytics, TeamAnalytics)
            assert analytics.total_proposals == 15
            assert analytics.average_completion_time == 15.5

    def test_get_team_proposals_client_filter(self, team_service, mock_db):
        """Test that client users only see their own proposals."""
        mock_proposals = [Mock(spec=Proposal) for _ in range(3)]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_proposals

        with patch.object(team_service, '_proposal_to_summary') as mock_summary:
            mock_summary.return_value = Mock()
            
            proposals = team_service.get_team_proposals(
                user_id="client_user_id",
                user_role=UserRole.CLIENT
            )

            # Verify that filter was applied for client user
            mock_db.query.return_value.filter.assert_called()

    def test_invalid_user_id_raises_error(self, team_service):
        """Test that invalid user ID raises ValueError."""
        with pytest.raises(ValueError, match="User ID is required"):
            team_service.get_dashboard_overview("", UserRole.ADMIN)

    def test_proposal_assignment_missing_data_fails(self, team_service):
        """Test that missing assignment data raises ValueError."""
        with pytest.raises(ValueError, match="required"):
            team_service.assign_proposal_to_user("", "user_id", "assigned_by_id")

    def test_bulk_update_empty_proposal_list_fails(self, team_service):
        """Test that bulk update with empty proposal list raises ValueError."""
        operation = BulkUpdateOperation(
            operation_type="status_update",
            proposal_ids=[],
            update_data={},
            performed_by_id="admin_user_id"
        )

        with pytest.raises(ValueError, match="No proposal IDs provided"):
            team_service.bulk_update_proposals(operation)


class TestTeamDashboardIntegration:
    """Integration tests for team dashboard functionality."""

    def test_dashboard_workflow_integration(self):
        """Test complete dashboard workflow integration."""
        # This would test the full workflow from API call to database
        # In a real implementation, this would use a test database
        pass

    def test_permission_enforcement_integration(self):
        """Test that permissions are properly enforced across the system."""
        # This would test role-based access control integration
        pass

    def test_audit_logging_integration(self):
        """Test that audit logging works correctly for team operations."""
        # This would test audit trail functionality
        pass


if __name__ == "__main__":
    pytest.main([__file__]) 