"""
Proposal database models.
Handles proposal, version control, and project phase tracking.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
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
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    versions = relationship("ProposalVersion", back_populates="proposal", cascade="all, delete-orphan")
    creator = relationship("User", back_populates="proposals")
    
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