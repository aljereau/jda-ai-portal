"""
Client Portal API Endpoints
Provides read-only access to proposals and project progress for client users.

Features:
- Client-specific proposal viewing
- Public access via share tokens
- Project progress tracking
- Read-only access controls
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, optional_auth
from app.models.user import User
from app.models.proposal import Proposal, ProposalShare
from app.services.proposal_service import ProposalService
from app.schemas.proposal import ProposalResponse, ProjectStatusResponse

router = APIRouter(prefix="/client-portal", tags=["client-portal"])

@router.get("/proposals", response_model=List[ProposalResponse])
async def get_client_proposals(
    status: Optional[List[str]] = Query(None),
    phase: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[ProposalResponse]:
    """
    Get proposals accessible to the current client user.
    
    Args:
        status: Optional list of statuses to filter by
        phase: Optional phase to filter by
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of proposals accessible to the client
        
    Raises:
        HTTPException: If user is not authorized or proposals not found
    """
    try:
        proposal_service = ProposalService(db)
        
        # Only allow clients to see approved/sent/accepted proposals
        allowed_statuses = ['approved', 'sent', 'accepted']
        if status:
            # Filter to only allowed statuses
            status = [s for s in status if s in allowed_statuses]
        else:
            status = allowed_statuses
        
        # Get proposals where user is the client or has shared access
        proposals = proposal_service.search_proposals(
            user_id=current_user.id,
            status=status,
            phase=phase,
            client_access_only=True
        )
        
        if not proposals:
            return []
            
        return [ProposalResponse.from_orm(proposal) for proposal in proposals]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve client proposals: {str(e)}"
        )

@router.get("/proposals/shared/{share_token}", response_model=ProposalResponse)
async def get_shared_proposal(
    share_token: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(optional_auth)
) -> ProposalResponse:
    """
    Get a proposal via public share token (no authentication required).
    
    Args:
        share_token: Public share token for the proposal
        db: Database session
        current_user: Optional current user (for logging)
        
    Returns:
        Proposal accessible via share token
        
    Raises:
        HTTPException: If share token is invalid or expired
    """
    try:
        proposal_service = ProposalService(db)
        
        # Get proposal by share token
        proposal_share = db.query(ProposalShare).filter(
            ProposalShare.share_token == share_token,
            ProposalShare.is_active == True
        ).first()
        
        if not proposal_share:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share token not found or expired"
            )
        
        # Check if share has expired
        if proposal_share.expires_at and proposal_share.expires_at < proposal_service._get_current_timestamp():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Share token has expired"
            )
        
        # Get the proposal
        proposal = db.query(Proposal).filter(
            Proposal.id == proposal_share.proposal_id
        ).first()
        
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found"
            )
        
        # Log access if user is authenticated
        if current_user:
            proposal_service.log_audit_event(
                proposal.id,
                current_user.id,
                "shared_access",
                f"Accessed proposal via share token: {share_token}"
            )
        
        # Update access count
        proposal_share.access_count += 1
        proposal_share.last_accessed_at = proposal_service._get_current_timestamp()
        db.commit()
        
        return ProposalResponse.from_orm(proposal)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve shared proposal: {str(e)}"
        )

@router.get("/proposals/{proposal_id}/project-status", response_model=ProjectStatusResponse)
async def get_client_project_status(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(optional_auth)
) -> ProjectStatusResponse:
    """
    Get project status for a proposal (accessible to clients).
    
    Args:
        proposal_id: ID of the proposal
        db: Database session
        current_user: Optional current user
        
    Returns:
        Project status information
        
    Raises:
        HTTPException: If proposal not found or access denied
    """
    try:
        proposal_service = ProposalService(db)
        
        # Get proposal
        proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found"
            )
        
        # Check access permissions
        has_access = False
        
        if current_user:
            # Check if user is the client or has shared access
            if proposal.client_id == current_user.id:
                has_access = True
            else:
                # Check for shared access
                share = db.query(ProposalShare).filter(
                    ProposalShare.proposal_id == proposal_id,
                    ProposalShare.shared_with_user_id == current_user.id,
                    ProposalShare.is_active == True
                ).first()
                
                if share and (not share.expires_at or share.expires_at > proposal_service._get_current_timestamp()):
                    has_access = True
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this proposal"
            )
        
        # Get project status
        project_status = proposal_service.get_detailed_project_status(proposal_id)
        
        # Log access
        if current_user:
            proposal_service.log_audit_event(
                proposal_id,
                current_user.id,
                "status_view",
                "Viewed project status from client portal"
            )
        
        return project_status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project status: {str(e)}"
        )

@router.get("/proposals/{proposal_id}/export/{format}")
async def export_client_proposal(
    proposal_id: int,
    format: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(optional_auth)
):
    """
    Export a proposal in the specified format (client access).
    
    Args:
        proposal_id: ID of the proposal to export
        format: Export format (html, pdf, docx, markdown)
        db: Database session
        current_user: Optional current user
        
    Returns:
        File download response
        
    Raises:
        HTTPException: If proposal not found, access denied, or export fails
    """
    try:
        proposal_service = ProposalService(db)
        
        # Get proposal
        proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found"
            )
        
        # Check access permissions (same logic as project status)
        has_access = False
        
        if current_user:
            if proposal.client_id == current_user.id:
                has_access = True
            else:
                # Check for shared access
                share = db.query(ProposalShare).filter(
                    ProposalShare.proposal_id == proposal_id,
                    ProposalShare.shared_with_user_id == current_user.id,
                    ProposalShare.is_active == True
                ).first()
                
                if share and (not share.expires_at or share.expires_at > proposal_service._get_current_timestamp()):
                    has_access = True
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this proposal"
            )
        
        # Export proposal
        export_result = proposal_service.export_proposal(proposal_id, format, current_user.id if current_user else None)
        
        # Log export
        if current_user:
            proposal_service.log_audit_event(
                proposal_id,
                current_user.id,
                "export",
                f"Exported proposal as {format} from client portal"
            )
        
        return export_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export proposal: {str(e)}"
        )

@router.get("/dashboard", response_model=dict)
async def get_client_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Get client dashboard with summary information.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dashboard data with proposal summaries and project status
        
    Raises:
        HTTPException: If user is not authorized
    """
    try:
        proposal_service = ProposalService(db)
        
        # Get client's proposals
        proposals = proposal_service.search_proposals(
            user_id=current_user.id,
            status=['approved', 'sent', 'accepted'],
            client_access_only=True
        )
        
        # Calculate summary statistics
        total_proposals = len(proposals)
        active_projects = len([p for p in proposals if p.status == 'accepted'])
        pending_proposals = len([p for p in proposals if p.status == 'sent'])
        
        # Get recent activity (last 5 proposals)
        recent_proposals = sorted(proposals, key=lambda x: x.updated_at, reverse=True)[:5]
        
        # Get project phases summary
        phase_summary = {}
        for proposal in proposals:
            if proposal.status == 'accepted':  # Only count active projects
                phase = proposal.phase or 'exploratory'
                phase_summary[phase] = phase_summary.get(phase, 0) + 1
        
        dashboard_data = {
            "summary": {
                "total_proposals": total_proposals,
                "active_projects": active_projects,
                "pending_proposals": pending_proposals,
                "phase_summary": phase_summary
            },
            "recent_proposals": [
                {
                    "id": p.id,
                    "project_name": p.project_name,
                    "status": p.status,
                    "phase": p.phase,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None
                }
                for p in recent_proposals
            ]
        }
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve client dashboard: {str(e)}"
        ) 