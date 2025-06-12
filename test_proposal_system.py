#!/usr/bin/env python3
"""
Simple test script for proposal system validation.
Tests the core proposal generation pipeline built in Phase 3 Block 1.
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'backend'))

# Mock data for testing
MOCK_TRANSCRIPT = """
Meeting with ABC Corporation - Project Discovery Session
Date: December 29, 2024

Attendees:
- John Smith (ABC Corp, CTO)
- Sarah Johnson (ABC Corp, Project Manager)
- JDA Team

Meeting Summary:
John explained that ABC Corp needs a new customer portal system. Their current system is outdated and causing customer satisfaction issues. They need:

1. Modern web portal for customer login and account management
2. Integration with their existing CRM system
3. Mobile-responsive design
4. Timeline: They want to launch in Q2 2025
5. Budget: They have allocated $150,000 for this project

Key requirements discussed:
- Single sign-on integration
- Customer self-service capabilities
- Real-time notifications
- Reporting dashboard for internal teams
- API integration capabilities

Next steps:
- JDA to provide detailed proposal by January 15th
- Technical requirements gathering session scheduled for January 5th
- ABC Corp will provide access to current system for assessment

Risks identified:
- Tight timeline for Q2 launch
- Integration complexity with legacy CRM
- Need for extensive user training
"""

async def test_ai_service():
    """Test AI service functionality."""
    print("=" * 60)
    print("TESTING AI SERVICE")
    print("=" * 60)
    
    try:
        from app.services.ai_service import AIService
        
        ai_service = AIService()
        print(f"✓ AI Service initialized (OpenAI configured: {ai_service.client is not None})")
        
        # Test transcript summary generation
        print("\n📄 Testing transcript summary generation...")
        summary_result = await ai_service.generate_transcript_summary(
            transcript_content=MOCK_TRANSCRIPT,
            project_name="ABC Corp Customer Portal",
            client_name="ABC Corporation",
            phase="discovery"
        )
        
        print(f"✓ Generated summary (length: {len(summary_result['summary'])} chars)")
        print(f"✓ Extracted requirements: {len(summary_result['requirements'])} fields")
        
        # Test proposal content generation
        print("\n📋 Testing proposal content generation...")
        proposal_content = await ai_service.generate_proposal_content(
            requirements=summary_result['requirements'],
            project_name="ABC Corp Customer Portal",
            client_name="ABC Corporation",
            phase="discovery"
        )
        
        print(f"✓ Generated proposal content (length: {len(proposal_content)} chars)")
        
        # Display sample results
        print("\n" + "="*40)
        print("SAMPLE AI SUMMARY OUTPUT:")
        print("="*40)
        print(summary_result['summary'][:300] + "..." if len(summary_result['summary']) > 300 else summary_result['summary'])
        
        print("\n" + "="*40)
        print("SAMPLE REQUIREMENTS EXTRACTED:")
        print("="*40)
        for key, value in summary_result['requirements'].items():
            print(f"• {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI Service test failed: {str(e)}")
        return False

def test_models():
    """Test database models."""
    print("\n" + "=" * 60)
    print("TESTING DATABASE MODELS")
    print("=" * 60)
    
    try:
        from app.models.proposal import Proposal, ProposalVersion, ProjectTracker
        from app.models.proposal import ProjectPhaseEnum, ProposalStatusEnum
        
        print("✓ All models imported successfully")
        print(f"✓ Project phases: {[phase.value for phase in ProjectPhaseEnum]}")
        print(f"✓ Proposal statuses: {[status.value for status in ProposalStatusEnum]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Models test failed: {str(e)}")
        return False

def test_schemas():
    """Test Pydantic schemas."""
    print("\n" + "=" * 60)
    print("TESTING PYDANTIC SCHEMAS")
    print("=" * 60)
    
    try:
        from app.schemas.proposal import (
            TranscriptUploadResponse, ProposalGenerateRequest,
            ProposalResponse, ProjectPhase, ProposalStatus
        )
        
        print("✓ All schemas imported successfully")
        
        # Test schema validation
        test_requirements = {
            "scope": "Customer portal development",
            "timeline": "Q2 2025 launch",
            "deliverables": ["Web portal", "Mobile app", "API integration"]
        }
        
        proposal_request = ProposalGenerateRequest(
            proposal_id=1,
            requirements=test_requirements
        )
        
        print(f"✓ Schema validation passed for proposal request")
        print(f"✓ Requirements validated: {proposal_request.requirements}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schemas test failed: {str(e)}")
        return False

async def main():
    """Run all tests."""
    print("🚀 PHASE 3 PROPOSAL SYSTEM VALIDATION")
    print("Testing core proposal generation pipeline...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    results = []
    
    # Test components
    results.append(("Models", test_models()))
    results.append(("Schemas", test_schemas()))
    results.append(("AI Service", await test_ai_service()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All core components are working correctly!")
        print("✓ Ready to proceed with Block 1 completion")
    else:
        print(f"\n⚠️  {total - passed} component(s) need attention before proceeding")
    
    print("\n📋 Next steps:")
    print("1. Complete Task 1.3: Build proposal template engine")
    print("2. Complete Task 1.4: Create proposal requirements extraction")
    print("3. Complete Task 1.5: Integrate with existing authentication system")

if __name__ == "__main__":
    asyncio.run(main()) 