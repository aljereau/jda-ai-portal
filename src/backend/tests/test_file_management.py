"""
Unit tests for file management functionality.
Tests file upload, download, security validation, and access control.
"""
import pytest
import io
from datetime import datetime
from unittest.mock import Mock, patch, mock_open
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, UserRole
from app.models.proposal import Proposal
from app.models.file import File, FileType, FileStatus
from app.services.file_service import FileService
from app.schemas.file import (
    FileUploadRequest, FileUploadResponse, FileInfo, FileAccessRequest,
    FileAccessResponse, FileAttachmentRequest, FileAttachmentResponse,
    FileSearchFilters, FileSearchResponse, FileSecurityValidation
)

client = TestClient(app)


class TestFileManagementAPI:
    """Test cases for file management API endpoints."""

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
        return user

    @pytest.fixture
    def client_user(self):
        """Mock client user."""
        user = Mock(spec=User)
        user.id = "client_user_id"
        user.email = "client@test.com"
        user.role = UserRole.CLIENT
        user.full_name = "Client User"
        return user

    @pytest.fixture
    def sample_file_data(self):
        """Sample file data for testing."""
        return b"Sample file content for testing"

    @pytest.fixture
    def sample_file_info(self):
        """Sample file info for testing."""
        return FileInfo(
            id="file_123",
            filename="test_document.pdf",
            original_filename="test_document.pdf",
            file_type=FileType.DOCUMENT,
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            status=FileStatus.READY,
            is_public=False,
            uploaded_by_id="admin_user_id",
            proposal_id="proposal_123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    @patch('app.api.v1.file_management.get_current_user')
    @patch('app.api.v1.file_management.get_db')
    def test_upload_file_success(self, mock_get_db, mock_get_user, admin_user, mock_db, sample_file_data):
        """Test successful file upload."""
        mock_get_user.return_value = admin_user
        mock_get_db.return_value = mock_db

        with patch('app.api.v1.file_management.FileService') as mock_service:
            mock_response = FileUploadResponse(
                success=True,
                file_id="file_123",
                message="File uploaded successfully",
                file_info={"id": "file_123", "filename": "test.pdf"}
            )
            mock_service.return_value.upload_file.return_value = mock_response

            # Create a mock file upload
            files = {"file": ("test.pdf", sample_file_data, "application/pdf")}
            data = {
                "file_type": "document",
                "is_public": "false"
            }

            response = client.post(
                "/api/v1/files/upload",
                files=files,
                data=data,
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["file_id"] == "file_123"

    @patch('app.api.v1.file_management.get_current_user')
    @patch('app.api.v1.file_management.get_db')
    def test_upload_file_too_large(self, mock_get_db, mock_get_user, admin_user, mock_db):
        """Test file upload with file too large."""
        mock_get_user.return_value = admin_user
        mock_get_db.return_value = mock_db

        # Create a large file (simulate 60MB)
        large_file_data = b"x" * (60 * 1024 * 1024)
        files = {"file": ("large_file.pdf", large_file_data, "application/pdf")}
        data = {"file_type": "document"}

        response = client.post(
            "/api/v1/files/upload",
            files=files,
            data=data,
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 413  # Request Entity Too Large

    @patch('app.api.v1.file_management.get_current_user')
    @patch('app.api.v1.file_management.get_db')
    def test_get_file_info_success(self, mock_get_db, mock_get_user, admin_user, mock_db, sample_file_info):
        """Test successful file info retrieval."""
        mock_get_user.return_value = admin_user
        mock_get_db.return_value = mock_db

        with patch('app.api.v1.file_management.FileService') as mock_service:
            mock_service.return_value.get_file_info.return_value = sample_file_info

            response = client.get(
                "/api/v1/files/file_123",
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "file_123"
            assert data["filename"] == "test_document.pdf"

    @patch('app.api.v1.file_management.get_current_user')
    @patch('app.api.v1.file_management.get_db')
    def test_get_file_info_not_found(self, mock_get_db, mock_get_user, admin_user, mock_db):
        """Test file info retrieval for non-existent file."""
        mock_get_user.return_value = admin_user
        mock_get_db.return_value = mock_db

        with patch('app.api.v1.file_management.FileService') as mock_service:
            mock_service.return_value.get_file_info.return_value = None

            response = client.get(
                "/api/v1/files/nonexistent_file",
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 404

    @patch('app.api.v1.file_management.get_current_user')
    @patch('app.api.v1.file_management.get_db')
    @patch('builtins.open', new_callable=mock_open, read_data=b"file content")
    @patch('pathlib.Path.exists')
    def test_download_file_success(self, mock_exists, mock_file_open, mock_get_db, mock_get_user, 
                                  admin_user, mock_db, sample_file_info):
        """Test successful file download."""
        mock_get_user.return_value = admin_user
        mock_get_db.return_value = mock_db
        mock_exists.return_value = True

        with patch('app.api.v1.file_management.FileService') as mock_service:
            mock_access_response = FileAccessResponse(
                success=True,
                download_url="http://test.com/download",
                message="Access granted",
                file_info=sample_file_info
            )
            mock_service.return_value.get_file_access_url.return_value = mock_access_response

            response = client.get(
                "/api/v1/files/file_123/download",
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200

    @patch('app.api.v1.file_management.get_current_user')
    @patch('app.api.v1.file_management.get_db')
    def test_download_file_permission_denied(self, mock_get_db, mock_get_user, client_user, mock_db):
        """Test file download with insufficient permissions."""
        mock_get_user.return_value = client_user
        mock_get_db.return_value = mock_db

        with patch('app.api.v1.file_management.FileService') as mock_service:
            mock_access_response = FileAccessResponse(
                success=False,
                message="Insufficient permissions"
            )
            mock_service.return_value.get_file_access_url.return_value = mock_access_response

            response = client.get(
                "/api/v1/files/file_123/download",
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 403

    @patch('app.api.v1.file_management.get_current_user')
    @patch('app.api.v1.file_management.get_db')
    def test_get_proposal_files(self, mock_get_db, mock_get_user, admin_user, mock_db, sample_file_info):
        """Test getting files for a proposal."""
        mock_get_user.return_value = admin_user
        mock_get_db.return_value = mock_db

        with patch('app.api.v1.file_management.FileService') as mock_service:
            mock_service.return_value.get_proposal_files.return_value = [sample_file_info]

            response = client.get(
                "/api/v1/files/proposal/proposal_123",
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "file_123"

    @patch('app.api.v1.file_management.get_current_user')
    @patch('app.api.v1.file_management.get_db')
    def test_attach_file_to_proposal(self, mock_get_db, mock_get_user, admin_user, mock_db):
        """Test attaching file to proposal."""
        mock_get_user.return_value = admin_user
        mock_get_db.return_value = mock_db

        attachment_data = {
            "file_id": "file_123",
            "proposal_id": "proposal_123",
            "description": "Test attachment"
        }

        with patch('app.api.v1.file_management.FileService') as mock_service:
            mock_response = FileAttachmentResponse(
                success=True,
                message="File attached successfully",
                attachment_id="attachment_123"
            )
            mock_service.return_value.attach_file_to_proposal.return_value = mock_response

            response = client.post(
                "/api/v1/files/attach-to-proposal",
                json=attachment_data,
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @patch('app.api.v1.file_management.get_current_user')
    @patch('app.api.v1.file_management.get_db')
    def test_search_files(self, mock_get_db, mock_get_user, admin_user, mock_db, sample_file_info):
        """Test file search functionality."""
        mock_get_user.return_value = admin_user
        mock_get_db.return_value = mock_db

        with patch('app.api.v1.file_management.FileService') as mock_service:
            mock_search_response = FileSearchResponse(
                files=[sample_file_info],
                total_count=1,
                has_more=False,
                filters_applied={}
            )
            mock_service.return_value.search_files.return_value = mock_search_response

            response = client.get(
                "/api/v1/files/search?file_type=document&filename_search=test",
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["files"]) == 1
            assert data["total_count"] == 1

    @patch('app.api.v1.file_management.get_current_user')
    @patch('app.api.v1.file_management.get_db')
    def test_delete_file(self, mock_get_db, mock_get_user, admin_user, mock_db):
        """Test file deletion."""
        mock_get_user.return_value = admin_user
        mock_get_db.return_value = mock_db

        with patch('app.api.v1.file_management.FileService') as mock_service:
            mock_service.return_value.delete_file.return_value = True

            response = client.delete(
                "/api/v1/files/file_123",
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "deleted successfully" in data["message"]


class TestFileService:
    """Test cases for FileService business logic."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def file_service(self, mock_db):
        """FileService instance with mocked database."""
        with patch('app.services.file_service.settings') as mock_settings:
            mock_settings.UPLOAD_DIR = "/tmp/test_uploads"
            return FileService(mock_db)

    @pytest.fixture
    def sample_file_data(self):
        """Sample file data for testing."""
        return io.BytesIO(b"Sample file content for testing")

    @pytest.fixture
    def upload_request(self):
        """Sample upload request."""
        return FileUploadRequest(
            filename="test_document.pdf",
            file_type=FileType.DOCUMENT,
            proposal_id="proposal_123",
            is_public=False,
            description="Test document"
        )

    def test_upload_file_success(self, file_service, mock_db, sample_file_data, upload_request):
        """Test successful file upload."""
        with patch.object(file_service, '_validate_file') as mock_validate, \
             patch.object(file_service, '_save_file_to_storage') as mock_save, \
             patch.object(file_service, '_log_file_access') as mock_log, \
             patch('pathlib.Path.mkdir'):

            # Mock validation success
            mock_validate.return_value = FileSecurityValidation(
                is_safe=True,
                scan_results={},
                warnings=[],
                blocked_reasons=[]
            )
            mock_save.return_value = 1024

            result = file_service.upload_file(
                file_data=sample_file_data,
                upload_request=upload_request,
                uploaded_by_id="user_123"
            )

            assert result.success is True
            assert result.file_id is not None
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    def test_upload_file_validation_failure(self, file_service, sample_file_data, upload_request):
        """Test file upload with validation failure."""
        with patch.object(file_service, '_validate_file') as mock_validate:
            # Mock validation failure
            mock_validate.return_value = FileSecurityValidation(
                is_safe=False,
                scan_results={},
                warnings=[],
                blocked_reasons=["File too large"]
            )

            result = file_service.upload_file(
                file_data=sample_file_data,
                upload_request=upload_request,
                uploaded_by_id="user_123"
            )

            assert result.success is False
            assert "validation failed" in result.message.lower()

    def test_get_file_info_success(self, file_service, mock_db):
        """Test successful file info retrieval."""
        # Mock file record
        mock_file = Mock(spec=File)
        mock_file.id = "file_123"
        mock_file.filename = "test.pdf"
        mock_file.uploaded_by_id = "user_123"
        mock_file.is_public = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_file

        with patch.object(file_service, '_check_file_access_permission') as mock_check, \
             patch.object(file_service, '_log_file_access'):
            mock_check.return_value = True

            result = file_service.get_file_info("file_123", "user_123")

            assert result is not None
            mock_check.assert_called_once_with(mock_file, "user_123")

    def test_get_file_info_permission_denied(self, file_service, mock_db):
        """Test file info retrieval with permission denied."""
        mock_file = Mock(spec=File)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_file

        with patch.object(file_service, '_check_file_access_permission') as mock_check:
            mock_check.return_value = False

            with pytest.raises(PermissionError):
                file_service.get_file_info("file_123", "user_123")

    def test_attach_file_to_proposal_success(self, file_service, mock_db):
        """Test successful file attachment to proposal."""
        # Mock file and proposal
        mock_file = Mock(spec=File)
        mock_file.id = "file_123"
        mock_file.uploaded_by_id = "user_123"

        mock_proposal = Mock(spec=Proposal)
        mock_proposal.id = "proposal_123"
        mock_proposal.creator_id = "user_123"

        mock_user = Mock(spec=User)
        mock_user.id = "user_123"
        mock_user.role = UserRole.ADMIN

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_file, mock_proposal, mock_user
        ]

        with patch.object(file_service, '_check_file_access_permission') as mock_check_file, \
             patch.object(file_service, '_check_proposal_modification_permission') as mock_check_proposal, \
             patch.object(file_service, '_log_file_access'):

            mock_check_file.return_value = True
            mock_check_proposal.return_value = True

            attachment_request = FileAttachmentRequest(
                file_id="file_123",
                proposal_id="proposal_123"
            )

            result = file_service.attach_file_to_proposal(attachment_request, "user_123")

            assert result.success is True
            assert mock_file.proposal_id == "proposal_123"
            mock_db.commit.assert_called_once()

    def test_search_files_with_filters(self, file_service, mock_db):
        """Test file search with various filters."""
        # Mock user and files
        mock_user = Mock(spec=User)
        mock_user.id = "user_123"
        mock_user.role = UserRole.ADMIN

        mock_files = [Mock(spec=File) for _ in range(3)]
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value.count.return_value = 3
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = mock_files

        with patch.object(file_service, '_apply_file_search_filters') as mock_apply_filters:
            mock_apply_filters.return_value = mock_db.query.return_value

            filters = FileSearchFilters(
                file_type=FileType.DOCUMENT,
                filename_search="test",
                limit=10,
                offset=0
            )

            result = file_service.search_files(filters, "user_123")

            assert isinstance(result, FileSearchResponse)
            assert len(result.files) == 3
            assert result.total_count == 3

    def test_delete_file_success(self, file_service, mock_db):
        """Test successful file deletion."""
        # Mock file and user
        mock_file = Mock(spec=File)
        mock_file.id = "file_123"
        mock_file.uploaded_by_id = "user_123"
        mock_file.status = FileStatus.READY

        mock_user = Mock(spec=User)
        mock_user.id = "user_123"
        mock_user.role = UserRole.ADMIN

        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_file, mock_user]

        with patch.object(file_service, '_log_file_access'):
            result = file_service.delete_file("file_123", "user_123")

            assert result is True
            assert mock_file.status == FileStatus.DELETED
            mock_db.commit.assert_called_once()

    def test_validate_file_size_limit(self, file_service):
        """Test file validation with size limit."""
        large_file_data = io.BytesIO(b"x" * (60 * 1024 * 1024))  # 60MB
        upload_request = FileUploadRequest(
            filename="large_file.pdf",
            file_type=FileType.DOCUMENT,
            is_public=False
        )

        result = file_service._validate_file(large_file_data, upload_request)

        assert result.is_safe is False
        assert any("exceeds maximum" in reason for reason in result.blocked_reasons)

    def test_validate_file_extension(self, file_service):
        """Test file validation with unsupported extension."""
        file_data = io.BytesIO(b"test content")
        upload_request = FileUploadRequest(
            filename="test.exe",  # Unsupported extension
            file_type=FileType.DOCUMENT,
            is_public=False
        )

        result = file_service._validate_file(file_data, upload_request)

        assert result.is_safe is False
        assert any("not supported" in reason for reason in result.blocked_reasons)

    def test_check_file_access_permission_owner(self, file_service, mock_db):
        """Test file access permission for file owner."""
        mock_file = Mock(spec=File)
        mock_file.uploaded_by_id = "user_123"

        result = file_service._check_file_access_permission(mock_file, "user_123")
        assert result is True

    def test_check_file_access_permission_public(self, file_service, mock_db):
        """Test file access permission for public file."""
        mock_file = Mock(spec=File)
        mock_file.uploaded_by_id = "other_user"
        mock_file.is_public = True

        mock_user = Mock(spec=User)
        mock_user.id = "user_123"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = file_service._check_file_access_permission(mock_file, "user_123")
        assert result is True

    def test_check_file_access_permission_admin(self, file_service, mock_db):
        """Test file access permission for admin user."""
        mock_file = Mock(spec=File)
        mock_file.uploaded_by_id = "other_user"
        mock_file.is_public = False

        mock_user = Mock(spec=User)
        mock_user.id = "admin_user"
        mock_user.role = UserRole.ADMIN
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = file_service._check_file_access_permission(mock_file, "admin_user")
        assert result is True

    def test_check_file_access_permission_denied(self, file_service, mock_db):
        """Test file access permission denied."""
        mock_file = Mock(spec=File)
        mock_file.uploaded_by_id = "other_user"
        mock_file.is_public = False
        mock_file.proposal_id = None

        mock_user = Mock(spec=User)
        mock_user.id = "user_123"
        mock_user.role = UserRole.CLIENT
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = file_service._check_file_access_permission(mock_file, "user_123")
        assert result is False

    def test_generate_safe_filename(self, file_service):
        """Test safe filename generation."""
        unsafe_filename = "test file with spaces & special chars!.pdf"
        safe_filename = file_service._generate_safe_filename(unsafe_filename)
        
        assert " " not in safe_filename
        assert "&" not in safe_filename
        assert "!" not in safe_filename
        assert safe_filename.endswith(".pdf")

    def test_determine_file_type_image(self, file_service):
        """Test file type determination for images."""
        file_type = file_service._determine_file_type(".jpg")
        assert file_type == FileType.IMAGE

    def test_determine_file_type_document(self, file_service):
        """Test file type determination for documents."""
        file_type = file_service._determine_file_type(".pdf")
        assert file_type == FileType.DOCUMENT

    def test_determine_file_type_spreadsheet(self, file_service):
        """Test file type determination for spreadsheets."""
        file_type = file_service._determine_file_type(".xlsx")
        assert file_type == FileType.SPREADSHEET

    def test_determine_file_type_presentation(self, file_service):
        """Test file type determination for presentations."""
        file_type = file_service._determine_file_type(".pptx")
        assert file_type == FileType.PRESENTATION


class TestFileManagementIntegration:
    """Integration tests for file management functionality."""

    def test_file_upload_download_workflow(self):
        """Test complete file upload and download workflow."""
        # This would test the full workflow from upload to download
        # In a real implementation, this would use a test database and file system
        pass

    def test_file_security_validation_integration(self):
        """Test file security validation integration."""
        # This would test security validation with real file samples
        pass

    def test_file_access_control_integration(self):
        """Test file access control across different user roles."""
        # This would test role-based access control with real scenarios
        pass


if __name__ == "__main__":
    pytest.main([__file__]) 