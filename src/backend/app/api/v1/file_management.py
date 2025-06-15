"""
File management API endpoints for JDA AI Portal.
Provides REST API for file upload, download, attachment, and management operations.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import logging
import io
from pathlib import Path

from ...core.database import get_db
from ...core.auth import get_current_user, require_role
from ...models.user import User, UserRole
from ...models.file import FileType
from ...services.file_service import FileService
from ...schemas.file import (
    FileUploadRequest, FileUploadResponse, FileInfo, FileAccessRequest,
    FileAccessResponse, FileAttachmentRequest, FileAttachmentResponse,
    FileSearchFilters, FileSearchResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["file-management"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    file_type: FileType = Form(..., description="Type of file being uploaded"),
    proposal_id: Optional[str] = Form(None, description="Optional proposal ID to attach to"),
    is_public: bool = Form(False, description="Whether file should be publicly accessible"),
    description: Optional[str] = Form(None, description="Optional file description"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FileUploadResponse:
    """Upload a file to the system.
    
    This endpoint handles file uploads with security validation, storage management,
    and optional proposal attachment. Supports multiple file types with size limits.
    
    Args:
        file: File to upload (multipart/form-data)
        file_type: Type of file being uploaded
        proposal_id: Optional proposal ID to attach file to
        is_public: Whether file should be publicly accessible
        description: Optional file description
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        File upload response with success status and file information
        
    Raises:
        HTTPException: If upload fails, file is invalid, or user lacks permissions
    """
    logger.info(f"File upload requested by user {current_user.id}: {file.filename}")
    
    try:
        # Validate file size
        if file.size and file.size > FileService.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file.size} bytes) exceeds maximum allowed ({FileService.MAX_FILE_SIZE} bytes)"
            )
        
        # Create upload request
        upload_request = FileUploadRequest(
            filename=file.filename,
            file_type=file_type,
            proposal_id=proposal_id,
            is_public=is_public,
            description=description
        )
        
        # Read file data
        file_data = io.BytesIO(await file.read())
        
        # Process upload
        file_service = FileService(db)
        result = file_service.upload_file(
            file_data=file_data,
            upload_request=upload_request,
            uploaded_by_id=str(current_user.id)
        )
        
        if result.success:
            logger.info(f"File uploaded successfully: {result.file_id}")
        else:
            logger.warning(f"File upload failed: {result.message}")
        
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid upload data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid upload data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )


@router.get("/{file_id}", response_model=FileInfo)
async def get_file_info(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FileInfo:
    """Get file information and metadata.
    
    This endpoint returns detailed information about a file including metadata,
    status, and access permissions. Access is controlled based on user permissions.
    
    Args:
        file_id: ID of the file to retrieve information for
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        File information including metadata and status
        
    Raises:
        HTTPException: If file not found or user lacks access permissions
    """
    logger.info(f"File info requested for {file_id} by user {current_user.id}")
    
    try:
        file_service = FileService(db)
        file_info = file_service.get_file_info(
            file_id=file_id,
            user_id=str(current_user.id)
        )
        
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        logger.info(f"File info retrieved successfully for {file_id}")
        return file_info
        
    except HTTPException:
        raise
    except PermissionError as e:
        logger.warning(f"Permission denied for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this file"
        )
    except Exception as e:
        logger.error(f"Error retrieving file info for {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file information"
        )


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    access_type: str = Query("download", description="Type of access (download, view, preview)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download or access a file.
    
    This endpoint provides secure file access with permission checking and
    audit logging. Supports different access types for various use cases.
    
    Args:
        file_id: ID of the file to download
        access_type: Type of access (download, view, preview)
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        File content as streaming response or file response
        
    Raises:
        HTTPException: If file not found or user lacks access permissions
    """
    logger.info(f"File download requested for {file_id} by user {current_user.id} (type: {access_type})")
    
    try:
        file_service = FileService(db)
        
        # Get file access URL/permission
        access_request = FileAccessRequest(
            file_id=file_id,
            access_type=access_type
        )
        
        access_response = file_service.get_file_access_url(
            access_request=access_request,
            user_id=str(current_user.id)
        )
        
        if not access_response.success:
            if "not found" in access_response.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=access_response.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=access_response.message
                )
        
        # Get file info for actual file serving
        file_info = access_response.file_info
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File information not available"
            )
        
        # Serve the actual file
        file_path = Path(file_info.storage_path)
        if not file_path.exists():
            logger.error(f"File not found on disk: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on storage"
            )
        
        # Determine response type based on access type
        if access_type == "download":
            return FileResponse(
                path=str(file_path),
                filename=file_info.original_filename,
                media_type=file_info.mime_type
            )
        else:
            # For view/preview, return as streaming response
            def file_generator():
                with open(file_path, "rb") as f:
                    while chunk := f.read(8192):
                        yield chunk
            
            return StreamingResponse(
                file_generator(),
                media_type=file_info.mime_type,
                headers={
                    "Content-Disposition": f"inline; filename={file_info.original_filename}"
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )


@router.get("/proposal/{proposal_id}", response_model=List[FileInfo])
async def get_proposal_files(
    proposal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[FileInfo]:
    """Get all files attached to a specific proposal.
    
    This endpoint returns all files associated with a proposal, with access
    control based on user permissions for the proposal.
    
    Args:
        proposal_id: ID of the proposal to get files for
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        List of files attached to the proposal
        
    Raises:
        HTTPException: If proposal not found or user lacks access permissions
    """
    logger.info(f"Proposal files requested for {proposal_id} by user {current_user.id}")
    
    try:
        file_service = FileService(db)
        files = file_service.get_proposal_files(
            proposal_id=proposal_id,
            user_id=str(current_user.id)
        )
        
        logger.info(f"Retrieved {len(files)} files for proposal {proposal_id}")
        return files
        
    except ValueError as e:
        logger.error(f"Invalid proposal ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid proposal ID: {str(e)}"
        )
    except PermissionError as e:
        logger.warning(f"Permission denied for proposal {proposal_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this proposal's files"
        )
    except Exception as e:
        logger.error(f"Error retrieving files for proposal {proposal_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve proposal files"
        )


@router.post("/attach-to-proposal", response_model=FileAttachmentResponse)
async def attach_file_to_proposal(
    attachment: FileAttachmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FileAttachmentResponse:
    """Attach an existing file to a proposal.
    
    This endpoint allows users to attach previously uploaded files to proposals,
    with permission checking for both file access and proposal modification.
    
    Args:
        attachment: File attachment request details
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        File attachment response with success status
        
    Raises:
        HTTPException: If attachment fails or user lacks permissions
    """
    logger.info(f"File attachment requested: {attachment.file_id} -> {attachment.proposal_id}")
    
    try:
        file_service = FileService(db)
        result = file_service.attach_file_to_proposal(
            attachment_request=attachment,
            user_id=str(current_user.id)
        )
        
        if result.success:
            logger.info(f"File {attachment.file_id} attached successfully to proposal {attachment.proposal_id}")
        else:
            logger.warning(f"File attachment failed: {result.message}")
        
        return result
        
    except ValueError as e:
        logger.error(f"Invalid attachment data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid attachment data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error attaching file to proposal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to attach file to proposal"
        )


@router.get("/search", response_model=FileSearchResponse)
async def search_files(
    file_type: Optional[FileType] = Query(None, description="Filter by file type"),
    proposal_id: Optional[str] = Query(None, description="Filter by proposal ID"),
    uploaded_by_id: Optional[str] = Query(None, description="Filter by uploader user ID"),
    filename_search: Optional[str] = Query(None, description="Search in filenames"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FileSearchResponse:
    """Search files with filtering and pagination.
    
    This endpoint provides comprehensive file search capabilities with various
    filters and pagination. Results are filtered based on user access permissions.
    
    Args:
        file_type: Optional file type filter
        proposal_id: Optional proposal ID filter
        uploaded_by_id: Optional uploader filter
        filename_search: Optional filename search
        is_public: Optional public/private filter
        limit: Maximum results to return
        offset: Pagination offset
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        File search response with matching files and pagination info
        
    Raises:
        HTTPException: If search fails or user lacks permissions
    """
    logger.info(f"File search requested by user {current_user.id}")
    
    try:
        # Build search filters
        filters = FileSearchFilters(
            file_type=file_type,
            proposal_id=proposal_id,
            uploaded_by_id=uploaded_by_id,
            filename_search=filename_search,
            is_public=is_public,
            limit=limit,
            offset=offset
        )
        
        file_service = FileService(db)
        result = file_service.search_files(
            filters=filters,
            user_id=str(current_user.id)
        )
        
        logger.info(f"File search completed: {len(result.files)} results for user {current_user.id}")
        return result
        
    except ValueError as e:
        logger.error(f"Invalid search parameters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search parameters: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error searching files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search files"
        )


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Delete a file (soft delete).
    
    This endpoint performs a soft delete on a file, marking it as deleted
    while preserving the record for audit purposes. Only file owners,
    admins, or proposal owners can delete files.
    
    Args:
        file_id: ID of the file to delete
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Success confirmation message
        
    Raises:
        HTTPException: If deletion fails or user lacks permissions
    """
    logger.info(f"File deletion requested for {file_id} by user {current_user.id}")
    
    try:
        file_service = FileService(db)
        success = file_service.delete_file(
            file_id=file_id,
            user_id=str(current_user.id)
        )
        
        if success:
            logger.info(f"File {file_id} deleted successfully")
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
    except HTTPException:
        raise
    except PermissionError as e:
        logger.warning(f"Permission denied for file deletion {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this file"
        )
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        ) 