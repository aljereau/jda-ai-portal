"""
Team dashboard schemas for JDA AI Portal.
Provides Pydantic models for team management and dashboard functionality.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .proposal import ProposalSummary
from .user import UserSummary


class DashboardMetric(BaseModel):
    """Dashboard metric data structure.
    
    Args:
        label: Display label for the metric
        value: Current metric value
        change: Change from previous period (optional)
        change_type: Type of change (increase, decrease, neutral)
        format_type: How to format the value (number, percentage, currency)
    """
    label: str = Field(..., description="Display label for the metric")
    value: float = Field(..., description="Current metric value")
    change: Optional[float] = Field(None, description="Change from previous period")
    change_type: Optional[str] = Field(None, description="Type of change")
    format_type: str = Field(default="number", description="Value format type")


class TeamAnalytics(BaseModel):
    """Team analytics data structure.
    
    Args:
        total_proposals: Total number of proposals
        active_proposals: Number of active proposals
        completed_proposals: Number of completed proposals
        proposals_this_month: Proposals created this month
        average_completion_time: Average time to complete proposals (days)
        team_productivity: Team productivity metrics
        proposal_status_distribution: Distribution of proposal statuses
        monthly_trends: Monthly trend data
    """
    total_proposals: int = Field(..., description="Total number of proposals")
    active_proposals: int = Field(..., description="Number of active proposals")
    completed_proposals: int = Field(..., description="Number of completed proposals")
    proposals_this_month: int = Field(..., description="Proposals created this month")
    average_completion_time: Optional[float] = Field(None, description="Average completion time in days")
    team_productivity: Dict[str, Any] = Field(default_factory=dict, description="Team productivity metrics")
    proposal_status_distribution: Dict[str, int] = Field(default_factory=dict, description="Proposal status distribution")
    monthly_trends: List[Dict[str, Any]] = Field(default_factory=list, description="Monthly trend data")


class DashboardOverview(BaseModel):
    """Dashboard overview data structure.
    
    Args:
        metrics: Key dashboard metrics
        recent_proposals: Recently created or updated proposals
        team_analytics: Team performance analytics
        user_activity: Recent user activity summary
        system_status: System health and status information
    """
    metrics: List[DashboardMetric] = Field(..., description="Key dashboard metrics")
    recent_proposals: List[ProposalSummary] = Field(..., description="Recent proposals")
    team_analytics: TeamAnalytics = Field(..., description="Team analytics data")
    user_activity: List[Dict[str, Any]] = Field(default_factory=list, description="Recent user activity")
    system_status: Dict[str, Any] = Field(default_factory=dict, description="System status information")


class ProposalAssignment(BaseModel):
    """Proposal assignment request structure.
    
    Args:
        proposal_id: ID of the proposal to assign
        user_id: ID of the user to assign to
        assigned_by_id: ID of the user making the assignment
        notes: Optional assignment notes
    """
    proposal_id: str = Field(..., description="ID of the proposal to assign")
    user_id: str = Field(..., description="ID of the user to assign to")
    assigned_by_id: str = Field(..., description="ID of the user making the assignment")
    notes: Optional[str] = Field(None, description="Optional assignment notes")


class ProposalAssignmentResponse(BaseModel):
    """Proposal assignment response structure.
    
    Args:
        success: Whether the assignment was successful
        message: Response message
        assignment_id: ID of the created assignment (if successful)
        assigned_user: Summary of the assigned user
        assigned_proposal: Summary of the assigned proposal
    """
    success: bool = Field(..., description="Whether the assignment was successful")
    message: str = Field(..., description="Response message")
    assignment_id: Optional[str] = Field(None, description="ID of the created assignment")
    assigned_user: Optional[UserSummary] = Field(None, description="Summary of assigned user")
    assigned_proposal: Optional[ProposalSummary] = Field(None, description="Summary of assigned proposal")


class BulkUpdateOperation(BaseModel):
    """Bulk update operation structure.
    
    Args:
        operation_type: Type of bulk operation (status_update, assignment, delete)
        proposal_ids: List of proposal IDs to update
        update_data: Data to apply in the bulk update
        performed_by_id: ID of the user performing the operation
    """
    operation_type: str = Field(..., description="Type of bulk operation")
    proposal_ids: List[str] = Field(..., description="List of proposal IDs to update")
    update_data: Dict[str, Any] = Field(..., description="Data to apply in bulk update")
    performed_by_id: str = Field(..., description="ID of user performing operation")


class BulkUpdateResult(BaseModel):
    """Bulk update operation result structure.
    
    Args:
        success: Whether the bulk operation was successful
        total_items: Total number of items processed
        successful_updates: Number of successful updates
        failed_updates: Number of failed updates
        errors: List of errors encountered
        updated_proposals: List of successfully updated proposals
    """
    success: bool = Field(..., description="Whether the bulk operation was successful")
    total_items: int = Field(..., description="Total number of items processed")
    successful_updates: int = Field(..., description="Number of successful updates")
    failed_updates: int = Field(..., description="Number of failed updates")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    updated_proposals: List[ProposalSummary] = Field(default_factory=list, description="Successfully updated proposals")


class TeamMember(BaseModel):
    """Team member information structure.
    
    Args:
        user: User summary information
        role: User's role in the team
        active_proposals: Number of active proposals assigned
        completed_proposals: Number of completed proposals
        last_activity: Timestamp of last activity
        performance_metrics: Performance metrics for the team member
    """
    user: UserSummary = Field(..., description="User summary information")
    role: str = Field(..., description="User's role in the team")
    active_proposals: int = Field(default=0, description="Number of active proposals assigned")
    completed_proposals: int = Field(default=0, description="Number of completed proposals")
    last_activity: Optional[datetime] = Field(None, description="Timestamp of last activity")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")


class TeamDashboardData(BaseModel):
    """Complete team dashboard data structure.
    
    Args:
        overview: Dashboard overview data
        team_members: List of team members and their information
        recent_activity: Recent team activity
        pending_actions: Actions requiring attention
    """
    overview: DashboardOverview = Field(..., description="Dashboard overview data")
    team_members: List[TeamMember] = Field(default_factory=list, description="Team members information")
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list, description="Recent team activity")
    pending_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Actions requiring attention") 