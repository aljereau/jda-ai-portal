"""
Proposal management API endpoints.
Handles transcript upload, AI processing, proposal generation, sharing, exports, and audit trail.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import os
import aiofiles
from datetime import datetime, timedelta
import uuid
import json

from app.core.database import get_db
from app.core.auth import verify_token, get_current_user
from app.models.proposal import (
    Proposal, ProposalVersion, ProjectTracker, ProposalShare,
    ProposalExport, ProposalAuditLog
)
from app.schemas.proposal import (
    ProposalCreate, ProposalResponse, ProposalUpdate,
    TranscriptUploadResponse, ProposalGenerateRequest,
    ProposalBlockRequest, ProposalBlockResponse,
    ProposalValidationResponse, ProposalShareRequest,
    ProposalShareResponse, ProposalExportResponse,
    ProposalAuditLogResponse, ProposalAnalyticsResponse
)
from app.services.ai_service import AIService
from app.services.proposal_service import ProposalService
from app.services.template_service import TemplateService

router = APIRouter()
security = HTTPBearer()


@router.post("/upload-transcript", response_model=TranscriptUploadResponse)
async def upload_transcript(
    file: UploadFile = File(...),
    project_name: str = Form(...),
    client_name: str = Form(...),
    phase: str = Form(default="exploratory"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload meeting transcript for proposal generation.
    
    Args:
        file: Text file containing meeting transcript
        project_name: Name of the project
        client_name: Client company name
        phase: Project phase (exploratory, discovery, development, deployment)
        current_user: Authenticated user
        db: Database session
        
    Returns:
        TranscriptUploadResponse with upload details and AI summary
    """
    # Validate file type
    if not file.filename.endswith(('.txt', '.md')):
        raise HTTPException(
            status_code=400, 
            detail="Only .txt and .md files are supported for transcripts"
        )
    
    # Validate project phase
    valid_phases = ["exploratory", "discovery", "development", "deployment"]
    if phase not in valid_phases:
        raise HTTPException(
            status_code=400,
            detail=f"Phase must be one of: {valid_phases}"
        )
    
    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        upload_dir = "uploads/transcripts"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save uploaded file
        file_path = f"{upload_dir}/{file_id}_{file.filename}"
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Read transcript content for AI processing
        transcript_content = content.decode('utf-8')
        
        # Generate AI summary
        ai_service = AIService()
        summary_result = await ai_service.generate_transcript_summary(
            transcript_content=transcript_content,
            project_name=project_name,
            client_name=client_name,
            phase=phase
        )
        
        # Create initial proposal record
        proposal_service = ProposalService(db)
        proposal = proposal_service.create_proposal(
            project_name=project_name,
            client_name=client_name,
            phase=phase,
            transcript_path=file_path,
            created_by=current_user["user_id"],
            ai_summary=summary_result["summary"],
            extracted_requirements=summary_result["requirements"]
        )
        
        return TranscriptUploadResponse(
            file_id=file_id,
            filename=file.filename,
            project_name=project_name,
            client_name=client_name,
            phase=phase,
            ai_summary=summary_result["summary"],
            extracted_requirements=summary_result["requirements"],
            proposal_id=proposal.id,
            upload_timestamp=datetime.utcnow(),
            status="processed"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process transcript: {str(e)}"
        )


@router.post("/generate", response_model=ProposalResponse)
async def generate_proposal(
    request: ProposalGenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate proposal from uploaded transcript and requirements.
    
    Args:
        request: Proposal generation request with requirements
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Generated proposal data
    """
    try:
        proposal_service = ProposalService(db)
        ai_service = AIService()
        
        # Get existing proposal
        proposal = proposal_service.get_proposal(request.proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Generate proposal content using AI
        ai_content = await ai_service.generate_proposal_content(
            requirements=request.requirements,
            project_name=proposal.project_name,
            client_name=proposal.client_name,
            phase=proposal.phase,
            template_preferences=request.template_preferences
        )
        
        # Render proposal using template engine
        template_service = TemplateService()
        proposal_content = template_service.render_proposal(
            project_name=proposal.project_name,
            client_name=proposal.client_name,
            phase=proposal.phase,
            requirements=request.requirements,
            ai_content=ai_content
        )
        
        # Update proposal with generated content
        updated_proposal = proposal_service.update_proposal_content(
            proposal_id=request.proposal_id,
            content=proposal_content,
            status="draft"
        )
        
        return ProposalResponse(
            id=updated_proposal.id,
            project_name=updated_proposal.project_name,
            client_name=updated_proposal.client_name,
            phase=updated_proposal.phase,
            content=proposal_content,
            status=updated_proposal.status,
            created_at=updated_proposal.created_at,
            updated_at=updated_proposal.updated_at,
            created_by=updated_proposal.created_by
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate proposal: {str(e)}"
        )


@router.get("/", response_model=List[ProposalResponse])
async def list_proposals(
    skip: int = 0,
    limit: int = 100,
    phase: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List proposals with optional filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        phase: Filter by project phase
        status: Filter by proposal status
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of proposals
    """
    proposal_service = ProposalService(db)
    proposals = proposal_service.list_proposals(
        skip=skip,
        limit=limit,
        phase=phase,
        status=status,
        user_role=current_user["role"]
    )
    
    return [
        ProposalResponse(
            id=p.id,
            project_name=p.project_name,
            client_name=p.client_name,
            phase=p.phase,
            content=p.content,
            status=p.status,
            created_at=p.created_at,
            updated_at=p.updated_at,
            created_by=p.created_by
        )
        for p in proposals
    ]


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific proposal by ID.
    
    Args:
        proposal_id: Proposal ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Proposal details
    """
    proposal_service = ProposalService(db)
    proposal = proposal_service.get_proposal(proposal_id)
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Check access permissions
    if current_user["role"] == "client":
        # Clients can only view proposals they're associated with
        if proposal.client_name != current_user.get("company"):
            raise HTTPException(status_code=403, detail="Access denied")
    
    return ProposalResponse(
        id=proposal.id,
        project_name=proposal.project_name,
        client_name=proposal.client_name,
        phase=proposal.phase,
        content=proposal.content,
        status=proposal.status,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
        created_by=proposal.created_by
    )


@router.put("/{proposal_id}", response_model=ProposalResponse)
async def update_proposal(
    proposal_id: int,
    proposal_update: ProposalUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update proposal content and status.
    
    Args:
        proposal_id: Proposal ID
        proposal_update: Updated proposal data
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Updated proposal
    """
    # Only admin and project managers can update proposals
    if current_user["role"] not in ["admin", "project_manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        proposal_service = ProposalService(db)
        updated_proposal = proposal_service.update_proposal(
            proposal_id=proposal_id,
            update_data=proposal_update.dict(exclude_unset=True)
        )
        
        if not updated_proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        return ProposalResponse(
            id=updated_proposal.id,
            project_name=updated_proposal.project_name,
            client_name=updated_proposal.client_name,
            phase=updated_proposal.phase,
            content=updated_proposal.content,
            status=updated_proposal.status,
            created_at=updated_proposal.created_at,
            updated_at=updated_proposal.updated_at,
            created_by=updated_proposal.created_by
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update proposal: {str(e)}"
        )


@router.post("/{proposal_id}/extract-requirements")
async def extract_requirements(
    proposal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Extract and update requirements from proposal transcript.
    
    Args:
        proposal_id: Proposal ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Updated requirements
    """
    try:
        proposal_service = ProposalService(db)
        proposal = proposal_service.get_proposal(proposal_id)
        
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Check permissions
        if current_user["role"] not in ["admin", "project_manager"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Re-extract requirements if transcript exists
        if proposal.transcript_path:
            try:
                with open(proposal.transcript_path, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                
                ai_service = AIService()
                summary_result = await ai_service.generate_transcript_summary(
                    transcript_content=transcript_content,
                    project_name=proposal.project_name,
                    client_name=proposal.client_name,
                    phase=proposal.phase
                )
                
                # Update proposal with new requirements
                updated_proposal = proposal_service.update_proposal(
                    proposal_id=proposal_id,
                    update_data={
                        "ai_summary": summary_result["summary"],
                        "extracted_requirements": summary_result["requirements"]
                    }
                )
                
                return {
                    "message": "Requirements extracted successfully",
                    "requirements": summary_result["requirements"],
                    "summary": summary_result["summary"]
                }
                
            except FileNotFoundError:
                raise HTTPException(
                    status_code=404, 
                    detail="Transcript file not found"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="No transcript available for requirements extraction"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract requirements: {str(e)}"
        )


@router.post("/{proposal_id}/render-template")
async def render_template(
    proposal_id: int,
    template_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Render proposal using template engine.
    
    Args:
        proposal_id: Proposal ID
        template_name: Template to use (optional)
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Rendered proposal HTML
    """
    try:
        proposal_service = ProposalService(db)
        proposal = proposal_service.get_proposal(proposal_id)
        
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Check permissions
        if current_user["role"] == "client":
            # Clients can only view approved proposals
            if proposal.status not in ["approved", "sent", "accepted"]:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Parse requirements
        import json
        requirements = {}
        if proposal.extracted_requirements:
            try:
                requirements = json.loads(proposal.extracted_requirements)
            except json.JSONDecodeError:
                requirements = {"scope": "Requirements parsing error"}
        
        # Render using template service
        template_service = TemplateService()
        rendered_html = template_service.render_proposal(
            project_name=proposal.project_name,
            client_name=proposal.client_name,
            phase=proposal.phase,
            requirements=requirements,
            ai_content=proposal.content or "Content not yet generated",
            template_name=template_name
        )
        
        return {
            "proposal_id": proposal_id,
            "rendered_html": rendered_html,
            "template_used": template_name or "default"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to render template: {str(e)}"
        )


@router.delete("/{proposal_id}")
async def delete_proposal(
    proposal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete proposal (admin only).
    
    Args:
        proposal_id: Proposal ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    # Only admin can delete proposals
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        proposal_service = ProposalService(db)
        success = proposal_service.delete_proposal(proposal_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        return {"message": "Proposal deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete proposal: {str(e)}"
        )


@router.post("/{proposal_id}/blocks", response_model=ProposalBlockResponse)
async def add_proposal_block(
    proposal_id: int,
    block_request: ProposalBlockRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a new block to an existing proposal.
    
    Args:
        proposal_id: ID of the proposal to modify
        block_request: Block content and positioning information
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Updated proposal with new block added
    """
    try:
        proposal_service = ProposalService(db)
        ai_service = AIService()
        
        # Get existing proposal
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Generate AI content for the new block if requested
        block_content = block_request.content
        if block_request.use_ai_generation:
            ai_content = await ai_service.generate_proposal_block(
                block_type=block_request.block_type,
                context=block_request.context,
                project_name=proposal.project_name,
                client_name=proposal.client_name,
                phase=proposal.phase
            )
            block_content = ai_content
        
        # Add block to proposal content
        updated_content = proposal_service.add_block_to_content(
            proposal_id=proposal_id,
            block_type=block_request.block_type,
            block_content=block_content,
            position=block_request.position
        )
        
        return ProposalBlockResponse(
            proposal_id=proposal_id,
            block_id=f"block_{block_request.block_type}_{datetime.utcnow().timestamp()}",
            block_type=block_request.block_type,
            content=block_content,
            position=block_request.position,
            updated_content=updated_content
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add proposal block: {str(e)}"
        )


@router.delete("/{proposal_id}/blocks/{block_id}")
async def remove_proposal_block(
    proposal_id: int,
    block_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a block from an existing proposal.
    
    Args:
        proposal_id: ID of the proposal to modify
        block_id: ID of the block to remove
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Success message with updated content
    """
    try:
        proposal_service = ProposalService(db)
        
        # Get existing proposal
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Remove block from proposal content
        updated_content = proposal_service.remove_block_from_content(
            proposal_id=proposal_id,
            block_id=block_id
        )
        
        return {
            "message": "Block removed successfully",
            "proposal_id": proposal_id,
            "block_id": block_id,
            "updated_content": updated_content
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove proposal block: {str(e)}"
        )


@router.post("/{proposal_id}/validate", response_model=ProposalValidationResponse)
async def validate_proposal(
    proposal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate proposal content and structure for completeness and accuracy.
    
    Args:
        proposal_id: ID of the proposal to validate
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Validation results with issues and recommendations
    """
    try:
        proposal_service = ProposalService(db)
        ai_service = AIService()
        
        # Get existing proposal
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Run validation checks
        validation_result = await ai_service.validate_proposal_content(
            content=proposal.content,
            requirements=proposal.extracted_requirements,
            phase=proposal.phase,
            project_name=proposal.project_name,
            client_name=proposal.client_name
        )
        
        # Update proposal validation status
        proposal_service.update_proposal_validation(
            proposal_id=proposal_id,
            validation_status=validation_result["status"],
            validation_issues=validation_result["issues"],
            validation_score=validation_result["score"]
        )
        
        return ProposalValidationResponse(
            proposal_id=proposal_id,
            validation_status=validation_result["status"],
            validation_score=validation_result["score"],
            issues=validation_result["issues"],
            recommendations=validation_result["recommendations"],
            phase_alignment=validation_result["phase_alignment"],
            completeness_score=validation_result["completeness_score"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate proposal: {str(e)}"
        )


@router.post("/{proposal_id}/context-update")
async def update_proposal_context(
    proposal_id: int,
    phase: str,
    context_data: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update proposal with phase-aware context and regenerate relevant sections.
    
    Args:
        proposal_id: ID of the proposal to update
        phase: New project phase (exploratory, discovery, development, deployment)
        context_data: Additional context information
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Updated proposal with context-aware content
    """
    try:
        proposal_service = ProposalService(db)
        ai_service = AIService()
        
        # Validate phase
        valid_phases = ["exploratory", "discovery", "development", "deployment"]
        if phase not in valid_phases:
            raise HTTPException(
                status_code=400,
                detail=f"Phase must be one of: {valid_phases}"
            )
        
        # Get existing proposal
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Generate phase-aware content updates
        updated_content = await ai_service.update_proposal_for_phase(
            current_content=proposal.content,
            new_phase=phase,
            context_data=context_data,
            project_name=proposal.project_name,
            client_name=proposal.client_name
        )
        
        # Update proposal with new phase and content
        updated_proposal = proposal_service.update_proposal_content(
            proposal_id=proposal_id,
            content=updated_content,
            phase=phase,
            status="draft"
        )
        
        return {
            "message": "Proposal context updated successfully",
            "proposal_id": proposal_id,
            "new_phase": phase,
            "updated_content": updated_content,
            "updated_at": updated_proposal.updated_at
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update proposal context: {str(e)}"
        )


@router.post("/{proposal_id}/share")
async def create_proposal_share(
    proposal_id: int,
    share_type: str = "client_view",  # client_view, public_link, team_access
    expiry_days: Optional[int] = None,
    password_protected: bool = False,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a shareable link for proposal access.
    
    Args:
        proposal_id: ID of the proposal to share
        share_type: Type of sharing (client_view, public_link, team_access)
        expiry_days: Number of days until link expires (None = no expiry)
        password_protected: Whether to require password for access
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Share link details and access information
    """
    try:
        proposal_service = ProposalService(db)
        
        # Get existing proposal
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Generate share token and create share record
        share_token = proposal_service.create_proposal_share(
            proposal_id=proposal_id,
            share_type=share_type,
            created_by=current_user["user_id"],
            expiry_days=expiry_days,
            password_protected=password_protected
        )
        
        # Generate share URL
        base_url = "http://localhost:3000"  # Should come from config
        share_url = f"{base_url}/shared/proposal/{share_token}"
        
        return {
            "share_token": share_token,
            "share_url": share_url,
            "share_type": share_type,
            "proposal_id": proposal_id,
            "expires_at": None if not expiry_days else datetime.utcnow() + timedelta(days=expiry_days),
            "password_protected": password_protected,
            "created_by": current_user["user_id"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create proposal share: {str(e)}"
        )


@router.get("/{proposal_id}/export/{format}")
async def export_proposal(
    proposal_id: int,
    format: str,  # html, pdf, docx, markdown
    include_metadata: bool = True,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export proposal in specified format.
    
    Args:
        proposal_id: ID of the proposal to export
        format: Export format (html, pdf, docx, markdown)
        include_metadata: Whether to include proposal metadata
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Exported proposal file
    """
    from fastapi.responses import FileResponse, Response
    
    try:
        proposal_service = ProposalService(db)
        
        # Get existing proposal
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Generate export content
        export_content = proposal_service.export_proposal(
            proposal_id=proposal_id,
            format=format,
            include_metadata=include_metadata
        )
        
        # Set appropriate headers based on format
        content_types = {
            "html": "text/html",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "markdown": "text/markdown"
        }
        
        filename = f"{proposal.project_name}_{proposal.client_name}_proposal.{format}"
        
        if format in ["pdf", "docx"]:
            # Return file response for binary formats
            return FileResponse(
                export_content,  # This would be a file path
                media_type=content_types[format],
                filename=filename
            )
        else:
            # Return direct content for text formats
            return Response(
                content=export_content,
                media_type=content_types[format],
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export proposal: {str(e)}"
        )


@router.get("/{proposal_id}/history")
async def get_proposal_history(
    proposal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get complete proposal history including versions, shares, and modifications.
    
    Args:
        proposal_id: ID of the proposal
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Complete proposal history and audit trail
    """
    try:
        proposal_service = ProposalService(db)
        
        # Get existing proposal
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Get complete history
        history = proposal_service.get_proposal_complete_history(proposal_id)
        
        return {
            "proposal_id": proposal_id,
            "project_name": proposal.project_name,
            "client_name": proposal.client_name,
            "created_at": proposal.created_at,
            "current_status": proposal.status,
            "versions": history["versions"],
            "shares": history["shares"],
            "modifications": history["modifications"],
            "validation_history": history["validations"],
            "export_history": history["exports"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get proposal history: {str(e)}"
        )


@router.post("/{proposal_id}/duplicate")
async def duplicate_proposal(
    proposal_id: int,
    new_project_name: str,
    new_client_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a duplicate of an existing proposal.
    
    Args:
        proposal_id: ID of the proposal to duplicate
        new_project_name: Name for the new project
        new_client_name: Client name for new proposal (optional)
        current_user: Authenticated user
        db: Database session
        
    Returns:
        New proposal details
    """
    try:
        proposal_service = ProposalService(db)
        
        # Get existing proposal
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Create duplicate
        new_proposal = proposal_service.duplicate_proposal(
            original_proposal_id=proposal_id,
            new_project_name=new_project_name,
            new_client_name=new_client_name or proposal.client_name,
            created_by=current_user["user_id"]
        )
        
        return ProposalResponse(
            id=new_proposal.id,
            project_name=new_proposal.project_name,
            client_name=new_proposal.client_name,
            phase=new_proposal.phase,
            status=new_proposal.status,
            content=new_proposal.content,
            ai_summary=new_proposal.ai_summary,
            extracted_requirements=json.loads(new_proposal.extracted_requirements) if new_proposal.extracted_requirements else None,
            created_at=new_proposal.created_at,
            updated_at=new_proposal.updated_at,
            created_by=new_proposal.created_by
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to duplicate proposal: {str(e)}"
        )


@router.get("/projects/dashboard")
async def get_projects_dashboard(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive project dashboard with status, phases, and metrics.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Dashboard data with project overview and metrics
    """
    try:
        proposal_service = ProposalService(db)
        
        # Get dashboard data
        dashboard_data = proposal_service.get_projects_dashboard(
            user_role=current_user.get("role", "admin")
        )
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get projects dashboard: {str(e)}"
        )


@router.get("/{proposal_id}/project-status")
async def get_project_status(
    proposal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed project status and phase progression.
    
    Args:
        proposal_id: ID of the proposal/project
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Detailed project status with phase breakdown
    """
    try:
        proposal_service = ProposalService(db)
        
        # Get project status
        project_status = proposal_service.get_detailed_project_status(proposal_id)
        
        return project_status
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get project status: {str(e)}"
        )


@router.post("/{proposal_id}/advance-phase")
async def advance_project_phase(
    proposal_id: int,
    completion_notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Advance project to next phase and mark current phase as completed.
    
    Args:
        proposal_id: ID of the proposal/project
        completion_notes: Notes about current phase completion
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Updated project status
    """
    try:
        proposal_service = ProposalService(db)
        
        # Advance project phase
        updated_status = proposal_service.advance_project_phase(
            proposal_id=proposal_id,
            completion_notes=completion_notes,
            updated_by=current_user["user_id"]
        )
        
        return updated_status
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to advance project phase: {str(e)}"
        )


@router.post("/{proposal_id}/update-milestone")
async def update_project_milestone(
    proposal_id: int,
    milestone_name: str,
    milestone_status: str,  # not_started, in_progress, completed, blocked
    milestone_notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update project milestone status and tracking.
    
    Args:
        proposal_id: ID of the proposal/project
        milestone_name: Name of the milestone
        milestone_status: Status of the milestone
        milestone_notes: Additional notes about milestone
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Updated milestone information
    """
    try:
        proposal_service = ProposalService(db)
        
        # Update milestone
        milestone_data = proposal_service.update_project_milestone(
            proposal_id=proposal_id,
            milestone_name=milestone_name,
            milestone_status=milestone_status,
            milestone_notes=milestone_notes,
            updated_by=current_user["user_id"]
        )
        
        return milestone_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update project milestone: {str(e)}"
        )


@router.get("/analytics/summary")
async def get_analytics_summary(
    date_range: Optional[int] = 30,  # days
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get analytics summary for projects and proposals.
    
    Args:
        date_range: Number of days to include in analysis
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Analytics summary with metrics and trends
    """
    try:
        proposal_service = ProposalService(db)
        
        # Get analytics data
        analytics = proposal_service.get_analytics_summary(
            date_range=date_range,
            user_role=current_user.get("role", "admin")
        )
        
        return analytics
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analytics summary: {str(e)}"
        )


# Block 3: Enhanced Sharing, Export, and Audit API Endpoints

@router.post("/{proposal_id}/shares", response_model=ProposalShareResponse)
async def create_proposal_share_enhanced(
    proposal_id: int,
    share_request: ProposalShareRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new proposal share with enhanced permissions and tracking.
    
    Args:
        proposal_id: Proposal ID to share
        share_request: Share configuration
        request: HTTP request for audit trail
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Created share details
    """
    try:
        proposal_service = ProposalService(db)
        
        # Verify proposal exists and user has access
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Extract client info for audit
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Create share
        share = proposal_service.create_proposal_share(
            proposal_id=proposal_id,
            shared_by=current_user["user_id"],
            shared_with_user_id=share_request.shared_with_user_id,
            shared_with_email=share_request.shared_with_email,
            permission_level=share_request.permission_level,
            can_download=share_request.can_download,
            can_comment=share_request.can_comment,
            expires_in_days=share_request.expires_in_days,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        return ProposalShareResponse(
            id=share.id,
            proposal_id=share.proposal_id,
            shared_with_user_id=share.shared_with_user_id,
            shared_with_email=share.shared_with_email,
            permission_level=share.permission_level.value,
            can_download=share.can_download,
            can_comment=share.can_comment,
            expires_at=share.expires_at,
            is_active=share.is_active,
            access_count=share.access_count,
            created_at=share.created_at,
            share_url=f"/shared/proposals/{proposal.share_token}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create proposal share: {str(e)}"
        )


@router.get("/{proposal_id}/shares", response_model=List[ProposalShareResponse])
async def get_proposal_shares(
    proposal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all shares for a proposal.
    
    Args:
        proposal_id: Proposal ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of proposal shares
    """
    try:
        proposal_service = ProposalService(db)
        
        # Verify proposal exists and user has access
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        shares = proposal_service.get_proposal_shares(proposal_id)
        
        return [
            ProposalShareResponse(
                id=share.id,
                proposal_id=share.proposal_id,
                shared_with_user_id=share.shared_with_user_id,
                shared_with_email=share.shared_with_email,
                permission_level=share.permission_level.value,
                can_download=share.can_download,
                can_comment=share.can_comment,
                expires_at=share.expires_at,
                is_active=share.is_active,
                access_count=share.access_count,
                created_at=share.created_at,
                share_url=f"/shared/proposals/{proposal.share_token}"
            )
            for share in shares
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve proposal shares: {str(e)}"
        )


@router.delete("/shares/{share_id}")
async def revoke_proposal_share(
    share_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke a proposal share.
    
    Args:
        share_id: Share ID to revoke
        request: HTTP request for audit trail
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Success confirmation
    """
    try:
        proposal_service = ProposalService(db)
        
        # Extract client info for audit
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        success = proposal_service.revoke_proposal_share(
            share_id=share_id,
            revoked_by=current_user["user_id"],
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Share not found")
        
        return {"message": "Share revoked successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke proposal share: {str(e)}"
        )


@router.get("/{proposal_id}/exports", response_model=List[ProposalExportResponse])
async def get_proposal_exports(
    proposal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all exports for a proposal.
    
    Args:
        proposal_id: Proposal ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of proposal exports
    """
    try:
        proposal_service = ProposalService(db)
        
        # Verify proposal exists and user has access
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        exports = proposal_service.get_proposal_exports(proposal_id)
        
        return [
            ProposalExportResponse(
                id=export.id,
                proposal_id=export.proposal_id,
                format=export.format.value,
                file_path=export.file_path,
                file_size_bytes=export.file_size_bytes,
                version_exported=export.version_exported,
                download_count=export.download_count,
                last_downloaded_at=export.last_downloaded_at,
                created_at=export.created_at,
                download_url=f"/api/v1/proposals/exports/{export.id}/download"
            )
            for export in exports
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve proposal exports: {str(e)}"
        )


@router.post("/exports/{export_id}/download")
async def track_export_download(
    export_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Track a download of an exported proposal.
    
    Args:
        export_id: Export ID
        request: HTTP request for audit trail
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Download tracking confirmation
    """
    try:
        proposal_service = ProposalService(db)
        
        # Extract client info for audit
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        success = proposal_service.track_export_download(
            export_id=export_id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Export not found")
        
        return {"message": "Download tracked successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track export download: {str(e)}"
        )


@router.get("/{proposal_id}/audit-log", response_model=List[ProposalAuditLogResponse])
async def get_proposal_audit_log(
    proposal_id: int,
    limit: int = 100,
    action_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get audit log for a proposal.
    
    Args:
        proposal_id: Proposal ID
        limit: Maximum number of records
        action_filter: Filter by action type
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of audit log entries
    """
    try:
        proposal_service = ProposalService(db)
        
        # Verify proposal exists and user has access
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        audit_logs = proposal_service.get_proposal_audit_log(
            proposal_id=proposal_id,
            limit=limit,
            action_filter=action_filter
        )
        
        return [
            ProposalAuditLogResponse(
                id=log.id,
                proposal_id=log.proposal_id,
                action=log.action.value,
                description=log.description,
                details=json.loads(log.details) if log.details else None,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                old_values=json.loads(log.old_values) if log.old_values else None,
                new_values=json.loads(log.new_values) if log.new_values else None,
                performed_by=log.performed_by,
                created_at=log.created_at
            )
            for log in audit_logs
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve proposal audit log: {str(e)}"
        )


@router.get("/{proposal_id}/analytics", response_model=ProposalAnalyticsResponse)
async def get_proposal_analytics(
    proposal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics for a proposal.
    
    Args:
        proposal_id: Proposal ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Proposal analytics data
    """
    try:
        proposal_service = ProposalService(db)
        
        # Verify proposal exists and user has access
        proposal = proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        analytics = proposal_service.get_proposal_analytics(proposal_id)
        
        return ProposalAnalyticsResponse(**analytics)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve proposal analytics: {str(e)}"
        ) 