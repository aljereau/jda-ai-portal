"""
Proposal Pydantic schemas for API serialization.
Handles request/response models for proposal management.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class ProjectPhase(str, Enum):
    """Project phase enumeration for validation."""
    EXPLORATORY = "exploratory"
    DISCOVERY = "discovery"
    DEVELOPMENT = "development"
    DEPLOYMENT = "deployment"


class ProposalStatus(str, Enum):
    """Proposal status enumeration for validation."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class TranscriptUploadResponse(BaseModel):
    """Response model for transcript upload."""
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    project_name: str = Field(..., description="Project name")
    client_name: str = Field(..., description="Client company name")
    phase: ProjectPhase = Field(..., description="Project phase")
    ai_summary: str = Field(..., description="AI-generated meeting summary")
    extracted_requirements: Dict[str, Any] = Field(..., description="Extracted requirements")
    proposal_id: int = Field(..., description="Created proposal ID")
    upload_timestamp: datetime = Field(..., description="Upload timestamp")
    status: str = Field(..., description="Processing status")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProposalGenerateRequest(BaseModel):
    """Request model for proposal generation."""
    proposal_id: int = Field(..., description="Proposal ID to generate content for")
    requirements: Dict[str, Any] = Field(..., description="Project requirements")
    template_preferences: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Template customization preferences"
    )
    custom_sections: Optional[List[str]] = Field(
        default=None,
        description="Custom sections to include"
    )

    @validator('requirements')
    def validate_requirements(cls, v):
        """Validate requirements structure."""
        required_fields = ['scope', 'timeline', 'deliverables']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Requirements must include '{field}' field")
        return v


class ProposalCreate(BaseModel):
    """Schema for creating a new proposal."""
    project_name: str = Field(..., min_length=1, max_length=255)
    client_name: str = Field(..., min_length=1, max_length=255)
    phase: ProjectPhase = Field(default=ProjectPhase.EXPLORATORY)
    content: Optional[str] = Field(default=None)
    ai_summary: Optional[str] = Field(default=None)
    extracted_requirements: Optional[Dict[str, Any]] = Field(default=None)
    transcript_path: Optional[str] = Field(default=None)

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ProposalUpdate(BaseModel):
    """Schema for updating an existing proposal."""
    project_name: Optional[str] = Field(None, min_length=1, max_length=255)
    client_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phase: Optional[ProjectPhase] = Field(None)
    content: Optional[str] = Field(None)
    status: Optional[ProposalStatus] = Field(None)
    ai_summary: Optional[str] = Field(None)
    extracted_requirements: Optional[Dict[str, Any]] = Field(None)

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ProposalResponse(BaseModel):
    """Response model for proposal data."""
    id: int = Field(..., description="Proposal ID")
    project_name: str = Field(..., description="Project name")
    client_name: str = Field(..., description="Client company name")
    phase: ProjectPhase = Field(..., description="Project phase")
    status: ProposalStatus = Field(..., description="Proposal status")
    content: Optional[str] = Field(None, description="Proposal content")
    ai_summary: Optional[str] = Field(None, description="AI-generated summary")
    extracted_requirements: Optional[Dict[str, Any]] = Field(None, description="Extracted requirements")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: int = Field(..., description="Creator user ID")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        orm_mode = True


class ProposalVersionResponse(BaseModel):
    """Response model for proposal version data."""
    id: int = Field(..., description="Version ID")
    proposal_id: int = Field(..., description="Proposal ID")
    version_number: int = Field(..., description="Version number")
    content: str = Field(..., description="Version content")
    change_summary: Optional[str] = Field(None, description="Summary of changes")
    created_by: int = Field(..., description="Creator user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    is_current: bool = Field(..., description="Whether this is the current version")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        orm_mode = True


class ProposalTemplateResponse(BaseModel):
    """Response model for proposal template data."""
    id: int = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    html_template: str = Field(..., description="HTML template content")
    css_styles: Optional[str] = Field(None, description="CSS styles")
    is_default: bool = Field(..., description="Whether this is the default template")
    is_active: bool = Field(..., description="Whether this template is active")
    usage_count: int = Field(..., description="Number of times used")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        orm_mode = True


class ProjectTrackerResponse(BaseModel):
    """Response model for project tracking data."""
    id: int = Field(..., description="Tracker ID")
    proposal_id: int = Field(..., description="Associated proposal ID")
    project_name: str = Field(..., description="Project name")
    client_name: str = Field(..., description="Client name")
    current_phase: ProjectPhase = Field(..., description="Current project phase")
    exploratory_completed: bool = Field(..., description="Exploratory phase completed")
    discovery_completed: bool = Field(..., description="Discovery phase completed")
    development_completed: bool = Field(..., description="Development phase completed")
    deployment_completed: bool = Field(..., description="Deployment phase completed")
    start_date: Optional[datetime] = Field(None, description="Project start date")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion")
    actual_completion: Optional[datetime] = Field(None, description="Actual completion")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        orm_mode = True


class AIGenerationRequest(BaseModel):
    """Request model for AI content generation."""
    transcript_content: str = Field(..., description="Meeting transcript content")
    project_name: str = Field(..., description="Project name")
    client_name: str = Field(..., description="Client name")
    phase: ProjectPhase = Field(..., description="Project phase")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class AIGenerationResponse(BaseModel):
    """Response model for AI content generation."""
    summary: str = Field(..., description="AI-generated summary")
    requirements: Dict[str, Any] = Field(..., description="Extracted requirements")
    proposed_timeline: Optional[str] = Field(None, description="Proposed timeline")
    suggested_pricing: Optional[str] = Field(None, description="Suggested pricing structure")
    key_deliverables: List[str] = Field(..., description="Key deliverables identified")
    risks_and_assumptions: List[str] = Field(..., description="Identified risks and assumptions")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ProposalBlockType(str, Enum):
    """Proposal block type enumeration."""
    OVERVIEW = "overview"
    SCOPE = "scope"
    TIMELINE = "timeline"
    DELIVERABLES = "deliverables"
    PRICING = "pricing"
    RISKS = "risks"
    ASSUMPTIONS = "assumptions"
    SUPPORT = "support"
    PAYMENT = "payment"
    TERMS = "terms"
    CUSTOM = "custom"


class ProposalBlockRequest(BaseModel):
    """Request model for adding/editing proposal blocks."""
    block_type: ProposalBlockType = Field(..., description="Type of block to add")
    content: Optional[str] = Field(None, description="Block content (if not AI-generated)")
    position: Optional[int] = Field(None, description="Position to insert block (0-based)")
    use_ai_generation: bool = Field(default=True, description="Whether to use AI for content generation")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Context for AI generation")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ProposalBlockResponse(BaseModel):
    """Response model for proposal block operations."""
    proposal_id: int = Field(..., description="Proposal ID")
    block_id: str = Field(..., description="Generated block ID")
    block_type: ProposalBlockType = Field(..., description="Block type")
    content: str = Field(..., description="Block content")
    position: int = Field(..., description="Block position in proposal")
    updated_content: str = Field(..., description="Full updated proposal content")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ValidationStatus(str, Enum):
    """Validation status enumeration."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    PENDING = "pending"


class ValidationIssue(BaseModel):
    """Model for individual validation issues."""
    issue_type: str = Field(..., description="Type of validation issue")
    severity: str = Field(..., description="Issue severity (low, medium, high, critical)")
    description: str = Field(..., description="Issue description")
    suggestion: Optional[str] = Field(None, description="Suggested fix")
    section: Optional[str] = Field(None, description="Affected section")


class ProposalValidationResponse(BaseModel):
    """Response model for proposal validation."""
    proposal_id: int = Field(..., description="Proposal ID")
    validation_status: ValidationStatus = Field(..., description="Overall validation status")
    validation_score: float = Field(..., description="Validation score (0-100)")
    issues: List[ValidationIssue] = Field(..., description="List of validation issues")
    recommendations: List[str] = Field(..., description="Improvement recommendations")
    phase_alignment: Dict[str, Any] = Field(..., description="Phase alignment analysis")
    completeness_score: float = Field(..., description="Content completeness score (0-100)")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ProposalContextUpdateRequest(BaseModel):
    """Request model for updating proposal context."""
    phase: ProjectPhase = Field(..., description="New project phase")
    context_data: Dict[str, Any] = Field(..., description="Additional context information")
    regenerate_sections: List[str] = Field(default=[], description="Sections to regenerate")
    preserve_manual_edits: bool = Field(default=True, description="Whether to preserve manual edits")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


# Block 3: Enhanced Sharing, Export, and Audit Schemas

class SharePermissionLevel(str, Enum):
    """Share permission level enumeration."""
    VIEW_ONLY = "view_only"
    COMMENT = "comment"
    EDIT = "edit"
    FULL_ACCESS = "full_access"


class ExportFormat(str, Enum):
    """Export format enumeration."""
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"


class AuditAction(str, Enum):
    """Audit action enumeration."""
    CREATED = "created"
    UPDATED = "updated"
    SHARED = "shared"
    EXPORTED = "exported"
    STATUS_CHANGED = "status_changed"
    VERSION_CREATED = "version_created"
    ACCESS_GRANTED = "access_granted"
    ACCESS_REVOKED = "access_revoked"


class ProposalShareRequest(BaseModel):
    """Request model for creating proposal shares."""
    shared_with_user_id: Optional[int] = Field(None, description="User ID to share with (for internal users)")
    shared_with_email: Optional[str] = Field(None, description="Email to share with (for external users)")
    permission_level: SharePermissionLevel = Field(default=SharePermissionLevel.VIEW_ONLY, description="Permission level")
    can_download: bool = Field(default=False, description="Whether recipient can download")
    can_comment: bool = Field(default=False, description="Whether recipient can comment")
    expires_in_days: Optional[int] = Field(None, description="Number of days until expiration")

    @validator('shared_with_user_id', 'shared_with_email')
    def validate_share_target(cls, v, values):
        """Validate that either user_id or email is provided."""
        if not v and not values.get('shared_with_email') and not values.get('shared_with_user_id'):
            raise ValueError("Either shared_with_user_id or shared_with_email must be provided")
        return v

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ProposalShareResponse(BaseModel):
    """Response model for proposal shares."""
    id: int = Field(..., description="Share ID")
    proposal_id: int = Field(..., description="Proposal ID")
    shared_with_user_id: Optional[int] = Field(None, description="Shared with user ID")
    shared_with_email: Optional[str] = Field(None, description="Shared with email")
    permission_level: str = Field(..., description="Permission level")
    can_download: bool = Field(..., description="Can download flag")
    can_comment: bool = Field(..., description="Can comment flag")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    is_active: bool = Field(..., description="Active status")
    access_count: int = Field(..., description="Number of times accessed")
    created_at: datetime = Field(..., description="Creation timestamp")
    share_url: str = Field(..., description="Share URL")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        orm_mode = True


class ProposalExportResponse(BaseModel):
    """Response model for proposal exports."""
    id: int = Field(..., description="Export ID")
    proposal_id: int = Field(..., description="Proposal ID")
    format: str = Field(..., description="Export format")
    file_path: str = Field(..., description="File path")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    version_exported: Optional[int] = Field(None, description="Version number exported")
    download_count: int = Field(..., description="Number of downloads")
    last_downloaded_at: Optional[datetime] = Field(None, description="Last download timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    download_url: str = Field(..., description="Download URL")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        orm_mode = True


class ProposalAuditLogResponse(BaseModel):
    """Response model for proposal audit logs."""
    id: int = Field(..., description="Audit log ID")
    proposal_id: int = Field(..., description="Proposal ID")
    action: str = Field(..., description="Action performed")
    description: str = Field(..., description="Action description")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional action details")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    old_values: Optional[Dict[str, Any]] = Field(None, description="Previous values")
    new_values: Optional[Dict[str, Any]] = Field(None, description="New values")
    performed_by: int = Field(..., description="User who performed the action")
    created_at: datetime = Field(..., description="Action timestamp")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        orm_mode = True


class ProposalAnalyticsResponse(BaseModel):
    """Response model for proposal analytics."""
    proposal_id: int = Field(..., description="Proposal ID")
    created_at: str = Field(..., description="Creation timestamp")
    last_updated: str = Field(..., description="Last update timestamp")
    status: str = Field(..., description="Current status")
    phase: str = Field(..., description="Current phase")
    sharing: Dict[str, Any] = Field(..., description="Sharing analytics")
    exports: Dict[str, Any] = Field(..., description="Export analytics")
    versions: Dict[str, Any] = Field(..., description="Version analytics")
    activity: Dict[str, Any] = Field(..., description="Activity analytics")

    class Config:
        """Pydantic configuration."""
        orm_mode = True


class ProposalExportRequest(BaseModel):
    """Request model for proposal exports."""
    format: ExportFormat = Field(..., description="Export format")
    include_metadata: bool = Field(default=True, description="Include metadata in export")
    version_number: Optional[int] = Field(None, description="Specific version to export")
    export_settings: Optional[Dict[str, Any]] = Field(None, description="Export-specific settings")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ProposalSearchRequest(BaseModel):
    """Request model for proposal search."""
    query: Optional[str] = Field(None, description="Search query")
    phase: Optional[ProjectPhase] = Field(None, description="Filter by phase")
    status: Optional[ProposalStatus] = Field(None, description="Filter by status")
    client_name: Optional[str] = Field(None, description="Filter by client name")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(default=50, description="Maximum results")
    offset: int = Field(default=0, description="Results offset")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProposalSearchResponse(BaseModel):
    """Response model for proposal search results."""
    proposals: List[ProposalResponse] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total number of matching proposals")
    has_more: bool = Field(..., description="Whether there are more results")
    search_metadata: Dict[str, Any] = Field(..., description="Search metadata")

    class Config:
        """Pydantic configuration."""
        orm_mode = True


class ProposalBulkActionRequest(BaseModel):
    """Request model for bulk proposal actions."""
    proposal_ids: List[int] = Field(..., description="List of proposal IDs")
    action: str = Field(..., description="Action to perform")
    action_data: Optional[Dict[str, Any]] = Field(None, description="Action-specific data")

    @validator('proposal_ids')
    def validate_proposal_ids(cls, v):
        """Validate proposal IDs list."""
        if not v or len(v) == 0:
            raise ValueError("At least one proposal ID must be provided")
        if len(v) > 100:
            raise ValueError("Cannot perform bulk actions on more than 100 proposals at once")
        return v

    @validator('action')
    def validate_action(cls, v):
        """Validate action type."""
        valid_actions = ['delete', 'update_status', 'export', 'share', 'archive']
        if v not in valid_actions:
            raise ValueError(f"Action must be one of: {valid_actions}")
        return v


class ProposalBulkActionResponse(BaseModel):
    """Response model for bulk proposal actions."""
    successful_ids: List[int] = Field(..., description="Successfully processed proposal IDs")
    failed_ids: List[int] = Field(..., description="Failed proposal IDs")
    errors: Dict[int, str] = Field(..., description="Error messages for failed IDs")
    total_processed: int = Field(..., description="Total number of proposals processed")
    success_count: int = Field(..., description="Number of successful operations")
    failure_count: int = Field(..., description="Number of failed operations")

    class Config:
        """Pydantic configuration."""
        orm_mode = True 