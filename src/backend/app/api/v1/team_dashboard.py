"""
Team dashboard API endpoints for JDA AI Portal.
Provides REST API for team management, analytics, and proposal operations.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import logging

from ...core.database import get_db
from ...core.auth import get_current_user, require_role
from ...models.user import User, UserRole
from ...services.team_service import TeamService
from ...schemas.team import (
    DashboardOverview, TeamAnalytics, ProposalAssignment, ProposalAssignmentResponse,
    BulkUpdateOperation, BulkUpdateResult, TeamDashboardData
)
from ...schemas.proposal import ProposalSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/team-dashboard", tags=["team-dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DashboardOverview:
    """Get comprehensive team dashboard overview.
    
    This endpoint provides key metrics, recent proposals, team analytics,
    and system status information for the dashboard.
    
    Args:
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Dashboard overview data including metrics and analytics
        
    Raises:
        HTTPException: If user lacks required permissions or data retrieval fails
    """
    logger.info(f"Dashboard overview requested by user {current_user.id} ({current_user.role})")
    
    try:
        team_service = TeamService(db)
        overview = team_service.get_dashboard_overview(
            user_id=str(current_user.id),
            user_role=current_user.role
        )
        
        logger.info(f"Dashboard overview generated successfully for user {current_user.id}")
        return overview
        
    except PermissionError as e:
        logger.warning(f"Permission denied for dashboard overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access dashboard overview"
        )
    except Exception as e:
        logger.error(f"Error generating dashboard overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate dashboard overview"
        )


@router.get("/proposals", response_model=List[ProposalSummary])
async def get_team_proposals(
    status_filter: Optional[str] = Query(None, description="Filter by proposal status"),
    assigned_to_id: Optional[str] = Query(None, description="Filter by assigned user ID"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[ProposalSummary]:
    """Get proposals accessible to the current team member.
    
    This endpoint returns proposals based on the user's role and permissions,
    with optional filtering and pagination.
    
    Args:
        status_filter: Optional status filter
        assigned_to_id: Optional assigned user filter
        date_from: Optional start date filter
        date_to: Optional end date filter
        search: Optional text search
        limit: Maximum results to return
        offset: Pagination offset
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        List of proposal summaries accessible to the user
        
    Raises:
        HTTPException: If user lacks required permissions or data retrieval fails
    """
    logger.info(f"Team proposals requested by user {current_user.id} with filters")
    
    try:
        # Build filters dictionary
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if assigned_to_id:
            filters["assigned_to_id"] = assigned_to_id
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        if search:
            filters["search"] = search
        
        team_service = TeamService(db)
        proposals = team_service.get_team_proposals(
            user_id=str(current_user.id),
            user_role=current_user.role,
            filters=filters
        )
        
        # Apply pagination
        paginated_proposals = proposals[offset:offset + limit]
        
        logger.info(f"Retrieved {len(paginated_proposals)} proposals for user {current_user.id}")
        return paginated_proposals
        
    except PermissionError as e:
        logger.warning(f"Permission denied for team proposals: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access team proposals"
        )
    except Exception as e:
        logger.error(f"Error retrieving team proposals: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team proposals"
        )


@router.get("/analytics", response_model=TeamAnalytics)
async def get_team_analytics(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.PROJECT_MANAGER])),
    db: Session = Depends(get_db)
) -> TeamAnalytics:
    """Get team analytics and performance metrics.
    
    This endpoint provides comprehensive analytics including proposal metrics,
    team productivity, status distribution, and trends. Restricted to admins
    and project managers.
    
    Args:
        current_user: Currently authenticated user (admin or project manager)
        db: Database session
        
    Returns:
        Team analytics data including metrics and trends
        
    Raises:
        HTTPException: If user lacks required permissions or data retrieval fails
    """
    logger.info(f"Team analytics requested by user {current_user.id} ({current_user.role})")
    
    try:
        team_service = TeamService(db)
        analytics = team_service.get_team_analytics(current_user.role)
        
        logger.info(f"Team analytics generated successfully for user {current_user.id}")
        return analytics
        
    except Exception as e:
        logger.error(f"Error generating team analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate team analytics"
        )


@router.post("/assign-proposal", response_model=ProposalAssignmentResponse)
async def assign_proposal_to_user(
    assignment: ProposalAssignment,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.PROJECT_MANAGER])),
    db: Session = Depends(get_db)
) -> ProposalAssignmentResponse:
    """Assign a proposal to a team member.
    
    This endpoint allows admins and project managers to assign proposals
    to team members for management and execution.
    
    Args:
        assignment: Proposal assignment details
        current_user: Currently authenticated user (admin or project manager)
        db: Database session
        
    Returns:
        Assignment response with success status and details
        
    Raises:
        HTTPException: If assignment fails or user lacks permissions
    """
    logger.info(f"Proposal assignment requested: {assignment.proposal_id} -> {assignment.user_id}")
    
    try:
        # Set the assigned_by_id to current user
        assignment.assigned_by_id = str(current_user.id)
        
        team_service = TeamService(db)
        result = team_service.assign_proposal_to_user(
            proposal_id=assignment.proposal_id,
            user_id=assignment.user_id,
            assigned_by_id=assignment.assigned_by_id,
            notes=assignment.notes
        )
        
        if result.success:
            logger.info(f"Proposal {assignment.proposal_id} assigned successfully to user {assignment.user_id}")
        else:
            logger.warning(f"Proposal assignment failed: {result.message}")
        
        return result
        
    except ValueError as e:
        logger.error(f"Invalid assignment data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assignment data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error assigning proposal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign proposal"
        )


@router.post("/bulk-update", response_model=BulkUpdateResult)
async def bulk_update_proposals(
    operation: BulkUpdateOperation,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.PROJECT_MANAGER])),
    db: Session = Depends(get_db)
) -> BulkUpdateResult:
    """Perform bulk update operations on multiple proposals.
    
    This endpoint allows admins and project managers to perform bulk operations
    such as status updates, assignments, or deletions on multiple proposals.
    
    Args:
        operation: Bulk update operation details
        current_user: Currently authenticated user (admin or project manager)
        db: Database session
        
    Returns:
        Bulk update result with success counts and error details
        
    Raises:
        HTTPException: If bulk operation fails or user lacks permissions
    """
    logger.info(f"Bulk update requested: {operation.operation_type} on {len(operation.proposal_ids)} proposals")
    
    try:
        # Set the performed_by_id to current user
        operation.performed_by_id = str(current_user.id)
        
        team_service = TeamService(db)
        result = team_service.bulk_update_proposals(operation)
        
        logger.info(f"Bulk update completed: {result.successful_updates} successful, {result.failed_updates} failed")
        return result
        
    except ValueError as e:
        logger.error(f"Invalid bulk operation data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bulk operation data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error performing bulk update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk update"
        )


@router.get("/dashboard-data", response_model=TeamDashboardData)
async def get_complete_dashboard_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TeamDashboardData:
    """Get complete team dashboard data in a single request.
    
    This endpoint provides all dashboard data including overview, team members,
    recent activity, and pending actions in a single response for efficient
    dashboard loading.
    
    Args:
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Complete team dashboard data
        
    Raises:
        HTTPException: If user lacks required permissions or data retrieval fails
    """
    logger.info(f"Complete dashboard data requested by user {current_user.id}")
    
    try:
        team_service = TeamService(db)
        
        # Get dashboard overview
        overview = team_service.get_dashboard_overview(
            user_id=str(current_user.id),
            user_role=current_user.role
        )
        
        # Get team members (for admins and project managers)
        team_members = []
        if current_user.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]:
            # This would be implemented in the team service
            # team_members = team_service.get_team_members()
            pass
        
        # Get recent activity
        recent_activity = []  # This would come from an activity service
        
        # Get pending actions
        pending_actions = []  # This would come from analyzing proposals and tasks
        
        dashboard_data = TeamDashboardData(
            overview=overview,
            team_members=team_members,
            recent_activity=recent_activity,
            pending_actions=pending_actions
        )
        
        logger.info(f"Complete dashboard data generated successfully for user {current_user.id}")
        return dashboard_data
        
    except PermissionError as e:
        logger.warning(f"Permission denied for dashboard data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access dashboard data"
        )
    except Exception as e:
        logger.error(f"Error generating dashboard data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate dashboard data"
        ) 