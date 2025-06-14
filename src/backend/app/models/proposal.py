"""
Proposal database models.
Handles proposal, version control, project phase tracking, sharing, and audit trail.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class ProjectPhaseEnum(enum.Enum):
    """Project phase enumeration."""
    EXPLORATORY = "exploratory"
    DISCOVERY = "discovery"
    DEVELOPMENT = "development"
    DEPLOYMENT = "deployment"


class ProposalStatusEnum(enum.Enum):
    """Proposal status enumeration."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class SharePermissionEnum(enum.Enum):
    """Proposal sharing permission levels."""
    VIEW_ONLY = "view_only"
    COMMENT = "comment"
    EDIT = "edit"
    FULL_ACCESS = "full_access"


class ExportFormatEnum(enum.Enum):
    """Proposal export format options."""
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"


class AuditActionEnum(enum.Enum):
    """Audit trail action types."""
    CREATED = "created"
    UPDATED = "updated"
    SHARED = "shared"
    EXPORTED = "exported"
    STATUS_CHANGED = "status_changed"
    VERSION_CREATED = "version_created"
    ACCESS_GRANTED = "access_granted"
    ACCESS_REVOKED = "access_revoked"


class Proposal(Base):
    """
    Main proposal model.
    Stores proposal metadata and current content.
    """
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(255), nullable=False, index=True)
    client_name = Column(String(255), nullable=False, index=True)
    phase = Column(Enum(ProjectPhaseEnum), nullable=False, default=ProjectPhaseEnum.EXPLORATORY)
    status = Column(Enum(ProposalStatusEnum), nullable=False, default=ProposalStatusEnum.DRAFT)
    
    # Content fields
    content = Column(Text, nullable=True)  # Generated proposal HTML/markdown
    ai_summary = Column(Text, nullable=True)  # AI-generated meeting summary
    extracted_requirements = Column(Text, nullable=True)  # JSON string of requirements
    
    # File references
    transcript_path = Column(String(500), nullable=True)  # Path to uploaded transcript
    
    # Sharing and access control
    is_public = Column(Boolean, default=False)  # Public access flag
    share_token = Column(String(255), nullable=True, unique=True)  # Unique sharing token
    client_access_enabled = Column(Boolean, default=False)  # Client portal access
    
    # Export tracking
    last_exported_at = Column(DateTime(timezone=True), nullable=True)
    export_count = Column(Integer, default=0)
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    versions = relationship("ProposalVersion", back_populates="proposal", cascade="all, delete-orphan")
    creator = relationship("User", back_populates="proposals")
    shares = relationship("ProposalShare", back_populates="proposal", cascade="all, delete-orphan")
    exports = relationship("ProposalExport", back_populates="proposal", cascade="all, delete-orphan")
    audit_logs = relationship("ProposalAuditLog", back_populates="proposal", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        """String representation of proposal."""
        return f"<Proposal(id={self.id}, project='{self.project_name}', client='{self.client_name}')>"


class ProposalVersion(Base):
    """
    Proposal version control model.
    Tracks changes and maintains history.
    """
    __tablename__ = "proposal_versions"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    
    # Version content
    content = Column(Text, nullable=False)
    change_summary = Column(String(500), nullable=True)  # Summary of what changed
    content_diff = Column(Text, nullable=True)  # JSON diff from previous version
    
    # Version metadata
    size_bytes = Column(Integer, nullable=True)  # Content size for tracking
    word_count = Column(Integer, nullable=True)  # Word count for analytics
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_current = Column(Boolean, default=False)  # Mark current active version
    
    # Relationships
    proposal = relationship("Proposal", back_populates="versions")
    creator = relationship("User")
    
    def __repr__(self) -> str:
        """String representation of proposal version."""
        return f"<ProposalVersion(id={self.id}, proposal_id={self.proposal_id}, version={self.version_number})>"


class ProposalShare(Base):
    """
    Proposal sharing model.
    Manages access control and sharing permissions.
    """
    __tablename__ = "proposal_shares"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=False)
    shared_with_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for public shares
    shared_with_email = Column(String(255), nullable=True)  # For external sharing
    
    # Permission settings
    permission_level = Column(Enum(SharePermissionEnum), nullable=False, default=SharePermissionEnum.VIEW_ONLY)
    can_download = Column(Boolean, default=False)
    can_comment = Column(Boolean, default=False)
    
    # Access control
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    is_active = Column(Boolean, default=True)
    access_count = Column(Integer, default=0)  # Track usage
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    shared_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    proposal = relationship("Proposal", back_populates="shares")
    shared_with_user = relationship("User", foreign_keys=[shared_with_user_id])
    shared_by_user = relationship("User", foreign_keys=[shared_by])
    
    def __repr__(self) -> str:
        """String representation of proposal share."""
        return f"<ProposalShare(id={self.id}, proposal_id={self.proposal_id}, permission='{self.permission_level}')>"


class ProposalExport(Base):
    """
    Proposal export tracking model.
    Tracks export history and generated files.
    """
    __tablename__ = "proposal_exports"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=False)
    
    # Export details
    format = Column(Enum(ExportFormatEnum), nullable=False)
    file_path = Column(String(500), nullable=False)  # Path to exported file
    file_size_bytes = Column(Integer, nullable=True)
    
    # Export metadata
    export_settings = Column(JSON, nullable=True)  # JSON settings used for export
    version_exported = Column(Integer, nullable=True)  # Version number exported
    
    # Access tracking
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    exported_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    proposal = relationship("Proposal", back_populates="exports")
    exporter = relationship("User")
    
    def __repr__(self) -> str:
        """String representation of proposal export."""
        return f"<ProposalExport(id={self.id}, proposal_id={self.proposal_id}, format='{self.format}')>"


class ProposalAuditLog(Base):
    """
    Proposal audit trail model.
    Tracks all actions performed on proposals for compliance and history.
    """
    __tablename__ = "proposal_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=False)
    
    # Action details
    action = Column(Enum(AuditActionEnum), nullable=False)
    description = Column(String(500), nullable=False)
    details = Column(JSON, nullable=True)  # Additional action details
    
    # Context information
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6 address
    user_agent = Column(String(500), nullable=True)  # Browser/client info
    
    # Change tracking
    old_values = Column(JSON, nullable=True)  # Previous values (for updates)
    new_values = Column(JSON, nullable=True)  # New values (for updates)
    
    # Metadata
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    proposal = relationship("Proposal", back_populates="audit_logs")
    performer = relationship("User")
    
    def __repr__(self) -> str:
        """String representation of proposal audit log."""
        return f"<ProposalAuditLog(id={self.id}, proposal_id={self.proposal_id}, action='{self.action}')>"


class ProjectTracker(Base):
    """
    Project tracking model.
    Links proposals to project lifecycle phases.
    """
    __tablename__ = "project_trackers"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=False)
    
    # Project details
    project_name = Column(String(255), nullable=False, index=True)
    client_name = Column(String(255), nullable=False, index=True)
    current_phase = Column(Enum(ProjectPhaseEnum), nullable=False)
    
    # Phase tracking
    exploratory_completed = Column(Boolean, default=False)
    discovery_completed = Column(Boolean, default=False)
    development_completed = Column(Boolean, default=False)
    deployment_completed = Column(Boolean, default=False)
    
    # Timeline
    start_date = Column(DateTime(timezone=True), nullable=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    actual_completion = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    proposal = relationship("Proposal")
    creator = relationship("User")
    
    def __repr__(self) -> str:
        """String representation of project tracker."""
        return f"<ProjectTracker(id={self.id}, project='{self.project_name}', phase='{self.current_phase}')>"


class ProposalTemplate(Base):
    """
    Proposal template model.
    Stores reusable proposal templates.
    """
    __tablename__ = "proposal_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Template content
    html_template = Column(Text, nullable=False)  # HTML template content
    css_styles = Column(Text, nullable=True)  # Associated CSS styles
    
    # Template metadata
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")
    
    def __repr__(self) -> str:
        """String representation of proposal template."""
        return f"<ProposalTemplate(id={self.id}, name='{self.name}')>" 