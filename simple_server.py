from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import json

app = FastAPI(title="JDA Proposal Maker - Test Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

test_users = {
    "admin@jda.com": {
        "id": 1,
        "email": "admin@jda.com",
        "full_name": "Admin User",
        "role": "admin",
        "password": "AdminPass123!"
    }
}

test_proposals = {}
proposal_id_counter = 1

@app.get("/")
async def root():
    return {"message": "JDA Proposal Maker Test Server", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "JDA Test Server"}

@app.post("/api/v1/auth/login")
async def login(credentials: Dict[str, str]):
    email = credentials.get("email")
    password = credentials.get("password")
    
    user = test_users.get(email)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "access_token": f"mock_token_{user['id']}",
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }

@app.get("/api/v1/proposals/")
async def list_proposals():
    return list(test_proposals.values())

@app.post("/api/v1/proposals/upload-transcript")
async def upload_transcript():
    global proposal_id_counter
    proposal = {
        "proposal_id": proposal_id_counter,
        "project_name": "Sample AI Project",
        "status": "transcript_uploaded"
    }
    test_proposals[proposal_id_counter] = proposal
    proposal_id_counter += 1
    return proposal

@app.post("/api/v1/proposals/generate")
async def generate_proposal(request: Dict[str, Any]):
    proposal_id = request.get("proposal_id")
    if proposal_id not in test_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = test_proposals[proposal_id]
    proposal["status"] = "generated"
    proposal["content"] = {
        "overview": "AI-powered solution",
        "timeline": "2-3 weeks"
    }
    return proposal

@app.post("/api/v1/proposals/{proposal_id}/blocks")
async def add_proposal_block(proposal_id: int, block_data: Dict[str, Any]):
    if proposal_id not in test_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    block_type = block_data.get("block_type", "overview")
    content = block_data.get("content")
    
    if not content:
        # Generate AI content based on block type
        ai_content = {
            "overview": "This AI-powered customer service automation solution will streamline your operations and reduce manual workload by 60-80%.",
            "scope": "The discovery phase includes: process analysis, AI demonstrations, technical feasibility assessment, and implementation roadmap.",
            "timeline": "Phase 1 (Discovery): 2-3 weeks\nPhase 2 (Development): 6-8 weeks\nPhase 3 (Deployment): 2-3 weeks",
            "deliverables": "• Process automation analysis\n• AI demo prototypes\n• Technical implementation plan\n• Training documentation\n• Go-live support",
            "pricing": "Discovery Phase: €3,500\nFull Implementation: €15,000 - €25,000\n(Based on complexity and scale)",
            "risks": "• Integration complexity with existing systems\n• Change management requirements\n• Data quality considerations\n• User adoption timeline"
        }
        content = ai_content.get(block_type, f"AI-generated {block_type} content for your project")
    
    proposal = test_proposals[proposal_id]
    if "blocks" not in proposal:
        proposal["blocks"] = []
    
    block = {
        "block_type": block_type,
        "content": content,
        "created_at": "2024-01-01T10:00:00Z"
    }
    
    proposal["blocks"].append(block)
    return {
        "message": f"Successfully added {block_type} block",
        "block": block,
        "total_blocks": len(proposal["blocks"])
    }

@app.post("/api/v1/proposals/{proposal_id}/validate")
async def validate_proposal(proposal_id: int):
    if proposal_id not in test_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = test_proposals[proposal_id]
    blocks = proposal.get("blocks", [])
    
    # Calculate validation score based on content
    score = 70  # Base score
    if len(blocks) >= 3:
        score += 10  # Has multiple sections
    if any(block["block_type"] == "pricing" for block in blocks):
        score += 10  # Has pricing
    if any(block["block_type"] == "timeline" for block in blocks):
        score += 5   # Has timeline
    
    suggestions = []
    if not any(block["block_type"] == "risks" for block in blocks):
        suggestions.append("Consider adding a risk assessment section")
    if not any(block["block_type"] == "deliverables" for block in blocks):
        suggestions.append("Add specific deliverables section")
    if score < 85:
        suggestions.append("Add more detailed timeline breakdown")
    
    return {
        "validation_status": "passed" if score >= 75 else "needs_improvement",
        "score": score,
        "max_score": 100,
        "suggestions": suggestions,
        "validation_details": {
            "completeness": f"{len(blocks)}/6 sections completed",
            "clarity_score": 85,
            "professional_tone": 90
        }
    }

@app.post("/api/v1/proposals/{proposal_id}/share")
async def create_share(proposal_id: int, share_data: Dict[str, Any]):
    if proposal_id not in test_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    share_type = share_data.get("share_type", "client_view")
    expiry_days = share_data.get("expiry_days", 30)
    
    share_token = f"share_{proposal_id}_{share_type}_{hash(str(proposal_id))}"[:16]
    share_url = f"http://localhost:8000/shared/{share_token}"
    
    return {
        "share_url": share_url,
        "share_token": share_token,
        "share_type": share_type,
        "expires_at": "2024-02-01T00:00:00Z",
        "permissions": {
            "can_view": True,
            "can_comment": share_type in ["team_access"],
            "can_edit": False
        }
    }

@app.get("/api/v1/proposals/{proposal_id}/export/{format}")
async def export_proposal(proposal_id: int, format: str):
    if proposal_id not in test_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = test_proposals[proposal_id]
    blocks = proposal.get("blocks", [])
    
    if format == "html":
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Proposal: {proposal.get('project_name', 'Untitled')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #007bff; border-bottom: 2px solid #007bff; }}
        h2 {{ color: #333; margin-top: 30px; }}
        .block {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007bff; background: #f8f9fa; }}
    </style>
</head>
<body>
    <h1>Project Proposal: {proposal.get('project_name', 'Untitled')}</h1>
    <p><strong>Status:</strong> {proposal.get('status', 'Draft')}</p>
    <p><strong>Generated:</strong> 2024-01-01</p>
"""
        for block in blocks:
            html_content += f"""
    <div class="block">
        <h2>{block['block_type'].title()}</h2>
        <p>{block['content']}</p>
    </div>
"""
        html_content += "</body></html>"
        return html_content
    
    elif format == "markdown":
        md_content = f"""# Project Proposal: {proposal.get('project_name', 'Untitled')}

**Status:** {proposal.get('status', 'Draft')}  
**Generated:** 2024-01-01

---

"""
        for block in blocks:
            md_content += f"""## {block['block_type'].title()}

{block['content']}

"""
        return md_content
    
    else:
        return {
            "message": f"Export to {format.upper()} format completed successfully",
            "file_size": "2.4 MB",
            "download_url": f"/downloads/proposal_{proposal_id}.{format}"
        }

@app.get("/api/v1/proposals/{proposal_id}/project-status")
async def get_project_status(proposal_id: int):
    if proposal_id not in test_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return {
        "proposal_id": proposal_id,
        "current_phase": "discovery",
        "progress_percentage": 65,
        "phase_status": "in_progress",
        "milestones": [
            {
                "name": "Initial Meeting",
                "status": "completed",
                "completion_date": "2024-01-01",
                "description": "Kick-off meeting with stakeholders"
            },
            {
                "name": "Requirements Analysis",
                "status": "in_progress",
                "progress": 80,
                "description": "Analyzing current processes and requirements"
            },
            {
                "name": "AI Demo Preparation",
                "status": "not_started",
                "description": "Preparing AI demonstration prototypes"
            },
            {
                "name": "Technical Assessment",
                "status": "not_started",
                "description": "Technical feasibility and integration analysis"
            }
        ],
        "next_actions": [
            "Complete requirements documentation",
            "Schedule AI demonstration session",
            "Prepare technical architecture proposal"
        ],
        "estimated_completion": "2024-01-15"
    }

@app.post("/api/v1/proposals/{proposal_id}/advance-phase")
async def advance_phase(proposal_id: int, phase_data: Dict[str, Any] = {}):
    if proposal_id not in test_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    current_phases = ["exploratory", "discovery", "development", "deployment"]
    current_phase = "discovery"  # Mock current phase
    
    try:
        current_index = current_phases.index(current_phase)
        if current_index < len(current_phases) - 1:
            new_phase = current_phases[current_index + 1]
        else:
            new_phase = "completed"
    except ValueError:
        new_phase = "development"
    
    return {
        "message": f"Successfully advanced from {current_phase} to {new_phase}",
        "previous_phase": current_phase,
        "new_phase": new_phase,
        "completion_notes": phase_data.get("completion_notes", "Phase completed successfully"),
        "next_milestones": [
            f"{new_phase.title()} planning",
            f"{new_phase.title()} execution",
            f"{new_phase.title()} review"
        ],
        "updated_at": "2024-01-01T12:00:00Z"
    }

@app.post("/api/v1/proposals/{proposal_id}/update-milestone")
async def update_milestone(proposal_id: int, milestone_data: Dict[str, Any]):
    if proposal_id not in test_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    milestone_name = milestone_data.get("milestone_name", "Unnamed Milestone")
    milestone_status = milestone_data.get("milestone_status", "not_started")
    
    return {
        "message": f"Milestone '{milestone_name}' updated to '{milestone_status}'",
        "milestone": {
            "name": milestone_name,
            "status": milestone_status,
            "updated_at": "2024-01-01T12:00:00Z",
            "notes": milestone_data.get("milestone_notes", ""),
            "completion_percentage": {
                "not_started": 0,
                "in_progress": 50,
                "completed": 100,
                "blocked": 25
            }.get(milestone_status, 0)
        },
        "project_impact": f"Project phase progress updated based on milestone status"
    }

@app.get("/api/v1/proposals/{proposal_id}/history")
async def get_proposal_history(proposal_id: int):
    if proposal_id not in test_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return {
        "proposal_id": proposal_id,
        "history": [
            {
                "id": 1,
                "action": "created",
                "timestamp": "2024-01-01T09:00:00Z",
                "user": "admin@jda.com",
                "description": "Proposal created from meeting transcript",
                "details": {"source": "transcript_upload", "file_size": "2.1KB"}
            },
            {
                "id": 2,
                "action": "generated",
                "timestamp": "2024-01-01T09:15:00Z",
                "user": "admin@jda.com",
                "description": "AI content generation completed",
                "details": {"sections_generated": 2, "ai_model": "gpt-4"}
            },
            {
                "id": 3,
                "action": "block_added",
                "timestamp": "2024-01-01T10:30:00Z",
                "user": "admin@jda.com",
                "description": "Added overview block",
                "details": {"block_type": "overview", "content_length": 145}
            },
            {
                "id": 4,
                "action": "validated",
                "timestamp": "2024-01-01T11:00:00Z",
                "user": "admin@jda.com",
                "description": "Proposal validation completed",
                "details": {"score": 85, "status": "passed"}
            },
            {
                "id": 5,
                "action": "shared",
                "timestamp": "2024-01-01T11:30:00Z",
                "user": "admin@jda.com",
                "description": "Shared with client",
                "details": {"share_type": "client_view", "expires": "2024-02-01"}
            }
        ],
        "total_actions": 5,
        "last_modified": "2024-01-01T11:30:00Z",
        "version": "1.4"
    }

@app.get("/api/v1/proposals/analytics/summary")
async def get_analytics():
    return {
        "overview": {
            "total_proposals": len(test_proposals),
            "proposals_this_month": 8,
            "proposals_this_week": 3,
            "success_rate": 87.5,
            "average_completion_time": "4.2 days"
        },
        "proposal_status_distribution": {
            "draft": 2,
            "in_review": 3,
            "approved": 15,
            "completed": 12
        },
        "phase_distribution": {
            "exploratory": 4,
            "discovery": 6,
            "development": 8,
            "deployment": 3
        },
        "performance_metrics": {
            "average_score": 84.3,
            "client_satisfaction": 4.6,
            "time_to_approval": "2.1 days",
            "revision_cycles": 1.8
        },
        "recent_activity": [
            {"date": "2024-01-01", "proposals_created": 2, "proposals_completed": 1},
            {"date": "2023-12-31", "proposals_created": 1, "proposals_completed": 2},
            {"date": "2023-12-30", "proposals_created": 3, "proposals_completed": 1}
        ],
        "top_clients": [
            {"name": "Test Client Inc", "proposals": 3, "success_rate": 100},
            {"name": "Demo Corp", "proposals": 2, "success_rate": 90},
            {"name": "Sample LLC", "proposals": 1, "success_rate": 85}
        ]
    }

@app.get("/api/v1/proposals/projects/dashboard")
async def get_projects_dashboard():
    return {
        "summary": {
            "active_projects": 6,
            "completed_projects": 15,
            "pending_proposals": 4,
            "total_revenue": "€125,000",
            "success_rate": 89.2
        },
        "active_projects": [
            {
                "id": 1,
                "name": "Sample AI Project",
                "client": "Test Client Inc",
                "phase": "discovery",
                "progress": 65,
                "deadline": "2024-01-15",
                "status": "on_track"
            },
            {
                "id": 2,
                "name": "Automation Suite",
                "client": "Demo Corp",
                "phase": "development",
                "progress": 45,
                "deadline": "2024-02-01",
                "status": "on_track"
            },
            {
                "id": 3,
                "name": "Data Analytics Platform",
                "client": "Sample LLC",
                "phase": "deployment",
                "progress": 90,
                "deadline": "2024-01-10",
                "status": "ahead"
            }
        ],
        "phase_breakdown": {
            "exploratory": {"count": 2, "percentage": 12.5},
            "discovery": {"count": 3, "percentage": 18.8},
            "development": {"count": 7, "percentage": 43.8},
            "deployment": {"count": 4, "percentage": 25.0}
        },
        "recent_completions": [
            {
                "project": "CRM Integration",
                "client": "Previous Client",
                "completed": "2023-12-28",
                "duration": "6 weeks",
                "satisfaction": 4.8
            }
        ],
        "upcoming_deadlines": [
            {"project": "Data Analytics Platform", "deadline": "2024-01-10", "days_remaining": 9},
            {"project": "Sample AI Project", "deadline": "2024-01-15", "days_remaining": 14}
        ],
        "resource_utilization": {
            "team_capacity": 85,
            "available_hours": 120,
            "allocated_hours": 102
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting test server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 