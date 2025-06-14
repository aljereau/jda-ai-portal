"""
Unit tests for Block 3 Proposal Service functionality.
Tests sharing, export tracking, audit logs, and analytics features.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.proposal_service import ProposalService, ProposalServiceError
from app.models.proposal import (
    Proposal, ProposalShare, ProposalExport, ProposalAuditLog,
    SharePermissionEnum, ExportFormatEnum, AuditActionEnum,
    ProposalStatusEnum, ProjectPhaseEnum
)
from app.models.user import User, UserRole


class TestProposalServiceBlock3:
    """Test class for Block 3 proposal service functionality."""

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

    def test_create_proposal_share_success(self, proposal_service, mock_db, sample_proposal):
        """Test successful proposal share creation."""
        # Setup
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        share = ProposalShare(
            id=1,
            proposal_id=1,
            shared_with_email="client@example.com",
            permission_level=SharePermissionEnum.VIEW_ONLY,
            shared_by=1
        )
        mock_db.refresh.side_effect = lambda obj: setattr(obj, 'id', 1)

        # Execute
        result = proposal_service.create_proposal_share(
            proposal_id=1,
            shared_by=1,
            shared_with_email="client@example.com",
            permission_level="view_only",
            can_download=False,
            can_comment=False,
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )

        # Verify
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
        assert isinstance(result, ProposalShare)

    def test_create_proposal_share_with_expiration(self, proposal_service, mock_db):
        """Test proposal share creation with expiration."""
        # Setup
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        # Execute
        result = proposal_service.create_proposal_share(
            proposal_id=1,
            shared_by=1,
            shared_with_user_id=2,
            permission_level="edit",
            expires_in_days=7
        )

        # Verify
        mock_db.add.assert_called()
        call_args = mock_db.add.call_args[0][0]
        assert call_args.expires_at is not None
        assert call_args.permission_level == SharePermissionEnum.EDIT

    def test_get_proposal_shares(self, proposal_service, mock_db):
        """Test retrieving proposal shares."""
        # Setup
        mock_shares = [
            ProposalShare(
                id=1,
                proposal_id=1,
                shared_with_email="client1@example.com",
                permission_level=SharePermissionEnum.VIEW_ONLY,
                is_active=True
            ),
            ProposalShare(
                id=2,
                proposal_id=1,
                shared_with_user_id=2,
                permission_level=SharePermissionEnum.EDIT,
                is_active=True
            )
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_shares

        # Execute
        result = proposal_service.get_proposal_shares(1)

        # Verify
        assert len(result) == 2
        assert all(share.is_active for share in result)

    def test_revoke_proposal_share_success(self, proposal_service, mock_db):
        """Test successful proposal share revocation."""
        # Setup
        mock_share = ProposalShare(
            id=1,
            proposal_id=1,
            shared_with_email="client@example.com",
            is_active=True
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_share
        mock_db.commit.return_value = None

        # Execute
        result = proposal_service.revoke_proposal_share(
            share_id=1,
            revoked_by=1,
            ip_address="192.168.1.1"
        )

        # Verify
        assert result is True
        assert mock_share.is_active is False
        mock_db.commit.assert_called()

    def test_revoke_proposal_share_not_found(self, proposal_service, mock_db):
        """Test proposal share revocation when share not found."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Execute & Verify
        with pytest.raises(ProposalServiceError, match="Share 999 not found"):
            proposal_service.revoke_proposal_share(999, 1)

    def test_track_proposal_export_success(self, proposal_service, mock_db, sample_proposal):
        """Test successful proposal export tracking."""
        # Setup
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        proposal_service.get_proposal = Mock(return_value=sample_proposal)

        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024):

            # Execute
            result = proposal_service.track_proposal_export(
                proposal_id=1,
                format="pdf",
                file_path="/tmp/proposal.pdf",
                exported_by=1,
                export_settings={"include_metadata": True},
                version_exported=1
            )

            # Verify
            mock_db.add.assert_called()
            mock_db.commit.assert_called()
            assert sample_proposal.export_count == 1
            assert sample_proposal.last_exported_at is not None

    def test_get_proposal_exports(self, proposal_service, mock_db):
        """Test retrieving proposal exports."""
        # Setup
        mock_exports = [
            ProposalExport(
                id=1,
                proposal_id=1,
                format=ExportFormatEnum.PDF,
                file_path="/tmp/proposal.pdf",
                exported_by=1
            ),
            ProposalExport(
                id=2,
                proposal_id=1,
                format=ExportFormatEnum.HTML,
                file_path="/tmp/proposal.html",
                exported_by=1
            )
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_exports

        # Execute
        result = proposal_service.get_proposal_exports(1)

        # Verify
        assert len(result) == 2
        assert result[0].format == ExportFormatEnum.PDF
        assert result[1].format == ExportFormatEnum.HTML

    def test_track_export_download_success(self, proposal_service, mock_db):
        """Test successful export download tracking."""
        # Setup
        mock_export = ProposalExport(
            id=1,
            proposal_id=1,
            format=ExportFormatEnum.PDF,
            download_count=0
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_export
        mock_db.commit.return_value = None

        # Execute
        result = proposal_service.track_export_download(1)

        # Verify
        assert result is True
        assert mock_export.download_count == 1
        assert mock_export.last_downloaded_at is not None

    def test_track_export_download_not_found(self, proposal_service, mock_db):
        """Test export download tracking when export not found."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Execute & Verify
        with pytest.raises(ProposalServiceError, match="Export 999 not found"):
            proposal_service.track_export_download(999)

    def test_get_proposal_audit_log(self, proposal_service, mock_db):
        """Test retrieving proposal audit log."""
        # Setup
        mock_logs = [
            ProposalAuditLog(
                id=1,
                proposal_id=1,
                action=AuditActionEnum.CREATED,
                description="Proposal created",
                performed_by=1
            ),
            ProposalAuditLog(
                id=2,
                proposal_id=1,
                action=AuditActionEnum.SHARED,
                description="Proposal shared",
                performed_by=1
            )
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_logs

        # Execute
        result = proposal_service.get_proposal_audit_log(1, limit=50)

        # Verify
        assert len(result) == 2
        assert result[0].action == AuditActionEnum.CREATED
        assert result[1].action == AuditActionEnum.SHARED

    def test_get_proposal_audit_log_with_filter(self, proposal_service, mock_db):
        """Test retrieving proposal audit log with action filter."""
        # Setup
        mock_logs = [
            ProposalAuditLog(
                id=1,
                proposal_id=1,
                action=AuditActionEnum.SHARED,
                description="Proposal shared",
                performed_by=1
            )
        ]
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_logs

        # Execute
        result = proposal_service.get_proposal_audit_log(1, action_filter="shared")

        # Verify
        assert len(result) == 1
        assert result[0].action == AuditActionEnum.SHARED

    def test_get_proposal_analytics_success(self, proposal_service, mock_db, sample_proposal):
        """Test successful proposal analytics retrieval."""
        # Setup
        proposal_service.get_proposal = Mock(return_value=sample_proposal)
        proposal_service.get_proposal_shares = Mock(return_value=[
            Mock(is_active=True, access_count=5),
            Mock(is_active=False, access_count=2)
        ])
        proposal_service.get_proposal_exports = Mock(return_value=[
            Mock(format=Mock(value="pdf"), download_count=3),
            Mock(format=Mock(value="html"), download_count=1)
        ])
        proposal_service.get_proposal_versions = Mock(return_value=[
            Mock(version_number=1),
            Mock(version_number=2)
        ])
        proposal_service.get_proposal_audit_log = Mock(return_value=[
            Mock(action=Mock(value="created"), description="Created", created_at=datetime.utcnow()),
            Mock(action=Mock(value="shared"), description="Shared", created_at=datetime.utcnow())
        ])

        # Execute
        result = proposal_service.get_proposal_analytics(1)

        # Verify
        assert result["proposal_id"] == 1
        assert "sharing" in result
        assert "exports" in result
        assert "versions" in result
        assert "activity" in result
        assert result["sharing"]["total_shares"] == 2
        assert result["sharing"]["active_shares"] == 1
        assert result["exports"]["total_downloads"] == 4
        assert result["versions"]["total_versions"] == 2

    def test_get_proposal_analytics_not_found(self, proposal_service, mock_db):
        """Test proposal analytics when proposal not found."""
        # Setup
        proposal_service.get_proposal = Mock(return_value=None)

        # Execute & Verify
        with pytest.raises(ProposalServiceError, match="Proposal 999 not found"):
            proposal_service.get_proposal_analytics(999)

    def test_log_audit_action_success(self, proposal_service, mock_db):
        """Test successful audit action logging."""
        # Setup
        mock_db.add.return_value = None
        mock_db.commit.return_value = None

        # Execute
        proposal_service._log_audit_action(
            proposal_id=1,
            action=AuditActionEnum.CREATED,
            performed_by=1,
            description="Test action",
            details={"key": "value"},
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )

        # Verify
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
        call_args = mock_db.add.call_args[0][0]
        assert call_args.proposal_id == 1
        assert call_args.action == AuditActionEnum.CREATED
        assert call_args.performed_by == 1

    def test_log_audit_action_with_old_new_values(self, proposal_service, mock_db):
        """Test audit action logging with old and new values."""
        # Setup
        mock_db.add.return_value = None
        mock_db.commit.return_value = None

        old_values = {"status": "draft"}
        new_values = {"status": "approved"}

        # Execute
        proposal_service._log_audit_action(
            proposal_id=1,
            action=AuditActionEnum.STATUS_CHANGED,
            performed_by=1,
            description="Status changed",
            old_values=old_values,
            new_values=new_values
        )

        # Verify
        call_args = mock_db.add.call_args[0][0]
        assert json.loads(call_args.old_values) == old_values
        assert json.loads(call_args.new_values) == new_values

    def test_generate_share_token(self, proposal_service):
        """Test share token generation."""
        # Execute
        token1 = proposal_service._generate_share_token()
        token2 = proposal_service._generate_share_token()

        # Verify
        assert token1 != token2
        assert len(token1) > 0
        assert isinstance(token1, str)

    def test_create_proposal_with_audit_logging(self, proposal_service, mock_db):
        """Test proposal creation includes audit logging."""
        # Setup
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        proposal_service._create_initial_version = Mock()
        proposal_service._create_project_tracker = Mock()

        # Execute
        result = proposal_service.create_proposal(
            project_name="Test Project",
            client_name="Test Client",
            phase="exploratory",
            transcript_path="/tmp/transcript.txt",
            created_by=1,
            ai_summary="Test summary",
            extracted_requirements={"scope": "test"},
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )

        # Verify audit logging was called
        assert mock_db.add.call_count >= 2  # Proposal + Audit log

    @pytest.mark.parametrize("permission_level,expected_enum", [
        ("view_only", SharePermissionEnum.VIEW_ONLY),
        ("comment", SharePermissionEnum.COMMENT),
        ("edit", SharePermissionEnum.EDIT),
        ("full_access", SharePermissionEnum.FULL_ACCESS)
    ])
    def test_share_permission_levels(self, proposal_service, mock_db, permission_level, expected_enum):
        """Test different share permission levels."""
        # Setup
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        # Execute
        proposal_service.create_proposal_share(
            proposal_id=1,
            shared_by=1,
            shared_with_email="test@example.com",
            permission_level=permission_level
        )

        # Verify
        call_args = mock_db.add.call_args[0][0]
        assert call_args.permission_level == expected_enum

    @pytest.mark.parametrize("export_format,expected_enum", [
        ("html", ExportFormatEnum.HTML),
        ("pdf", ExportFormatEnum.PDF),
        ("docx", ExportFormatEnum.DOCX),
        ("markdown", ExportFormatEnum.MARKDOWN)
    ])
    def test_export_formats(self, proposal_service, mock_db, export_format, expected_enum):
        """Test different export formats."""
        # Setup
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        proposal_service.get_proposal = Mock(return_value=Mock(export_count=0))

        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024):

            # Execute
            proposal_service.track_proposal_export(
                proposal_id=1,
                format=export_format,
                file_path=f"/tmp/proposal.{export_format}",
                exported_by=1
            )

            # Verify
            call_args = mock_db.add.call_args[0][0]
            assert call_args.format == expected_enum

    def test_error_handling_database_failure(self, proposal_service, mock_db):
        """Test error handling when database operations fail."""
        # Setup
        mock_db.add.side_effect = Exception("Database error")

        # Execute & Verify
        with pytest.raises(ProposalServiceError, match="Failed to create proposal share"):
            proposal_service.create_proposal_share(
                proposal_id=1,
                shared_by=1,
                shared_with_email="test@example.com"
            )

    def test_share_access_count_tracking(self, proposal_service, mock_db):
        """Test that share access count is properly tracked."""
        # Setup
        mock_share = ProposalShare(
            id=1,
            proposal_id=1,
            access_count=5,
            is_active=True
        )
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_share]

        # Execute
        shares = proposal_service.get_proposal_shares(1)

        # Verify
        assert shares[0].access_count == 5

    def test_export_file_size_tracking(self, proposal_service, mock_db):
        """Test that export file size is properly tracked."""
        # Setup
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        proposal_service.get_proposal = Mock(return_value=Mock(export_count=0))

        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=2048):

            # Execute
            proposal_service.track_proposal_export(
                proposal_id=1,
                format="pdf",
                file_path="/tmp/proposal.pdf",
                exported_by=1
            )

            # Verify
            call_args = mock_db.add.call_args[0][0]
            assert call_args.file_size_bytes == 2048 