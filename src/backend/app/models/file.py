from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from .base import Base

class FileType(str, Enum):
    """Enumeration of supported file types."""
    IMAGE = "image"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    TRANSCRIPT = "transcript"

class FileStatus(str, Enum):
    """Enumeration of file processing status."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"

class File(Base):
    """File model for managing uploaded files and attachments.
    
    This model handles file metadata, storage information, and relationships
    to proposals and users for the file management system.
    """
    __tablename__ = "files"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    file_type = Column(SQLEnum(FileType), nullable=False, index=True)
    file_extension = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    mime_type = Column(String, nullable=False)
    
    # Storage information
    storage_path = Column(String, nullable=False)
    storage_bucket = Column(String, nullable=True)  # For cloud storage
    
    # Status and processing
    status = Column(SQLEnum(FileStatus), default=FileStatus.UPLOADING, index=True)
    processing_error = Column(Text, nullable=True)
    
    # Security and access
    is_public = Column(Boolean, default=False, index=True)
    access_token = Column(String, nullable=True, index=True)  # For secure access
    
    # Relationships
    uploaded_by_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    proposal_id = Column(String, ForeignKey("proposals.id"), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    uploaded_by = relationship("User", back_populates="uploaded_files")
    proposal = relationship("Proposal", back_populates="files")
    
    def __repr__(self) -> str:
        return f"<File(id='{self.id}', filename='{self.filename}', type='{self.file_type}')>"

class FileAccess(Base):
    """File access tracking for audit and security purposes."""
    __tablename__ = "file_access"

    id = Column(String, primary_key=True, index=True)
    file_id = Column(String, ForeignKey("files.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    access_type = Column(String, nullable=False)  # 'download', 'view', 'preview'
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    accessed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    file = relationship("File")
    user = relationship("User")
    
    def __repr__(self) -> str:
        return f"<FileAccess(file_id='{self.file_id}', user_id='{self.user_id}', type='{self.access_type}')>" 