"""
AI Service for transcript processing and proposal generation.
Handles OpenAI API integration for meeting summary and proposal content generation.
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Custom exception for AI service errors."""
    pass


class AIService:
    """
    AI service for processing transcripts and generating proposals.
    Uses OpenAI GPT models for content generation.
    """

    def __init__(self):
        """Initialize AI service with OpenAI configuration."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            self.client = None
        else:
            try:
                import openai
                self.client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("OpenAI package not installed")
                self.client = None
        
        self.model = "gpt-4"  # Default model
        self.max_tokens = 4000
        self.temperature = 0.7

    async def generate_transcript_summary(
        self,
        transcript_content: str,
        project_name: str,
        client_name: str,
        phase: str
    ) -> Dict[str, Any]:
        """
        Generate AI summary from meeting transcript.
        
        Args:
            transcript_content: Raw transcript text
            project_name: Name of the project
            client_name: Client company name
            phase: Project phase (exploratory, discovery, development, deployment)
            
        Returns:
            Dictionary containing summary and extracted requirements
        """
        if not self.client:
            # Return mock data if OpenAI not configured
            return self._generate_mock_summary(
                transcript_content, project_name, client_name, phase
            )

        try:
            # Build context-aware prompt based on phase
            phase_context = self._get_phase_context(phase)
            
            prompt = f"""
            You are an expert business analyst analyzing a meeting transcript for a {phase} phase project.
            
            Context:
            - Project: {project_name}
            - Client: {client_name}
            - Phase: {phase} - {phase_context}
            
            Please analyze this meeting transcript and provide:
            1. A concise executive summary (2-3 paragraphs)
            2. Extracted requirements structured as JSON
            3. Key deliverables mentioned
            4. Timeline discussions
            5. Budget/pricing mentions
            6. Risks and assumptions identified
            
            Transcript:
            {transcript_content}
            
            Please respond with a JSON object containing:
            {{
                "summary": "Executive summary text",
                "requirements": {{
                    "scope": "Project scope details",
                    "timeline": "Timeline requirements",
                    "deliverables": ["list", "of", "deliverables"],
                    "budget_range": "Budget discussions or 'Not discussed'",
                    "technical_requirements": ["technical", "requirements"],
                    "business_objectives": ["business", "goals"]
                }},
                "key_insights": ["key", "insights", "from", "meeting"],
                "next_steps": ["identified", "next", "steps"],
                "risks_assumptions": ["identified", "risks", "and", "assumptions"]
            }}
            """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert business analyst who creates detailed project summaries from meeting transcripts."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            # Parse AI response
            ai_content = response.choices[0].message.content
            
            try:
                # Try to parse as JSON
                result = json.loads(ai_content)
            except json.JSONDecodeError:
                # If not valid JSON, create structured response
                result = {
                    "summary": ai_content,
                    "requirements": {
                        "scope": "To be defined based on analysis",
                        "timeline": "To be discussed",
                        "deliverables": ["Analysis pending"],
                        "budget_range": "Not discussed",
                        "technical_requirements": ["To be determined"],
                        "business_objectives": ["Initial assessment needed"]
                    }
                }

            logger.info(f"Generated AI summary for project: {project_name}")
            return result

        except Exception as e:
            logger.error(f"Error generating AI summary: {str(e)}")
            raise AIServiceError(f"Failed to generate transcript summary: {str(e)}")

    async def generate_proposal_content(
        self,
        requirements: Dict[str, Any],
        project_name: str,
        client_name: str,
        phase: str,
        template_preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate proposal content based on requirements.
        
        Args:
            requirements: Extracted project requirements
            project_name: Name of the project
            client_name: Client company name
            phase: Project phase
            template_preferences: Template customization options
            
        Returns:
            Generated proposal HTML content
        """
        if not self.client:
            return self._generate_mock_proposal(
                requirements, project_name, client_name, phase
            )

        try:
            # Build comprehensive proposal prompt
            prompt = f"""
            Create a professional project proposal based on the following requirements:
            
            Project Details:
            - Name: {project_name}
            - Client: {client_name}
            - Phase: {phase}
            
            Requirements:
            {json.dumps(requirements, indent=2)}
            
            Please generate a comprehensive proposal that includes:
            1. Executive Summary
            2. Project Overview
            3. Scope of Work
            4. Deliverables
            5. Timeline
            6. Budget Estimate (if discussed)
            7. Next Steps
            8. Terms and Conditions
            
            Format the response as clean HTML that can be embedded in a proposal template.
            Use professional business language appropriate for a {phase} phase proposal.
            Include specific details from the requirements where available.
            """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert proposal writer who creates comprehensive project proposals in HTML format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.6  # Slightly lower temperature for more consistent proposals
            )

            proposal_content = response.choices[0].message.content

            logger.info(f"Generated proposal content for project: {project_name}")
            return proposal_content

        except Exception as e:
            logger.error(f"Error generating proposal content: {str(e)}")
            raise AIServiceError(f"Failed to generate proposal content: {str(e)}")

    async def expand_proposal_section(
        self,
        current_content: str,
        section_type: str,
        expansion_request: str
    ) -> str:
        """
        Expand or modify specific sections of a proposal.
        
        Args:
            current_content: Current proposal content
            section_type: Type of section to expand (e.g., "deliverables", "timeline")
            expansion_request: Specific expansion request
            
        Returns:
            Updated proposal content
        """
        if not self.client:
            return current_content + f"\n\n<!-- {section_type} expansion: {expansion_request} -->"

        try:
            prompt = f"""
            You are helping to expand/modify a proposal section.
            
            Current proposal content:
            {current_content}
            
            Section to modify: {section_type}
            Requested change: {expansion_request}
            
            Please provide the updated proposal content with the requested changes.
            Maintain the existing HTML structure and professional tone.
            Only modify the relevant section while preserving the rest of the content.
            """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert proposal editor who makes precise modifications to proposal content."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.5
            )

            updated_content = response.choices[0].message.content
            logger.info(f"Expanded proposal section: {section_type}")
            return updated_content

        except Exception as e:
            logger.error(f"Error expanding proposal section: {str(e)}")
            raise AIServiceError(f"Failed to expand proposal section: {str(e)}")

    def _get_phase_context(self, phase: str) -> str:
        """Get context description for project phase."""
        phase_contexts = {
            "exploratory": "Initial exploration and feasibility assessment",
            "discovery": "Detailed requirements gathering and solution design",
            "development": "Active development and implementation",
            "deployment": "Final deployment and go-live preparation"
        }
        return phase_contexts.get(phase, "General project phase")

    def _generate_mock_summary(
        self,
        transcript_content: str,
        project_name: str,
        client_name: str,
        phase: str
    ) -> Dict[str, Any]:
        """Generate mock summary when OpenAI is not available."""
        logger.info("Generating mock AI summary (OpenAI not configured)")
        
        return {
            "summary": f"Mock AI Summary for {project_name}: This is a simulated analysis of the meeting transcript for {client_name}. The discussion covered key project requirements and next steps for the {phase} phase. Further analysis would be performed with actual AI integration.",
            "requirements": {
                "scope": f"Initial scope discussion for {project_name}",
                "timeline": "Timeline to be defined",
                "deliverables": ["Project deliverables from transcript analysis"],
                "budget_range": "Not discussed in detail",
                "technical_requirements": ["Technical requirements to be extracted"],
                "business_objectives": ["Business goals identified in meeting"]
            },
            "key_insights": ["Mock insight 1", "Mock insight 2"],
            "next_steps": ["Schedule follow-up meeting", "Prepare detailed requirements"],
            "risks_assumptions": ["Assumption about project scope", "Risk regarding timeline"]
        }

    def _generate_mock_proposal(
        self,
        requirements: Dict[str, Any],
        project_name: str,
        client_name: str,
        phase: str
    ) -> str:
        """Generate mock proposal when OpenAI is not available."""
        logger.info("Generating mock proposal content (OpenAI not configured)")
        
        deliverables_html = "".join([f"<li>{item}</li>" for item in requirements.get('deliverables', ['Mock deliverable'])])
        
        return f"""
        <div class="proposal-content">
            <h1>Project Proposal: {project_name}</h1>
            <h2>Client: {client_name}</h2>
            <h3>Phase: {phase.title()}</h3>
            
            <section class="executive-summary">
                <h3>Executive Summary</h3>
                <p>This is a mock proposal generated for demonstration purposes. 
                In a production environment, this would be generated by AI based on 
                the meeting transcript and extracted requirements.</p>
            </section>
            
            <section class="scope">
                <h3>Project Scope</h3>
                <p>Scope: {requirements.get('scope', 'To be defined')}</p>
            </section>
            
            <section class="deliverables">
                <h3>Deliverables</h3>
                <ul>
                    {deliverables_html}
                </ul>
            </section>
            
            <section class="timeline">
                <h3>Timeline</h3>
                <p>Timeline: {requirements.get('timeline', 'To be discussed')}</p>
            </section>
            
            <section class="next-steps">
                <h3>Next Steps</h3>
                <p>1. Review and approve this proposal</p>
                <p>2. Schedule project kickoff meeting</p>
                <p>3. Begin {phase} phase activities</p>
            </section>
        </div>
        """

    async def generate_proposal_block(
        self,
        block_type: str,
        context: Dict[str, Any],
        project_name: str,
        client_name: str,
        phase: str
    ) -> str:
        """
        Generate a specific proposal block using AI.
        
        Args:
            block_type: Type of block to generate (overview, scope, timeline, etc.)
            context: Context information for block generation
            project_name: Project name
            client_name: Client name
            phase: Project phase
            
        Returns:
            Generated block content as HTML
        """
        if not self.client:
            return self._generate_mock_block(block_type, context, project_name, client_name, phase)

        try:
            block_prompts = {
                "overview": "Create a comprehensive project overview section",
                "scope": "Define detailed project scope and boundaries",
                "timeline": "Create a realistic project timeline with milestones",
                "deliverables": "List specific project deliverables and outcomes",
                "pricing": "Provide transparent pricing structure and payment terms",
                "risks": "Identify and assess project risks with mitigation strategies",
                "assumptions": "Document key project assumptions and dependencies",
                "support": "Outline post-project support and maintenance options",
                "payment": "Define payment schedules and terms",
                "terms": "Specify contract terms and conditions",
                "custom": "Generate custom content based on specific requirements"
            }

            block_prompt = block_prompts.get(block_type, block_prompts["custom"])
            
            prompt = f"""
            {block_prompt} for the following project:
            
            Project: {project_name}
            Client: {client_name}
            Phase: {phase}
            
            Context:
            {json.dumps(context, indent=2)}
            
            Generate professional, detailed content for this {block_type} section.
            Format as clean HTML that can be inserted into a proposal.
            Use appropriate headers, lists, and structure for readability.
            Ensure content is specific to the {phase} phase and project context.
            """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert proposal writer specializing in {block_type} sections. Generate precise, professional content."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1500,  # Smaller max tokens for focused blocks
                temperature=0.7
            )

            block_content = response.choices[0].message.content
            logger.info(f"Generated {block_type} block for project: {project_name}")
            return block_content

        except Exception as e:
            logger.error(f"Error generating proposal block: {str(e)}")
            return self._generate_mock_block(block_type, context, project_name, client_name, phase)

    async def validate_proposal_content(
        self,
        content: str,
        requirements: Dict[str, Any],
        phase: str,
        project_name: str,
        client_name: str
    ) -> Dict[str, Any]:
        """
        Validate proposal content for completeness and accuracy.
        
        Args:
            content: Proposal content to validate
            requirements: Original project requirements
            phase: Project phase
            project_name: Project name
            client_name: Client name
            
        Returns:
            Validation results with status, score, issues, and recommendations
        """
        if not self.client:
            return self._generate_mock_validation(content, requirements, phase)

        try:
            prompt = f"""
            Analyze this proposal for completeness, accuracy, and alignment with requirements.
            
            Project: {project_name}
            Client: {client_name}
            Phase: {phase}
            
            Original Requirements:
            {json.dumps(requirements, indent=2)}
            
            Proposal Content:
            {content}
            
            Please evaluate:
            1. Completeness - Are all essential sections present?
            2. Accuracy - Does content align with requirements?
            3. Phase alignment - Is content appropriate for {phase} phase?
            4. Professional quality - Is writing clear and professional?
            5. Structure - Is the proposal well-organized?
            
            Return a JSON response with:
            - status: "pass", "warning", or "fail"
            - score: 0-100 overall quality score
            - issues: array of specific issues found
            - recommendations: array of improvement suggestions
            - phase_alignment: analysis of phase appropriateness
            - completeness_score: 0-100 completeness score
            """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert proposal reviewer. Analyze proposals for quality, completeness, and accuracy. Respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3  # Lower temperature for consistent validation
            )

            validation_response = response.choices[0].message.content
            
            # Parse JSON response
            try:
                validation_data = json.loads(validation_response)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                validation_data = {
                    "status": "warning",
                    "score": 75,
                    "issues": [{"issue_type": "parsing", "severity": "medium", "description": "Could not parse AI validation response"}],
                    "recommendations": ["Review proposal structure and content"],
                    "phase_alignment": {"appropriate": True, "notes": "Phase alignment unclear"},
                    "completeness_score": 70
                }

            logger.info(f"Validated proposal for project: {project_name}")
            return validation_data

        except Exception as e:
            logger.error(f"Error validating proposal: {str(e)}")
            return self._generate_mock_validation(content, requirements, phase)

    async def update_proposal_for_phase(
        self,
        current_content: str,
        new_phase: str,
        context_data: Dict[str, Any],
        project_name: str,
        client_name: str
    ) -> str:
        """
        Update proposal content for a new project phase.
        
        Args:
            current_content: Current proposal content
            new_phase: New project phase
            context_data: Additional context for the phase update
            project_name: Project name
            client_name: Client name
            
        Returns:
            Updated proposal content optimized for the new phase
        """
        if not self.client:
            return self._generate_mock_phase_update(current_content, new_phase, project_name)

        try:
            phase_descriptions = {
                "exploratory": "Initial exploration, feasibility assessment, and high-level planning",
                "discovery": "Detailed requirements gathering, solution design, and planning",
                "development": "Active development, implementation, and iterative delivery",
                "deployment": "Final testing, deployment preparation, and go-live support"
            }

            phase_focus = phase_descriptions.get(new_phase, "General project activities")

            prompt = f"""
            Update this proposal to align with the {new_phase} phase of the project.
            
            Project: {project_name}
            Client: {client_name}
            New Phase: {new_phase}
            Phase Focus: {phase_focus}
            
            Context Data:
            {json.dumps(context_data, indent=2)}
            
            Current Proposal:
            {current_content}
            
            Please update the proposal to:
            1. Reflect {new_phase} phase priorities and activities
            2. Adjust timeline and deliverables for this phase
            3. Update scope to match phase-specific work
            4. Modify language to be phase-appropriate
            5. Add any phase-specific sections or requirements
            
            Preserve the overall structure and any manually edited content.
            Focus updates on sections that need phase-specific adjustments.
            Return complete updated HTML content.
            """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert proposal writer who adapts proposals for different project phases. Focus on {new_phase} phase requirements."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.6
            )

            updated_content = response.choices[0].message.content
            logger.info(f"Updated proposal for {new_phase} phase: {project_name}")
            return updated_content

        except Exception as e:
            logger.error(f"Error updating proposal for phase: {str(e)}")
            return self._generate_mock_phase_update(current_content, new_phase, project_name)

    def _generate_mock_block(
        self,
        block_type: str,
        context: Dict[str, Any],
        project_name: str,
        client_name: str,
        phase: str
    ) -> str:
        """Generate mock block content when OpenAI is not available."""
        logger.info(f"Generating mock {block_type} block (OpenAI not configured)")
        
        mock_blocks = {
            "overview": f"<h3>Project Overview</h3><p>Mock overview for {project_name} - {client_name} in {phase} phase.</p>",
            "scope": f"<h3>Project Scope</h3><p>Mock scope definition for {project_name}. Detailed scope would be AI-generated based on context.</p>",
            "timeline": f"<h3>Timeline</h3><p>Mock timeline for {phase} phase of {project_name}. Actual timeline would be context-aware.</p>",
            "deliverables": f"<h3>Deliverables</h3><ul><li>Mock deliverable 1</li><li>Mock deliverable 2</li></ul>",
            "pricing": f"<h3>Pricing</h3><p>Mock pricing structure for {project_name}. Actual pricing would be phase and context specific.</p>"
        }
        
        return mock_blocks.get(block_type, f"<h3>{block_type.title()}</h3><p>Mock {block_type} content for {project_name}.</p>")

    def _generate_mock_validation(
        self,
        content: str,
        requirements: Dict[str, Any],
        phase: str
    ) -> Dict[str, Any]:
        """Generate mock validation results when OpenAI is not available."""
        logger.info("Generating mock validation results (OpenAI not configured)")
        
        return {
            "status": "warning",
            "score": 85,
            "issues": [
                {
                    "issue_type": "completeness",
                    "severity": "medium",
                    "description": "Mock validation issue - some sections may need expansion",
                    "suggestion": "Add more detail to scope section",
                    "section": "scope"
                }
            ],
            "recommendations": [
                "Review technical requirements section",
                "Clarify project timeline",
                "Add risk mitigation strategies"
            ],
            "phase_alignment": {
                "appropriate": True,
                "notes": f"Content appears suitable for {phase} phase",
                "score": 90
            },
            "completeness_score": 80
        }

    def _generate_mock_phase_update(
        self,
        current_content: str,
        new_phase: str,
        project_name: str
    ) -> str:
        """Generate mock phase update when OpenAI is not available."""
        logger.info(f"Generating mock phase update for {new_phase} (OpenAI not configured)")
        
        phase_marker = f"<!-- Updated for {new_phase} phase -->"
        updated_content = phase_marker + "\n" + current_content
        
        # Add phase-specific section
        phase_section = f"""
        <section class="phase-update">
            <h3>{new_phase.title()} Phase Focus</h3>
            <p>This proposal has been updated for the {new_phase} phase of {project_name}. 
            In a production environment, AI would intelligently adapt content, timeline, 
            and deliverables to match {new_phase} phase requirements.</p>
        </section>
        """
        
        return updated_content + phase_section 