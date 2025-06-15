"""
File management schemas for JDA AI Portal.
Provides Pydantic models for file upload, management, and access control.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.file import FileType, FileStatus


class FileUploadRequest(BaseModel):
    """File upload request structure.
    
    Args:
        filename: Original filename
        file_type: Type of file being uploaded
        proposal_id: Optional proposal ID to attach file to
        is_public: Whether the file should be publicly accessible
        description: Optional file description
    """
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Type of file being uploaded")
    proposal_id: Optional[str] = Field(None, description="Optional proposal ID to attach to")
    is_public: bool = Field(default=False, description="Whether file is publicly accessible")
    description: Optional[str] = Field(None, description="Optional file description")

    @validator('filename')
    def validate_filename(cls, v: str) -> str:
        """Validate filename is not empty and has reasonable length.
        
        Args:
            v: Filename to validate
            
        Returns:
            Validated filename
            
        Raises:
            ValueError: If filename is invalid
        """
        if not v or not v.strip():
            raise ValueError("Filename cannot be empty")
        if len(v) > 255:
            raise ValueError("Filename too long (max 255 characters)")
        return v.strip()


class FileUploadResponse(BaseModel):
    """File upload response structure.
    
    Args:
        success: Whether the upload was successful
        file_id: ID of the uploaded file
        upload_url: URL for uploading the file (if using presigned URLs)
        message: Response message
        file_info: Basic file information
    """
    success: bool = Field(..., description="Whether upload was successful")
    file_id: Optional[str] = Field(None, description="ID of uploaded file")
    upload_url: Optional[str] = Field(None, description="URL for file upload")
    message: str = Field(..., description="Response message")
    file_info: Optional[Dict[str, Any]] = Field(None, description="Basic file information")


class FileInfo(BaseModel):
    """File information structure.
    
    Args:
        id: File ID
        filename: Current filename
        original_filename: Original filename when uploaded
        file_type: Type of file
        file_extension: File extension
        file_size: File size in bytes
        mime_type: MIME type of the file
        status: Current file status
        is_public: Whether file is publicly accessible
        uploaded_by_id: ID of user who uploaded the file
        proposal_id: ID of associated proposal (if any)
        created_at: Upload timestamp
        updated_at: Last update timestamp
    """
    id: str = Field(..., description="File ID")
    filename: str = Field(..., description="Current filename")
    original_filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Type of file")
    file_extension: str = Field(..., description="File extension")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    status: FileStatus = Field(..., description="Current file status")
    is_public: bool = Field(..., description="Whether file is publicly accessible")
    uploaded_by_id: str = Field(..., description="ID of user who uploaded")
    proposal_id: Optional[str] = Field(None, description="Associated proposal ID")
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class FileAccessRequest(BaseModel):
    """File access request structure.
    
    Args:
        file_id: ID of file to access
        access_type: Type of access (download, view, preview)
        user_agent: User agent string (optional)
    """
    file_id: str = Field(..., description="ID of file to access")
    access_type: str = Field(..., description="Type of access")
    user_agent: Optional[str] = Field(None, description="User agent string")

    @validator('access_type')
    def validate_access_type(cls, v: str) -> str:
        """Validate access type is allowed.
        
        Args:
            v: Access type to validate
            
        Returns:
            Validated access type
            
        Raises:
            ValueError: If access type is invalid
        """
        allowed_types = ['download', 'view', 'preview']
        if v not in allowed_types:
            raise ValueError(f"Access type must be one of: {allowed_types}")
        return v


class FileAccessResponse(BaseModel):
    """File access response structure.
    
    Args:
        success: Whether access was granted
        download_url: URL for downloading/accessing the file
        expires_at: When the access URL expires
        message: Response message
        file_info: File information
    """
    success: bool = Field(..., description="Whether access was granted")
    download_url: Optional[str] = Field(None, description="URL for file access")
    expires_at: Optional[datetime] = Field(None, description="URL expiration time")
    message: str = Field(..., description="Response message")
    file_info: Optional[FileInfo] = Field(None, description="File information")


class FileAttachmentRequest(BaseModel):
    """File attachment to proposal request structure.
    
    Args:
        file_id: ID of file to attach
        proposal_id: ID of proposal to attach to
        attachment_type: Type of attachment (document, image, etc.)
        description: Optional attachment description
    """
    file_id: str = Field(..., description="ID of file to attach")
    proposal_id: str = Field(..., description="ID of proposal to attach to")
    attachment_type: Optional[str] = Field(None, description="Type of attachment")
    description: Optional[str] = Field(None, description="Attachment description")


class FileAttachmentResponse(BaseModel):
    """File attachment response structure.
    
    Args:
        success: Whether attachment was successful
        message: Response message
        attachment_id: ID of the attachment record
        file_info: Information about the attached file
    """
    success: bool = Field(..., description="Whether attachment was successful")
    message: str = Field(..., description="Response message")
    attachment_id: Optional[str] = Field(None, description="ID of attachment record")
    file_info: Optional[FileInfo] = Field(None, description="Attached file information")


class FileSearchFilters(BaseModel):
    """File search and filter criteria.
    
    Args:
        file_type: Filter by file type
        proposal_id: Filter by proposal ID
        uploaded_by_id: Filter by uploader user ID
        status: Filter by file status
        date_from: Filter files uploaded after this date
        date_to: Filter files uploaded before this date
        filename_search: Search in filenames
        is_public: Filter by public/private status
        limit: Maximum number of results
        offset: Pagination offset
    """
    file_type: Optional[FileType] = Field(None, description="Filter by file type")
    proposal_id: Optional[str] = Field(None, description="Filter by proposal ID")
    uploaded_by_id: Optional[str] = Field(None, description="Filter by uploader")
    status: Optional[FileStatus] = Field(None, description="Filter by file status")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    filename_search: Optional[str] = Field(None, description="Search in filenames")
    is_public: Optional[bool] = Field(None, description="Filter by public status")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class FileSearchResponse(BaseModel):
    """File search response structure.
    
    Args:
        files: List of matching files
        total_count: Total number of matching files
        has_more: Whether there are more results
        filters_applied: Summary of applied filters
    """
    files: List[FileInfo] = Field(..., description="List of matching files")
    total_count: int = Field(..., description="Total number of matching files")
    has_more: bool = Field(..., description="Whether there are more results")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters summary")


class FileSecurityValidation(BaseModel):
    """File security validation result.
    
    Args:
        is_safe: Whether the file passed security validation
        scan_results: Results of security scans
        warnings: List of security warnings
        blocked_reasons: Reasons why file was blocked (if any)
    """
    is_safe: bool = Field(..., description="Whether file passed security validation")
    scan_results: Dict[str, Any] = Field(default_factory=dict, description="Security scan results")
    warnings: List[str] = Field(default_factory=list, description="Security warnings")
    blocked_reasons: List[str] = Field(default_factory=list, description="Reasons for blocking file") 