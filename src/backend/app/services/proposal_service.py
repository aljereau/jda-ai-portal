"""
Proposal Service Layer.
Handles business logic and database operations for proposal management.
"""

import json
import uuid
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
from datetime import datetime, timedelta
import os

from app.models.proposal import (
    Proposal, ProposalVersion, ProjectTracker, ProposalTemplate,
    ProposalShare, ProposalExport, ProposalAuditLog
)
from app.models.proposal import (
    ProjectPhaseEnum, ProposalStatusEnum, SharePermissionEnum,
    ExportFormatEnum, AuditActionEnum
)
from app.schemas.proposal import ProposalCreate, ProposalUpdate

# Configure logging
logger = logging.getLogger(__name__)


class ProposalServiceError(Exception):
    """Custom exception for proposal service errors."""
    pass


class ProposalService:
    """
    Service layer for proposal management.
    Handles CRUD operations and business logic.
    """

    def __init__(self, db: Session):
        """
        Initialize proposal service.
        
        Args:
            db: Database session
        """
        self.db = db

    def create_proposal(
        self,
        project_name: str,
        client_name: str,
        phase: str,
        transcript_path: str,
        created_by: int,
        ai_summary: str,
        extracted_requirements: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Proposal:
        """
        Create a new proposal.
        
        Args:
            project_name: Name of the project
            client_name: Client company name
            phase: Project phase
            transcript_path: Path to uploaded transcript
            created_by: User ID who created the proposal
            ai_summary: AI-generated summary
            extracted_requirements: Extracted requirements dictionary
            ip_address: Client IP address for audit
            user_agent: Client user agent for audit
            
        Returns:
            Created proposal object
        """
        try:
            # Convert phase string to enum
            phase_enum = ProjectPhaseEnum(phase)
            
            # Generate unique share token
            share_token = self._generate_share_token()
            
            # Create proposal
            proposal = Proposal(
                project_name=project_name,
                client_name=client_name,
                phase=phase_enum,
                transcript_path=transcript_path,
                created_by=created_by,
                ai_summary=ai_summary,
                extracted_requirements=json.dumps(extracted_requirements),
                status=ProposalStatusEnum.DRAFT,
                share_token=share_token
            )
            
            self.db.add(proposal)
            self.db.commit()
            self.db.refresh(proposal)
            
            # Create initial version
            self._create_initial_version(proposal.id, created_by)
            
            # Create project tracker
            self._create_project_tracker(proposal.id, project_name, client_name, phase_enum, created_by)
            
            # Log audit trail
            self._log_audit_action(
                proposal.id, AuditActionEnum.CREATED, created_by,
                f"Proposal created for project: {project_name}",
                {"project_name": project_name, "client_name": client_name, "phase": phase},
                ip_address, user_agent
            )
            
            logger.info(f"Created proposal {proposal.id} for project: {project_name}")
            return proposal
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating proposal: {str(e)}")
            raise ProposalServiceError(f"Failed to create proposal: {str(e)}")

    def get_proposal(self, proposal_id: int) -> Optional[Proposal]:
        """
        Get proposal by ID.
        
        Args:
            proposal_id: Proposal ID
            
        Returns:
            Proposal object or None if not found
        """
        try:
            return self.db.query(Proposal).filter(Proposal.id == proposal_id).first()
        except Exception as e:
            logger.error(f"Error retrieving proposal {proposal_id}: {str(e)}")
            raise ProposalServiceError(f"Failed to retrieve proposal: {str(e)}")

    def list_proposals(
        self,
        skip: int = 0,
        limit: int = 100,
        phase: Optional[str] = None,
        status: Optional[str] = None,
        user_role: str = "admin"
    ) -> List[Proposal]:
        """
        List proposals with optional filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            phase: Filter by project phase
            status: Filter by proposal status
            user_role: User role for access control
            
        Returns:
            List of proposals
        """
        try:
            query = self.db.query(Proposal)
            
            # Apply filters
            if phase:
                phase_enum = ProjectPhaseEnum(phase)
                query = query.filter(Proposal.phase == phase_enum)
            
            if status:
                status_enum = ProposalStatusEnum(status)
                query = query.filter(Proposal.status == status_enum)
            
            # Apply access control
            if user_role == "client":
                # Clients can only see approved/sent proposals
                query = query.filter(
                    Proposal.status.in_([
                        ProposalStatusEnum.APPROVED,
                        ProposalStatusEnum.SENT,
                        ProposalStatusEnum.ACCEPTED
                    ])
                )
            
            return query.offset(skip).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error listing proposals: {str(e)}")
            raise ProposalServiceError(f"Failed to list proposals: {str(e)}")

    def update_proposal_content(
        self,
        proposal_id: int,
        content: str,
        status: str = "draft"
    ) -> Proposal:
        """
        Update proposal content and create new version.
        
        Args:
            proposal_id: Proposal ID
            content: New proposal content
            status: Proposal status
            
        Returns:
            Updated proposal object
        """
        try:
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                raise ProposalServiceError(f"Proposal {proposal_id} not found")
            
            # Update proposal
            proposal.content = content
            proposal.status = ProposalStatusEnum(status)
            
            self.db.commit()
            self.db.refresh(proposal)
            
            # Create new version
            self._create_version(proposal_id, content, proposal.created_by, "Content updated")
            
            logger.info(f"Updated content for proposal {proposal_id}")
            return proposal
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating proposal content: {str(e)}")
            raise ProposalServiceError(f"Failed to update proposal content: {str(e)}")

    def update_proposal(
        self,
        proposal_id: int,
        update_data: Dict[str, Any]
    ) -> Optional[Proposal]:
        """
        Update proposal with provided data.
        
        Args:
            proposal_id: Proposal ID
            update_data: Dictionary of fields to update
            
        Returns:
            Updated proposal object or None if not found
        """
        try:
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                return None
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(proposal, field):
                    if field == "phase" and isinstance(value, str):
                        value = ProjectPhaseEnum(value)
                    elif field == "status" and isinstance(value, str):
                        value = ProposalStatusEnum(value)
                    elif field == "extracted_requirements" and isinstance(value, dict):
                        value = json.dumps(value)
                    
                    setattr(proposal, field, value)
            
            self.db.commit()
            self.db.refresh(proposal)
            
            logger.info(f"Updated proposal {proposal_id}")
            return proposal
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating proposal: {str(e)}")
            raise ProposalServiceError(f"Failed to update proposal: {str(e)}")

    def delete_proposal(self, proposal_id: int) -> bool:
        """
        Delete proposal and related records.
        
        Args:
            proposal_id: Proposal ID
            
        Returns:
            True if successful, False if not found
        """
        try:
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                return False
            
            # Delete related records (cascading should handle this)
            self.db.delete(proposal)
            self.db.commit()
            
            logger.info(f"Deleted proposal {proposal_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting proposal: {str(e)}")
            raise ProposalServiceError(f"Failed to delete proposal: {str(e)}")

    def get_proposal_versions(self, proposal_id: int) -> List[ProposalVersion]:
        """
        Get all versions of a proposal.
        
        Args:
            proposal_id: Proposal ID
            
        Returns:
            List of proposal versions
        """
        try:
            return (
                self.db.query(ProposalVersion)
                .filter(ProposalVersion.proposal_id == proposal_id)
                .order_by(ProposalVersion.version_number.desc())
                .all()
            )
        except Exception as e:
            logger.error(f"Error retrieving proposal versions: {str(e)}")
            raise ProposalServiceError(f"Failed to retrieve proposal versions: {str(e)}")

    def get_project_tracker(self, proposal_id: int) -> Optional[ProjectTracker]:
        """
        Get project tracker for a proposal.
        
        Args:
            proposal_id: Proposal ID
            
        Returns:
            Project tracker object or None if not found
        """
        try:
            return (
                self.db.query(ProjectTracker)
                .filter(ProjectTracker.proposal_id == proposal_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error retrieving project tracker: {str(e)}")
            raise ProposalServiceError(f"Failed to retrieve project tracker: {str(e)}")

    def update_project_phase(
        self,
        proposal_id: int,
        new_phase: str,
        mark_completed: bool = True
    ) -> bool:
        """
        Update project phase and mark previous phases as completed.
        
        Args:
            proposal_id: Proposal ID
            new_phase: New project phase
            mark_completed: Whether to mark the previous phase as completed
            
        Returns:
            True if successful
        """
        try:
            # Update proposal phase
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                return False
            
            old_phase = proposal.phase
            proposal.phase = ProjectPhaseEnum(new_phase)
            
            # Update project tracker
            tracker = self.get_project_tracker(proposal_id)
            if tracker:
                tracker.current_phase = ProjectPhaseEnum(new_phase)
                
                # Mark previous phase as completed
                if mark_completed:
                    if old_phase == ProjectPhaseEnum.EXPLORATORY:
                        tracker.exploratory_completed = True
                    elif old_phase == ProjectPhaseEnum.DISCOVERY:
                        tracker.discovery_completed = True
                    elif old_phase == ProjectPhaseEnum.DEVELOPMENT:
                        tracker.development_completed = True
            
            self.db.commit()
            logger.info(f"Updated project phase for proposal {proposal_id} from {old_phase} to {new_phase}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating project phase: {str(e)}")
            raise ProposalServiceError(f"Failed to update project phase: {str(e)}")

    def _create_initial_version(self, proposal_id: int, created_by: int):
        """Create initial version for a new proposal."""
        version = ProposalVersion(
            proposal_id=proposal_id,
            version_number=1,
            content="Initial proposal draft",
            change_summary="Initial version",
            created_by=created_by,
            is_current=True
        )
        self.db.add(version)

    def _create_version(
        self,
        proposal_id: int,
        content: str,
        created_by: int,
        change_summary: str
    ):
        """Create a new version of a proposal."""
        # Mark all existing versions as not current
        self.db.query(ProposalVersion).filter(
            ProposalVersion.proposal_id == proposal_id
        ).update({"is_current": False})
        
        # Get next version number
        last_version = (
            self.db.query(ProposalVersion)
            .filter(ProposalVersion.proposal_id == proposal_id)
            .order_by(ProposalVersion.version_number.desc())
            .first()
        )
        
        next_version = (last_version.version_number + 1) if last_version else 1
        
        # Create new version
        version = ProposalVersion(
            proposal_id=proposal_id,
            version_number=next_version,
            content=content,
            change_summary=change_summary,
            created_by=created_by,
            is_current=True
        )
        self.db.add(version)

    def _create_project_tracker(
        self,
        proposal_id: int,
        project_name: str,
        client_name: str,
        phase: ProjectPhaseEnum,
        created_by: int
    ):
        """Create project tracker for a new proposal."""
        tracker = ProjectTracker(
            proposal_id=proposal_id,
            project_name=project_name,
            client_name=client_name,
            current_phase=phase,
            created_by=created_by
        )
        self.db.add(tracker)
        self.db.commit()
        
        logger.info(f"Created project tracker for proposal {proposal_id}")
        
    def add_block_to_content(
        self,
        proposal_id: int,
        block_type: str,
        block_content: str,
        position: Optional[int] = None
    ) -> str:
        """
        Add a new block to proposal content.
        
        Args:
            proposal_id: Proposal ID
            block_type: Type of block to add
            block_content: Content of the block
            position: Position to insert block (None = append)
            
        Returns:
            Updated proposal content
        """
        try:
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                raise ProposalServiceError(f"Proposal {proposal_id} not found")
            
            current_content = proposal.content or ""
            
            # Create block wrapper
            block_html = f"""
            <section class="proposal-block" id="block_{block_type}_{proposal_id}">
                <div class="block-content" data-block-type="{block_type}">
                    {block_content}
                </div>
            </section>
            """
            
            # Insert block at specified position or append
            if position is not None and current_content:
                # Split content into sections and insert at position
                sections = self._parse_content_sections(current_content)
                if position <= len(sections):
                    sections.insert(position, block_html)
                else:
                    sections.append(block_html)
                updated_content = "\n".join(sections)
            else:
                # Append to end
                updated_content = current_content + "\n" + block_html
            
            # Update proposal content
            proposal.content = updated_content
            self.db.commit()
            
            # Create version
            self._create_version(
                proposal_id,
                updated_content,
                proposal.created_by,
                f"Added {block_type} block"
            )
            
            logger.info(f"Added {block_type} block to proposal {proposal_id}")
            return updated_content
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding block to proposal: {str(e)}")
            raise ProposalServiceError(f"Failed to add block: {str(e)}")

    def remove_block_from_content(
        self,
        proposal_id: int,
        block_id: str
    ) -> str:
        """
        Remove a block from proposal content.
        
        Args:
            proposal_id: Proposal ID
            block_id: ID of block to remove
            
        Returns:
            Updated proposal content
        """
        try:
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                raise ProposalServiceError(f"Proposal {proposal_id} not found")
            
            current_content = proposal.content or ""
            
            # Remove block with matching ID
            import re
            pattern = rf'<section[^>]*id="{re.escape(block_id)}"[^>]*>.*?</section>'
            updated_content = re.sub(pattern, '', current_content, flags=re.DOTALL)
            
            # Clean up extra whitespace
            updated_content = re.sub(r'\n\s*\n', '\n\n', updated_content)
            
            # Update proposal content
            proposal.content = updated_content
            self.db.commit()
            
            # Create version
            self._create_version(
                proposal_id,
                updated_content,
                proposal.created_by,
                f"Removed block {block_id}"
            )
            
            logger.info(f"Removed block {block_id} from proposal {proposal_id}")
            return updated_content
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing block from proposal: {str(e)}")
            raise ProposalServiceError(f"Failed to remove block: {str(e)}")

    def update_proposal_validation(
        self,
        proposal_id: int,
        validation_status: str,
        validation_issues: List[Dict[str, Any]],
        validation_score: float
    ) -> bool:
        """
        Update proposal validation results.
        
        Args:
            proposal_id: Proposal ID
            validation_status: Validation status
            validation_issues: List of validation issues
            validation_score: Validation score (0-100)
            
        Returns:
            Success status
        """
        try:
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                raise ProposalServiceError(f"Proposal {proposal_id} not found")
            
            # Store validation data in metadata
            validation_data = {
                "status": validation_status,
                "score": validation_score,
                "issues": validation_issues,
                "validated_at": json.dumps(datetime.utcnow().isoformat())
            }
            
            # Update proposal metadata
            current_metadata = {}
            if hasattr(proposal, 'metadata') and proposal.metadata:
                current_metadata = json.loads(proposal.metadata)
            
            current_metadata['validation'] = validation_data
            proposal.metadata = json.dumps(current_metadata)
            
            self.db.commit()
            
            logger.info(f"Updated validation for proposal {proposal_id}: {validation_status}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating proposal validation: {str(e)}")
            raise ProposalServiceError(f"Failed to update validation: {str(e)}")

    def get_proposal_validation(self, proposal_id: int) -> Optional[Dict[str, Any]]:
        """
        Get proposal validation results.
        
        Args:
            proposal_id: Proposal ID
            
        Returns:
            Validation data or None
        """
        try:
            proposal = self.get_proposal(proposal_id)
            if not proposal or not hasattr(proposal, 'metadata') or not proposal.metadata:
                return None
            
            metadata = json.loads(proposal.metadata)
            return metadata.get('validation')
            
        except Exception as e:
            logger.error(f"Error getting proposal validation: {str(e)}")
            return None

    def _parse_content_sections(self, content: str) -> List[str]:
        """
        Parse content into sections for block manipulation.
        
        Args:
            content: HTML content to parse
            
        Returns:
            List of content sections
        """
        try:
            import re
            
            # Split by section tags
            sections = re.split(r'(<section[^>]*>.*?</section>)', content, flags=re.DOTALL)
            
            # Filter out empty sections and whitespace-only sections
            sections = [section.strip() for section in sections if section.strip()]
            
            return sections
            
        except Exception:
            # Fallback to simple line splitting
            return [line for line in content.split('\n') if line.strip()]

    def _log_audit_action(
        self,
        proposal_id: int,
        action: AuditActionEnum,
        performed_by: int,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None
    ):
        """
        Log an audit action for a proposal.
        
        Args:
            proposal_id: Proposal ID
            action: Audit action type
            performed_by: User ID who performed the action
            description: Action description
            details: Additional action details
            ip_address: Client IP address
            user_agent: Client user agent
            old_values: Previous values (for updates)
            new_values: New values (for updates)
        """
        try:
            audit_log = ProposalAuditLog(
                proposal_id=proposal_id,
                action=action,
                description=description,
                details=json.dumps(details) if details else None,
                ip_address=ip_address,
                user_agent=user_agent,
                old_values=json.dumps(old_values) if old_values else None,
                new_values=json.dumps(new_values) if new_values else None,
                performed_by=performed_by
            )
            self.db.add(audit_log)
            self.db.commit()
            
            logger.info(f"Logged audit action for proposal {proposal_id}: {action}")
            
        except Exception as e:
            logger.error(f"Error logging audit action: {str(e)}")

    def create_proposal_share(
        self,
        proposal_id: int,
        shared_by: int,
        shared_with_user_id: Optional[int] = None,
        shared_with_email: Optional[str] = None,
        permission_level: str = "view_only",
        can_download: bool = False,
        can_comment: bool = False,
        expires_in_days: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ProposalShare:
        """
        Create a new proposal share.
        
        Args:
            proposal_id: Proposal ID to share
            shared_by: User ID who is sharing
            shared_with_user_id: User ID to share with (for internal users)
            shared_with_email: Email to share with (for external users)
            permission_level: Permission level (view_only, comment, edit, full_access)
            can_download: Whether recipient can download
            can_comment: Whether recipient can comment
            expires_in_days: Number of days until expiration
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created ProposalShare object
        """
        try:
            # Calculate expiration date
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            # Create share
            share = ProposalShare(
                proposal_id=proposal_id,
                shared_with_user_id=shared_with_user_id,
                shared_with_email=shared_with_email,
                permission_level=SharePermissionEnum(permission_level),
                can_download=can_download,
                can_comment=can_comment,
                expires_at=expires_at,
                shared_by=shared_by
            )
            
            self.db.add(share)
            self.db.commit()
            self.db.refresh(share)
            
            # Log audit trail
            share_details = {
                "shared_with_user_id": shared_with_user_id,
                "shared_with_email": shared_with_email,
                "permission_level": permission_level,
                "expires_at": expires_at.isoformat() if expires_at else None
            }
            
            self._log_audit_action(
                proposal_id, AuditActionEnum.SHARED, shared_by,
                f"Proposal shared with {'user' if shared_with_user_id else 'email'}: {shared_with_user_id or shared_with_email}",
                share_details, ip_address, user_agent
            )
            
            logger.info(f"Created share {share.id} for proposal {proposal_id}")
            return share
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating proposal share: {str(e)}")
            raise ProposalServiceError(f"Failed to create proposal share: {str(e)}")

    def get_proposal_shares(self, proposal_id: int) -> List[ProposalShare]:
        """
        Get all shares for a proposal.
        
        Args:
            proposal_id: Proposal ID
            
        Returns:
            List of ProposalShare objects
        """
        try:
            return self.db.query(ProposalShare).filter(
                ProposalShare.proposal_id == proposal_id,
                ProposalShare.is_active == True
            ).all()
        except Exception as e:
            logger.error(f"Error retrieving proposal shares: {str(e)}")
            raise ProposalServiceError(f"Failed to retrieve proposal shares: {str(e)}")

    def revoke_proposal_share(
        self,
        share_id: int,
        revoked_by: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Revoke a proposal share.
        
        Args:
            share_id: Share ID to revoke
            revoked_by: User ID who is revoking
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            True if successful
        """
        try:
            share = self.db.query(ProposalShare).filter(ProposalShare.id == share_id).first()
            if not share:
                raise ProposalServiceError(f"Share {share_id} not found")
            
            share.is_active = False
            self.db.commit()
            
            # Log audit trail
            self._log_audit_action(
                share.proposal_id, AuditActionEnum.ACCESS_REVOKED, revoked_by,
                f"Share access revoked for share ID: {share_id}",
                {"share_id": share_id, "shared_with": share.shared_with_email or share.shared_with_user_id},
                ip_address, user_agent
            )
            
            logger.info(f"Revoked share {share_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error revoking proposal share: {str(e)}")
            raise ProposalServiceError(f"Failed to revoke proposal share: {str(e)}")

    def track_proposal_export(
        self,
        proposal_id: int,
        format: str,
        file_path: str,
        exported_by: int,
        export_settings: Optional[Dict[str, Any]] = None,
        version_exported: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ProposalExport:
        """
        Track a proposal export.
        
        Args:
            proposal_id: Proposal ID
            format: Export format (html, pdf, docx, markdown)
            file_path: Path to exported file
            exported_by: User ID who exported
            export_settings: Export settings used
            version_exported: Version number exported
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created ProposalExport object
        """
        try:
            # Get file size
            file_size_bytes = None
            if os.path.exists(file_path):
                file_size_bytes = os.path.getsize(file_path)
            
            # Create export record
            export_record = ProposalExport(
                proposal_id=proposal_id,
                format=ExportFormatEnum(format),
                file_path=file_path,
                file_size_bytes=file_size_bytes,
                export_settings=json.dumps(export_settings) if export_settings else None,
                version_exported=version_exported,
                exported_by=exported_by
            )
            
            self.db.add(export_record)
            
            # Update proposal export tracking
            proposal = self.get_proposal(proposal_id)
            if proposal:
                proposal.last_exported_at = datetime.utcnow()
                proposal.export_count = (proposal.export_count or 0) + 1
            
            self.db.commit()
            self.db.refresh(export_record)
            
            # Log audit trail
            export_details = {
                "format": format,
                "file_size_bytes": file_size_bytes,
                "version_exported": version_exported,
                "export_settings": export_settings
            }
            
            self._log_audit_action(
                proposal_id, AuditActionEnum.EXPORTED, exported_by,
                f"Proposal exported to {format.upper()} format",
                export_details, ip_address, user_agent
            )
            
            logger.info(f"Tracked export {export_record.id} for proposal {proposal_id}")
            return export_record
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error tracking proposal export: {str(e)}")
            raise ProposalServiceError(f"Failed to track proposal export: {str(e)}")

    def get_proposal_exports(self, proposal_id: int) -> List[ProposalExport]:
        """
        Get all exports for a proposal.
        
        Args:
            proposal_id: Proposal ID
            
        Returns:
            List of ProposalExport objects
        """
        try:
            return self.db.query(ProposalExport).filter(
                ProposalExport.proposal_id == proposal_id
            ).order_by(ProposalExport.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error retrieving proposal exports: {str(e)}")
            raise ProposalServiceError(f"Failed to retrieve proposal exports: {str(e)}")

    def track_export_download(
        self,
        export_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Track a download of an exported proposal.
        
        Args:
            export_id: Export ID
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            True if successful
        """
        try:
            export_record = self.db.query(ProposalExport).filter(ProposalExport.id == export_id).first()
            if not export_record:
                raise ProposalServiceError(f"Export {export_id} not found")
            
            export_record.download_count = (export_record.download_count or 0) + 1
            export_record.last_downloaded_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Tracked download for export {export_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error tracking export download: {str(e)}")
            raise ProposalServiceError(f"Failed to track export download: {str(e)}")

    def get_proposal_audit_log(
        self,
        proposal_id: int,
        limit: int = 100,
        action_filter: Optional[str] = None
    ) -> List[ProposalAuditLog]:
        """
        Get audit log for a proposal.
        
        Args:
            proposal_id: Proposal ID
            limit: Maximum number of records
            action_filter: Filter by action type
            
        Returns:
            List of ProposalAuditLog objects
        """
        try:
            query = self.db.query(ProposalAuditLog).filter(
                ProposalAuditLog.proposal_id == proposal_id
            )
            
            if action_filter:
                query = query.filter(ProposalAuditLog.action == AuditActionEnum(action_filter))
            
            return query.order_by(ProposalAuditLog.created_at.desc()).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error retrieving proposal audit log: {str(e)}")
            raise ProposalServiceError(f"Failed to retrieve proposal audit log: {str(e)}")

    def get_proposal_analytics(self, proposal_id: int) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a proposal.
        
        Args:
            proposal_id: Proposal ID
            
        Returns:
            Analytics dictionary
        """
        try:
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                raise ProposalServiceError(f"Proposal {proposal_id} not found")
            
            # Get shares analytics
            shares = self.get_proposal_shares(proposal_id)
            active_shares = [s for s in shares if s.is_active]
            
            # Get exports analytics
            exports = self.get_proposal_exports(proposal_id)
            total_downloads = sum(e.download_count or 0 for e in exports)
            
            # Get versions analytics
            versions = self.get_proposal_versions(proposal_id)
            
            # Get audit log analytics
            audit_logs = self.get_proposal_audit_log(proposal_id)
            
            return {
                "proposal_id": proposal_id,
                "created_at": proposal.created_at.isoformat(),
                "last_updated": proposal.updated_at.isoformat(),
                "status": proposal.status.value,
                "phase": proposal.phase.value,
                "sharing": {
                    "total_shares": len(shares),
                    "active_shares": len(active_shares),
                    "total_access_count": sum(s.access_count or 0 for s in shares)
                },
                "exports": {
                    "total_exports": len(exports),
                    "total_downloads": total_downloads,
                    "formats_used": list(set(e.format.value for e in exports)),
                    "last_exported": proposal.last_exported_at.isoformat() if proposal.last_exported_at else None
                },
                "versions": {
                    "total_versions": len(versions),
                    "current_version": max(v.version_number for v in versions) if versions else 0
                },
                "activity": {
                    "total_actions": len(audit_logs),
                    "recent_actions": [
                        {
                            "action": log.action.value,
                            "description": log.description,
                            "timestamp": log.created_at.isoformat()
                        }
                        for log in audit_logs[:5]
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Error retrieving proposal analytics: {str(e)}")
            raise ProposalServiceError(f"Failed to retrieve proposal analytics: {str(e)}")

    def _generate_share_token(self) -> str:
        """Generate a unique share token."""
        return str(uuid.uuid4())

    def _log_export_activity(self, proposal_id: int, format: str):
        """Log export activity to proposal metadata."""
        try:
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                return
            
            current_metadata = {}
            if hasattr(proposal, 'metadata') and proposal.metadata:
                current_metadata = json.loads(proposal.metadata)
            
            if 'export_history' not in current_metadata:
                current_metadata['export_history'] = []
            
            export_record = {
                "format": format,
                "exported_at": datetime.utcnow().isoformat(),
                "success": True
            }
            
            current_metadata['export_history'].append(export_record)
            proposal.metadata = json.dumps(current_metadata)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging export activity: {str(e)}")

    def _log_duplication_activity(self, original_id: int, new_id: int, created_by: int):
        """Log duplication activity to original proposal metadata."""
        try:
            proposal = self.get_proposal(original_id)
            if not proposal:
                return
            
            current_metadata = {}
            if hasattr(proposal, 'metadata') and proposal.metadata:
                current_metadata = json.loads(proposal.metadata)
            
            if 'duplications' not in current_metadata:
                current_metadata['duplications'] = []
            
            duplication_record = {
                "new_proposal_id": new_id,
                "created_by": created_by,
                "duplicated_at": datetime.utcnow().isoformat()
            }
            
            current_metadata['duplications'].append(duplication_record)
            proposal.metadata = json.dumps(current_metadata)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging duplication activity: {str(e)}") 