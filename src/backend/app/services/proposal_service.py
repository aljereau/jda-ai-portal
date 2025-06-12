"""
Proposal Service Layer.
Handles business logic and database operations for proposal management.
"""

import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
from datetime import datetime, timedelta
import os

from app.models.proposal import Proposal, ProposalVersion, ProjectTracker, ProposalTemplate
from app.models.proposal import ProjectPhaseEnum, ProposalStatusEnum
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
        extracted_requirements: Dict[str, Any]
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
            
        Returns:
            Created proposal object
        """
        try:
            # Convert phase string to enum
            phase_enum = ProjectPhaseEnum(phase)
            
            # Create proposal
            proposal = Proposal(
                project_name=project_name,
                client_name=client_name,
                phase=phase_enum,
                transcript_path=transcript_path,
                created_by=created_by,
                ai_summary=ai_summary,
                extracted_requirements=json.dumps(extracted_requirements),
                status=ProposalStatusEnum.DRAFT
            )
            
            self.db.add(proposal)
            self.db.commit()
            self.db.refresh(proposal)
            
            # Create initial version
            self._create_initial_version(proposal.id, created_by)
            
            # Create project tracker
            self._create_project_tracker(proposal.id, project_name, client_name, phase_enum, created_by)
            
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

    def create_proposal_share(
        self,
        proposal_id: int,
        share_type: str,
        created_by: int,
        expiry_days: Optional[int] = None,
        password_protected: bool = False
    ) -> str:
        """
        Create a shareable link for proposal access.
        
        Args:
            proposal_id: Proposal ID
            share_type: Type of sharing
            created_by: User who created the share
            expiry_days: Days until expiry
            password_protected: Whether password protection is enabled
            
        Returns:
            Share token
        """
        try:
            import uuid
            import hashlib
            
            # Generate unique share token
            share_token = str(uuid.uuid4())
            
            # Store share record in metadata (in production, use dedicated table)
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                raise ProposalServiceError(f"Proposal {proposal_id} not found")
            
            current_metadata = {}
            if hasattr(proposal, 'metadata') and proposal.metadata:
                current_metadata = json.loads(proposal.metadata)
            
            if 'shares' not in current_metadata:
                current_metadata['shares'] = []
            
            share_record = {
                "token": share_token,
                "share_type": share_type,
                "created_by": created_by,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=expiry_days)).isoformat() if expiry_days else None,
                "password_protected": password_protected,
                "access_count": 0
            }
            
            current_metadata['shares'].append(share_record)
            proposal.metadata = json.dumps(current_metadata)
            
            self.db.commit()
            
            logger.info(f"Created share for proposal {proposal_id}: {share_token}")
            return share_token
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating proposal share: {str(e)}")
            raise ProposalServiceError(f"Failed to create share: {str(e)}")

    def export_proposal(
        self,
        proposal_id: int,
        format: str,
        include_metadata: bool = True
    ) -> str:
        """
        Export proposal in specified format.
        
        Args:
            proposal_id: Proposal ID
            format: Export format (html, pdf, docx, markdown)
            include_metadata: Whether to include metadata
            
        Returns:
            Export content or file path
        """
        try:
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                raise ProposalServiceError(f"Proposal {proposal_id} not found")
            
            # Log export activity
            self._log_export_activity(proposal_id, format)
            
            if format == "html":
                return self._export_to_html(proposal, include_metadata)
            elif format == "markdown":
                return self._export_to_markdown(proposal, include_metadata)
            elif format == "pdf":
                return self._export_to_pdf(proposal, include_metadata)
            elif format == "docx":
                return self._export_to_docx(proposal, include_metadata)
            else:
                raise ProposalServiceError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting proposal: {str(e)}")
            raise ProposalServiceError(f"Failed to export proposal: {str(e)}")

    def get_proposal_complete_history(self, proposal_id: int) -> Dict[str, Any]:
        """
        Get complete proposal history including versions, shares, and modifications.
        
        Args:
            proposal_id: Proposal ID
            
        Returns:
            Complete history data
        """
        try:
            proposal = self.get_proposal(proposal_id)
            if not proposal:
                raise ProposalServiceError(f"Proposal {proposal_id} not found")
            
            # Get versions
            versions = self.get_proposal_versions(proposal_id)
            
            # Get metadata for shares and other history
            metadata = {}
            if hasattr(proposal, 'metadata') and proposal.metadata:
                metadata = json.loads(proposal.metadata)
            
            history = {
                "versions": [
                    {
                        "version_number": v.version_number,
                        "created_at": v.created_at.isoformat(),
                        "created_by": v.created_by,
                        "change_summary": v.change_summary,
                        "is_current": v.is_current
                    } for v in versions
                ],
                "shares": metadata.get('shares', []),
                "modifications": metadata.get('modifications', []),
                "validations": metadata.get('validation_history', []),
                "exports": metadata.get('export_history', [])
            }
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting proposal history: {str(e)}")
            raise ProposalServiceError(f"Failed to get history: {str(e)}")

    def duplicate_proposal(
        self,
        original_proposal_id: int,
        new_project_name: str,
        new_client_name: str,
        created_by: int
    ) -> Proposal:
        """
        Create a duplicate of an existing proposal.
        
        Args:
            original_proposal_id: ID of proposal to duplicate
            new_project_name: Name for new project
            new_client_name: Client name for new proposal
            created_by: User creating the duplicate
            
        Returns:
            New proposal object
        """
        try:
            original = self.get_proposal(original_proposal_id)
            if not original:
                raise ProposalServiceError(f"Original proposal {original_proposal_id} not found")
            
            # Create new proposal with copied content
            new_proposal = Proposal(
                project_name=new_project_name,
                client_name=new_client_name,
                phase=original.phase,
                content=original.content,
                ai_summary=f"Duplicated from {original.project_name}: {original.ai_summary}" if original.ai_summary else None,
                extracted_requirements=original.extracted_requirements,
                status=ProposalStatusEnum.DRAFT,
                created_by=created_by
            )
            
            self.db.add(new_proposal)
            self.db.commit()
            self.db.refresh(new_proposal)
            
            # Create initial version for new proposal
            self._create_initial_version(new_proposal.id, created_by)
            
            # Create project tracker for new proposal
            self._create_project_tracker(
                new_proposal.id, 
                new_project_name, 
                new_client_name, 
                original.phase, 
                created_by
            )
            
            # Log duplication activity
            self._log_duplication_activity(original_proposal_id, new_proposal.id, created_by)
            
            logger.info(f"Duplicated proposal {original_proposal_id} to {new_proposal.id}")
            return new_proposal
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error duplicating proposal: {str(e)}")
            raise ProposalServiceError(f"Failed to duplicate proposal: {str(e)}")

    def _export_to_html(self, proposal: Proposal, include_metadata: bool) -> str:
        """Export proposal to HTML format."""
        content = proposal.content or f"<h1>{proposal.project_name}</h1><p>No content available.</p>"
        
        if include_metadata:
            metadata_html = f"""
            <div class="proposal-metadata">
                <h2>Proposal Metadata</h2>
                <p><strong>Project:</strong> {proposal.project_name}</p>
                <p><strong>Client:</strong> {proposal.client_name}</p>
                <p><strong>Phase:</strong> {proposal.phase.value}</p>
                <p><strong>Status:</strong> {proposal.status.value}</p>
                <p><strong>Created:</strong> {proposal.created_at}</p>
                <p><strong>Last Updated:</strong> {proposal.updated_at}</p>
            </div>
            """
            content = metadata_html + content
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{proposal.project_name} - {proposal.client_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .proposal-metadata {{ background: #f5f5f5; padding: 15px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            {content}
        </body>
        </html>
        """

    def _export_to_markdown(self, proposal: Proposal, include_metadata: bool) -> str:
        """Export proposal to Markdown format."""
        import html2text
        
        content = proposal.content or f"# {proposal.project_name}\n\nNo content available."
        
        # Convert HTML to Markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        markdown_content = h.handle(content)
        
        if include_metadata:
            metadata_md = f"""
# {proposal.project_name} - {proposal.client_name}

**Project:** {proposal.project_name}  
**Client:** {proposal.client_name}  
**Phase:** {proposal.phase.value}  
**Status:** {proposal.status.value}  
**Created:** {proposal.created_at}  
**Last Updated:** {proposal.updated_at}  

---

"""
            markdown_content = metadata_md + markdown_content
        
        return markdown_content

    def _export_to_pdf(self, proposal: Proposal, include_metadata: bool) -> str:
        """Export proposal to PDF format. Returns file path."""
        # This would require libraries like weasyprint or reportlab
        # For now, return a placeholder path
        export_dir = "exports/pdf"
        os.makedirs(export_dir, exist_ok=True)
        
        filename = f"{proposal.project_name}_{proposal.client_name}_proposal.pdf"
        file_path = os.path.join(export_dir, filename)
        
        # In production, generate actual PDF here
        # For now, create a placeholder file
        with open(file_path, 'w') as f:
            f.write(f"PDF export for {proposal.project_name} - {proposal.client_name}")
        
        return file_path

    def _export_to_docx(self, proposal: Proposal, include_metadata: bool) -> str:
        """Export proposal to DOCX format. Returns file path."""
        # This would require python-docx library
        export_dir = "exports/docx"
        os.makedirs(export_dir, exist_ok=True)
        
        filename = f"{proposal.project_name}_{proposal.client_name}_proposal.docx"
        file_path = os.path.join(export_dir, filename)
        
        # In production, generate actual DOCX here
        # For now, create a placeholder file
        with open(file_path, 'w') as f:
            f.write(f"DOCX export for {proposal.project_name} - {proposal.client_name}")
        
        return file_path

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