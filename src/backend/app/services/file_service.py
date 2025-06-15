"""
File management service for JDA AI Portal.
Provides business logic for file upload, storage, security, and access control.
"""
import os
import uuid
import hashlib
import mimetypes
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, BinaryIO
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import logging

from ..models.file import File, FileType, FileStatus, FileAccess
from ..models.user import User, UserRole
from ..models.proposal import Proposal
from ..schemas.file import (
    FileUploadRequest, FileUploadResponse, FileInfo, FileAccessRequest,
    FileAccessResponse, FileAttachmentRequest, FileAttachmentResponse,
    FileSearchFilters, FileSearchResponse, FileSecurityValidation
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class FileService:
    """Service class for file management and storage operations.
    
    This service handles file uploads, security validation, access control,
    and storage management following the service layer pattern.
    """

    # Supported file types and extensions
    SUPPORTED_EXTENSIONS = {
        FileType.IMAGE: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
        FileType.DOCUMENT: ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
        FileType.SPREADSHEET: ['.xls', '.xlsx', '.csv'],
        FileType.PRESENTATION: ['.ppt', '.pptx'],
        FileType.TRANSCRIPT: ['.txt', '.docx', '.pdf']
    }

    # Maximum file sizes (in bytes)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_FILES_PER_UPLOAD = 10

    def __init__(self, db: Session):
        """Initialize FileService with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.storage_base_path = Path(settings.UPLOAD_DIR)
        self.storage_base_path.mkdir(parents=True, exist_ok=True)

    def upload_file(self, file_data: BinaryIO, upload_request: FileUploadRequest, 
                   uploaded_by_id: str) -> FileUploadResponse:
        """Upload and process a file.
        
        Args:
            file_data: Binary file data
            upload_request: File upload request details
            uploaded_by_id: ID of the user uploading the file
            
        Returns:
            File upload response with success status and file information
            
        Raises:
            ValueError: If file data or request is invalid
            PermissionError: If user lacks upload permissions
        """
        if not uploaded_by_id:
            raise ValueError("Uploaded by user ID is required")
        
        logger.info(f"Processing file upload: {upload_request.filename} by user {uploaded_by_id}")
        
        try:
            # Validate file
            validation_result = self._validate_file(file_data, upload_request)
            if not validation_result.is_safe:
                return FileUploadResponse(
                    success=False,
                    message=f"File validation failed: {', '.join(validation_result.blocked_reasons)}",
                    file_info={"validation_errors": validation_result.blocked_reasons}
                )
            
            # Generate unique file ID and storage path
            file_id = str(uuid.uuid4())
            file_extension = self._get_file_extension(upload_request.filename)
            file_type = self._determine_file_type(file_extension)
            
            # Create storage directory structure
            storage_path = self._create_storage_path(upload_request.proposal_id, file_type, file_id, file_extension)
            
            # Save file to storage
            file_size = self._save_file_to_storage(file_data, storage_path)
            
            # Create file record in database
            file_record = File(
                id=file_id,
                filename=self._generate_safe_filename(upload_request.filename),
                original_filename=upload_request.filename,
                file_type=file_type,
                file_extension=file_extension,
                file_size=file_size,
                mime_type=mimetypes.guess_type(upload_request.filename)[0] or 'application/octet-stream',
                storage_path=str(storage_path),
                status=FileStatus.READY,
                is_public=upload_request.is_public,
                uploaded_by_id=uploaded_by_id,
                proposal_id=upload_request.proposal_id
            )
            
            self.db.add(file_record)
            self.db.commit()
            
            # Log file access
            self._log_file_access(file_id, uploaded_by_id, "upload")
            
            logger.info(f"File uploaded successfully: {file_id}")
            
            return FileUploadResponse(
                success=True,
                file_id=file_id,
                message="File uploaded successfully",
                file_info={
                    "id": file_id,
                    "filename": file_record.filename,
                    "file_type": file_type.value,
                    "file_size": file_size,
                    "status": FileStatus.READY.value
                }
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error uploading file {upload_request.filename}: {str(e)}")
            return FileUploadResponse(
                success=False,
                message=f"File upload failed: {str(e)}"
            )

    def get_file_info(self, file_id: str, user_id: str) -> Optional[FileInfo]:
        """Get file information with access control.
        
        Args:
            file_id: ID of the file to retrieve
            user_id: ID of the requesting user
            
        Returns:
            File information if accessible, None otherwise
            
        Raises:
            ValueError: If file_id or user_id is invalid
            PermissionError: If user lacks access permissions
        """
        if not file_id or not user_id:
            raise ValueError("File ID and user ID are required")
        
        logger.info(f"Getting file info for {file_id} requested by user {user_id}")
        
        try:
            file_record = self.db.query(File).filter(File.id == file_id).first()
            if not file_record:
                return None
            
            # Check access permissions
            if not self._check_file_access_permission(file_record, user_id):
                raise PermissionError("Insufficient permissions to access this file")
            
            # Log file access
            self._log_file_access(file_id, user_id, "view")
            
            return FileInfo.from_orm(file_record)
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_id}: {str(e)}")
            raise

    def get_file_access_url(self, access_request: FileAccessRequest, user_id: str) -> FileAccessResponse:
        """Get secure access URL for file download/viewing.
        
        Args:
            access_request: File access request details
            user_id: ID of the requesting user
            
        Returns:
            File access response with download URL or error
            
        Raises:
            ValueError: If request data is invalid
            PermissionError: If user lacks access permissions
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        logger.info(f"Generating access URL for file {access_request.file_id} by user {user_id}")
        
        try:
            file_record = self.db.query(File).filter(File.id == access_request.file_id).first()
            if not file_record:
                return FileAccessResponse(
                    success=False,
                    message="File not found"
                )
            
            # Check access permissions
            if not self._check_file_access_permission(file_record, user_id):
                return FileAccessResponse(
                    success=False,
                    message="Insufficient permissions to access this file"
                )
            
            # Generate secure access URL (in production, this would be a signed URL)
            access_url = self._generate_access_url(file_record, access_request.access_type)
            expires_at = datetime.utcnow() + timedelta(hours=1)  # URL expires in 1 hour
            
            # Log file access
            self._log_file_access(access_request.file_id, user_id, access_request.access_type)
            
            return FileAccessResponse(
                success=True,
                download_url=access_url,
                expires_at=expires_at,
                message="Access URL generated successfully",
                file_info=FileInfo.from_orm(file_record)
            )
            
        except Exception as e:
            logger.error(f"Error generating access URL for file {access_request.file_id}: {str(e)}")
            return FileAccessResponse(
                success=False,
                message=f"Failed to generate access URL: {str(e)}"
            )

    def attach_file_to_proposal(self, attachment_request: FileAttachmentRequest, 
                               user_id: str) -> FileAttachmentResponse:
        """Attach an existing file to a proposal.
        
        Args:
            attachment_request: File attachment request details
            user_id: ID of the user making the attachment
            
        Returns:
            File attachment response with success status
            
        Raises:
            ValueError: If request data is invalid
            PermissionError: If user lacks attachment permissions
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        logger.info(f"Attaching file {attachment_request.file_id} to proposal {attachment_request.proposal_id}")
        
        try:
            # Verify file exists and user has access
            file_record = self.db.query(File).filter(File.id == attachment_request.file_id).first()
            if not file_record:
                return FileAttachmentResponse(
                    success=False,
                    message="File not found"
                )
            
            if not self._check_file_access_permission(file_record, user_id):
                return FileAttachmentResponse(
                    success=False,
                    message="Insufficient permissions to access this file"
                )
            
            # Verify proposal exists and user has access
            proposal = self.db.query(Proposal).filter(Proposal.id == attachment_request.proposal_id).first()
            if not proposal:
                return FileAttachmentResponse(
                    success=False,
                    message="Proposal not found"
                )
            
            # Check if user can modify this proposal
            user = self.db.query(User).filter(User.id == user_id).first()
            if not self._check_proposal_modification_permission(proposal, user):
                return FileAttachmentResponse(
                    success=False,
                    message="Insufficient permissions to modify this proposal"
                )
            
            # Update file to attach to proposal
            file_record.proposal_id = attachment_request.proposal_id
            file_record.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            # Log the attachment
            self._log_file_access(attachment_request.file_id, user_id, "attach_to_proposal")
            
            return FileAttachmentResponse(
                success=True,
                message="File successfully attached to proposal",
                attachment_id=f"{attachment_request.file_id}_{attachment_request.proposal_id}",
                file_info=FileInfo.from_orm(file_record)
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error attaching file to proposal: {str(e)}")
            return FileAttachmentResponse(
                success=False,
                message=f"Failed to attach file: {str(e)}"
            )

    def search_files(self, filters: FileSearchFilters, user_id: str) -> FileSearchResponse:
        """Search files with filtering and pagination.
        
        Args:
            filters: Search filters and criteria
            user_id: ID of the requesting user
            
        Returns:
            File search response with matching files
            
        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        logger.info(f"Searching files for user {user_id} with filters: {filters.dict()}")
        
        try:
            # Build base query with access control
            query = self.db.query(File)
            
            # Apply role-based access control
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            if user.role == UserRole.CLIENT:
                # Clients can only see their own files or public files
                query = query.filter(
                    or_(
                        File.uploaded_by_id == user_id,
                        File.is_public == True
                    )
                )
            elif user.role == UserRole.PROJECT_MANAGER:
                # Project managers can see files they uploaded, public files, or files in their proposals
                query = query.filter(
                    or_(
                        File.uploaded_by_id == user_id,
                        File.is_public == True,
                        File.proposal_id.in_(
                            self.db.query(Proposal.id).filter(
                                or_(
                                    Proposal.creator_id == user_id,
                                    Proposal.assigned_to_id == user_id
                                )
                            )
                        )
                    )
                )
            # Admins can see all files (no additional filter)
            
            # Apply search filters
            query = self._apply_file_search_filters(query, filters)
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply pagination and ordering
            query = query.order_by(desc(File.created_at))
            query = query.offset(filters.offset).limit(filters.limit)
            
            files = query.all()
            
            # Convert to FileInfo objects
            file_infos = [FileInfo.from_orm(file) for file in files]
            
            return FileSearchResponse(
                files=file_infos,
                total_count=total_count,
                has_more=total_count > (filters.offset + len(files)),
                filters_applied=filters.dict(exclude_unset=True)
            )
            
        except Exception as e:
            logger.error(f"Error searching files for user {user_id}: {str(e)}")
            raise

    def get_proposal_files(self, proposal_id: str, user_id: str) -> List[FileInfo]:
        """Get all files attached to a specific proposal.
        
        Args:
            proposal_id: ID of the proposal
            user_id: ID of the requesting user
            
        Returns:
            List of files attached to the proposal
            
        Raises:
            ValueError: If proposal_id or user_id is invalid
            PermissionError: If user lacks access permissions
        """
        if not proposal_id or not user_id:
            raise ValueError("Proposal ID and user ID are required")
        
        logger.info(f"Getting files for proposal {proposal_id} requested by user {user_id}")
        
        try:
            # Verify proposal exists and user has access
            proposal = self.db.query(Proposal).filter(Proposal.id == proposal_id).first()
            if not proposal:
                raise ValueError("Proposal not found")
            
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # Check proposal access permission
            if not self._check_proposal_access_permission(proposal, user):
                raise PermissionError("Insufficient permissions to access this proposal")
            
            # Get files attached to the proposal
            files = self.db.query(File).filter(
                and_(
                    File.proposal_id == proposal_id,
                    File.status != FileStatus.DELETED
                )
            ).order_by(desc(File.created_at)).all()
            
            return [FileInfo.from_orm(file) for file in files]
            
        except Exception as e:
            logger.error(f"Error getting files for proposal {proposal_id}: {str(e)}")
            raise

    def delete_file(self, file_id: str, user_id: str) -> bool:
        """Soft delete a file.
        
        Args:
            file_id: ID of the file to delete
            user_id: ID of the user requesting deletion
            
        Returns:
            True if deletion was successful, False otherwise
            
        Raises:
            ValueError: If file_id or user_id is invalid
            PermissionError: If user lacks deletion permissions
        """
        if not file_id or not user_id:
            raise ValueError("File ID and user ID are required")
        
        logger.info(f"Deleting file {file_id} requested by user {user_id}")
        
        try:
            file_record = self.db.query(File).filter(File.id == file_id).first()
            if not file_record:
                return False
            
            # Check deletion permissions
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # Only file uploader, admins, or proposal owners can delete files
            can_delete = (
                file_record.uploaded_by_id == user_id or
                user.role == UserRole.ADMIN or
                (file_record.proposal_id and 
                 self.db.query(Proposal).filter(
                     and_(
                         Proposal.id == file_record.proposal_id,
                         or_(
                             Proposal.creator_id == user_id,
                             Proposal.assigned_to_id == user_id
                         )
                     )
                 ).first())
            )
            
            if not can_delete:
                raise PermissionError("Insufficient permissions to delete this file")
            
            # Soft delete the file
            file_record.status = FileStatus.DELETED
            file_record.deleted_at = datetime.utcnow()
            file_record.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            # Log the deletion
            self._log_file_access(file_id, user_id, "delete")
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            raise

    def _validate_file(self, file_data: BinaryIO, upload_request: FileUploadRequest) -> FileSecurityValidation:
        """Validate file for security and compliance.
        
        Args:
            file_data: Binary file data
            upload_request: Upload request details
            
        Returns:
            File security validation result
        """
        warnings = []
        blocked_reasons = []
        
        # Check file size
        file_data.seek(0, 2)  # Seek to end
        file_size = file_data.tell()
        file_data.seek(0)  # Reset to beginning
        
        if file_size > self.MAX_FILE_SIZE:
            blocked_reasons.append(f"File size ({file_size} bytes) exceeds maximum allowed ({self.MAX_FILE_SIZE} bytes)")
        
        # Check file extension
        file_extension = self._get_file_extension(upload_request.filename).lower()
        file_type = upload_request.file_type
        
        if file_extension not in self.SUPPORTED_EXTENSIONS.get(file_type, []):
            blocked_reasons.append(f"File extension {file_extension} not supported for type {file_type.value}")
        
        # Basic content validation (check if file starts with expected magic bytes)
        file_data.seek(0)
        file_header = file_data.read(512)
        file_data.seek(0)
        
        if not self._validate_file_content(file_header, file_extension):
            warnings.append("File content may not match file extension")
        
        # Check filename for suspicious patterns
        if self._has_suspicious_filename(upload_request.filename):
            warnings.append("Filename contains potentially suspicious characters")
        
        return FileSecurityValidation(
            is_safe=len(blocked_reasons) == 0,
            scan_results={"file_size": file_size, "file_extension": file_extension},
            warnings=warnings,
            blocked_reasons=blocked_reasons
        )

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename.
        
        Args:
            filename: Original filename
            
        Returns:
            File extension including the dot
        """
        return Path(filename).suffix.lower()

    def _determine_file_type(self, file_extension: str) -> FileType:
        """Determine file type from extension.
        
        Args:
            file_extension: File extension
            
        Returns:
            FileType enum value
        """
        for file_type, extensions in self.SUPPORTED_EXTENSIONS.items():
            if file_extension in extensions:
                return file_type
        
        return FileType.DOCUMENT  # Default fallback

    def _create_storage_path(self, proposal_id: Optional[str], file_type: FileType, 
                           file_id: str, file_extension: str) -> Path:
        """Create storage path for file.
        
        Args:
            proposal_id: Optional proposal ID
            file_type: Type of file
            file_id: Unique file ID
            file_extension: File extension
            
        Returns:
            Path object for file storage
        """
        if proposal_id:
            storage_path = self.storage_base_path / "proposals" / proposal_id / file_type.value
        else:
            storage_path = self.storage_base_path / "general" / file_type.value
        
        storage_path.mkdir(parents=True, exist_ok=True)
        
        return storage_path / f"{file_id}{file_extension}"

    def _save_file_to_storage(self, file_data: BinaryIO, storage_path: Path) -> int:
        """Save file data to storage path.
        
        Args:
            file_data: Binary file data
            storage_path: Path to save file
            
        Returns:
            File size in bytes
        """
        file_data.seek(0)
        with open(storage_path, 'wb') as f:
            content = file_data.read()
            f.write(content)
            return len(content)

    def _generate_safe_filename(self, original_filename: str) -> str:
        """Generate a safe filename for storage.
        
        Args:
            original_filename: Original filename
            
        Returns:
            Safe filename for storage
        """
        # Remove or replace unsafe characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
        safe_filename = ''.join(c if c in safe_chars else '_' for c in original_filename)
        
        # Ensure filename is not too long
        if len(safe_filename) > 100:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:100-len(ext)] + ext
        
        return safe_filename

    def _check_file_access_permission(self, file_record: File, user_id: str) -> bool:
        """Check if user has permission to access file.
        
        Args:
            file_record: File record to check
            user_id: ID of the requesting user
            
        Returns:
            True if user has access permission, False otherwise
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # File uploader always has access
        if file_record.uploaded_by_id == user_id:
            return True
        
        # Public files are accessible to all authenticated users
        if file_record.is_public:
            return True
        
        # Admins have access to all files
        if user.role == UserRole.ADMIN:
            return True
        
        # If file is attached to a proposal, check proposal access
        if file_record.proposal_id:
            proposal = self.db.query(Proposal).filter(Proposal.id == file_record.proposal_id).first()
            if proposal:
                return self._check_proposal_access_permission(proposal, user)
        
        return False

    def _check_proposal_access_permission(self, proposal: Proposal, user: User) -> bool:
        """Check if user has permission to access proposal.
        
        Args:
            proposal: Proposal to check
            user: User requesting access
            
        Returns:
            True if user has access permission, False otherwise
        """
        # Proposal creator has access
        if proposal.creator_id == user.id:
            return True
        
        # Assigned user has access
        if proposal.assigned_to_id == user.id:
            return True
        
        # Admins have access to all proposals
        if user.role == UserRole.ADMIN:
            return True
        
        # Project managers have access to proposals in their domain
        if user.role == UserRole.PROJECT_MANAGER:
            return True
        
        return False

    def _check_proposal_modification_permission(self, proposal: Proposal, user: User) -> bool:
        """Check if user has permission to modify proposal.
        
        Args:
            proposal: Proposal to check
            user: User requesting modification
            
        Returns:
            True if user has modification permission, False otherwise
        """
        # Proposal creator can modify
        if proposal.creator_id == user.id:
            return True
        
        # Assigned user can modify
        if proposal.assigned_to_id == user.id:
            return True
        
        # Admins can modify all proposals
        if user.role == UserRole.ADMIN:
            return True
        
        return False

    def _apply_file_search_filters(self, query, filters: FileSearchFilters):
        """Apply search filters to file query.
        
        Args:
            query: SQLAlchemy query object
            filters: Search filters to apply
            
        Returns:
            Filtered query object
        """
        if filters.file_type:
            query = query.filter(File.file_type == filters.file_type)
        
        if filters.proposal_id:
            query = query.filter(File.proposal_id == filters.proposal_id)
        
        if filters.uploaded_by_id:
            query = query.filter(File.uploaded_by_id == filters.uploaded_by_id)
        
        if filters.status:
            query = query.filter(File.status == filters.status)
        
        if filters.date_from:
            query = query.filter(File.created_at >= filters.date_from)
        
        if filters.date_to:
            query = query.filter(File.created_at <= filters.date_to)
        
        if filters.filename_search:
            search_term = f"%{filters.filename_search}%"
            query = query.filter(
                or_(
                    File.filename.ilike(search_term),
                    File.original_filename.ilike(search_term)
                )
            )
        
        if filters.is_public is not None:
            query = query.filter(File.is_public == filters.is_public)
        
        # Exclude deleted files by default
        query = query.filter(File.status != FileStatus.DELETED)
        
        return query

    def _generate_access_url(self, file_record: File, access_type: str) -> str:
        """Generate secure access URL for file.
        
        Args:
            file_record: File record
            access_type: Type of access (download, view, preview)
            
        Returns:
            Secure access URL
        """
        # In production, this would generate a signed URL with expiration
        # For now, return a simple URL pattern
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        return f"{base_url}/api/v1/files/{file_record.id}/download?access_type={access_type}"

    def _log_file_access(self, file_id: str, user_id: str, access_type: str, 
                        ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        """Log file access for audit purposes.
        
        Args:
            file_id: ID of the accessed file
            user_id: ID of the user accessing the file
            access_type: Type of access
            ip_address: Optional IP address
            user_agent: Optional user agent string
        """
        try:
            access_log = FileAccess(
                id=str(uuid.uuid4()),
                file_id=file_id,
                user_id=user_id,
                access_type=access_type,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(access_log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging file access: {str(e)}")
            # Don't raise exception for logging failures

    def _validate_file_content(self, file_header: bytes, file_extension: str) -> bool:
        """Validate file content matches extension using magic bytes.
        
        Args:
            file_header: First 512 bytes of file
            file_extension: File extension
            
        Returns:
            True if content appears to match extension, False otherwise
        """
        # Basic magic byte validation
        magic_bytes = {
            '.pdf': b'%PDF',
            '.jpg': b'\xff\xd8\xff',
            '.jpeg': b'\xff\xd8\xff',
            '.png': b'\x89PNG\r\n\x1a\n',
            '.gif': b'GIF8',
            '.bmp': b'BM',
            '.webp': b'RIFF',
            '.doc': b'\xd0\xcf\x11\xe0',
            '.docx': b'PK\x03\x04',
            '.xls': b'\xd0\xcf\x11\xe0',
            '.xlsx': b'PK\x03\x04',
            '.ppt': b'\xd0\xcf\x11\xe0',
            '.pptx': b'PK\x03\x04',
        }
        
        expected_magic = magic_bytes.get(file_extension)
        if expected_magic:
            return file_header.startswith(expected_magic)
        
        # For file types without specific magic bytes, assume valid
        return True

    def _has_suspicious_filename(self, filename: str) -> bool:
        """Check if filename contains suspicious patterns.
        
        Args:
            filename: Filename to check
            
        Returns:
            True if filename appears suspicious, False otherwise
        """
        suspicious_patterns = [
            '..', '/', '\\', '<', '>', ':', '"', '|', '?', '*',
            'script', 'javascript', 'vbscript', 'onload', 'onerror'
        ]
        
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in suspicious_patterns) 