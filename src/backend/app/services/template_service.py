"""
Template Service for proposal template management.
Handles template loading, processing, and content injection.
"""

import os
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import logging

# Configure logging
logger = logging.getLogger(__name__)


class TemplateServiceError(Exception):
    """Custom exception for template service errors."""
    pass


class TemplateService:
    """
    Service for managing proposal templates.
    Handles template loading, variable substitution, and content generation.
    """

    def __init__(self):
        """Initialize template service."""
        self.template_dir = Path("project-assets/templates")
        self.default_template = "jda_proposal_template.html"
        
        # Ensure template directory exists
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default template if not exists
        self._ensure_default_template()

    def load_template(self, template_name: str = None) -> str:
        """
        Load template content from file.
        
        Args:
            template_name: Name of template file (optional, defaults to JDA template)
            
        Returns:
            Template HTML content
        """
        try:
            template_name = template_name or self.default_template
            template_path = self.template_dir / template_name
            
            if not template_path.exists():
                logger.warning(f"Template {template_name} not found, using default")
                return self._get_default_template()
            
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Loaded template: {template_name}")
            return content
            
        except Exception as e:
            logger.error(f"Error loading template: {str(e)}")
            raise TemplateServiceError(f"Failed to load template: {str(e)}")

    def render_proposal(
        self,
        project_name: str,
        client_name: str,
        phase: str,
        requirements: Dict[str, Any],
        ai_content: str,
        template_name: str = None
    ) -> str:
        """
        Render complete proposal using template and content.
        
        Args:
            project_name: Name of the project
            client_name: Client company name
            phase: Project phase
            requirements: Extracted requirements
            ai_content: AI-generated proposal content
            template_name: Template to use (optional)
            
        Returns:
            Rendered proposal HTML
        """
        try:
            # Load template
            template = self.load_template(template_name)
            
            # Prepare template variables
            template_vars = self._prepare_template_variables(
                project_name, client_name, phase, requirements, ai_content
            )
            
            # Render template
            rendered = self._substitute_variables(template, template_vars)
            
            logger.info(f"Rendered proposal for project: {project_name}")
            return rendered
            
        except Exception as e:
            logger.error(f"Error rendering proposal: {str(e)}")
            raise TemplateServiceError(f"Failed to render proposal: {str(e)}")

    def inject_ai_content(
        self,
        template: str,
        ai_content: str,
        section: str = "content"
    ) -> str:
        """
        Inject AI-generated content into template section.
        
        Args:
            template: Template HTML
            ai_content: AI-generated content
            section: Section name to inject into
            
        Returns:
            Template with injected content
        """
        try:
            # Define injection points
            injection_patterns = {
                "content": r'<!--\s*AI_CONTENT\s*-->',
                "summary": r'<!--\s*AI_SUMMARY\s*-->',
                "scope": r'<!--\s*AI_SCOPE\s*-->',
                "deliverables": r'<!--\s*AI_DELIVERABLES\s*-->',
                "timeline": r'<!--\s*AI_TIMELINE\s*-->'
            }
            
            pattern = injection_patterns.get(section, injection_patterns["content"])
            
            # Inject content
            if re.search(pattern, template):
                result = re.sub(pattern, ai_content, template)
                logger.info(f"Injected AI content into section: {section}")
                return result
            else:
                # If no injection point found, append to end of body
                logger.warning(f"No injection point found for section: {section}")
                body_end = "</body>"
                if body_end in template:
                    return template.replace(
                        body_end, 
                        f'<div class="ai-generated-content">{ai_content}</div>\n{body_end}'
                    )
                else:
                    return template + f'\n<div class="ai-generated-content">{ai_content}</div>'
            
        except Exception as e:
            logger.error(f"Error injecting AI content: {str(e)}")
            raise TemplateServiceError(f"Failed to inject AI content: {str(e)}")

    def customize_template(
        self,
        template: str,
        customizations: Dict[str, Any]
    ) -> str:
        """
        Apply customizations to template.
        
        Args:
            template: Template HTML
            customizations: Customization options
            
        Returns:
            Customized template
        """
        try:
            result = template
            
            # Apply color scheme
            if "colors" in customizations:
                colors = customizations["colors"]
                for color_var, color_value in colors.items():
                    result = result.replace(f"var(--{color_var})", color_value)
            
            # Apply branding
            if "branding" in customizations:
                branding = customizations["branding"]
                if "logo_url" in branding:
                    result = result.replace("{{COMPANY_LOGO}}", branding["logo_url"])
                if "company_name" in branding:
                    result = result.replace("{{COMPANY_NAME}}", branding["company_name"])
            
            # Apply layout options
            if "layout" in customizations:
                layout = customizations["layout"]
                if layout.get("hide_sidebar"):
                    result = re.sub(r'<aside[^>]*>.*?</aside>', '', result, flags=re.DOTALL)
            
            logger.info("Applied template customizations")
            return result
            
        except Exception as e:
            logger.error(f"Error customizing template: {str(e)}")
            raise TemplateServiceError(f"Failed to customize template: {str(e)}")

    def _prepare_template_variables(
        self,
        project_name: str,
        client_name: str,
        phase: str,
        requirements: Dict[str, Any],
        ai_content: str
    ) -> Dict[str, str]:
        """Prepare variables for template substitution."""
        
        # Extract specific requirements
        scope = requirements.get('scope', 'Project scope to be defined')
        timeline = requirements.get('timeline', 'Timeline to be discussed')
        deliverables = requirements.get('deliverables', [])
        budget_range = requirements.get('budget_range', 'Budget to be determined')
        
        # Format deliverables as HTML list
        deliverables_html = ""
        if deliverables:
            deliverables_html = "<ul>"
            for deliverable in deliverables:
                deliverables_html += f"<li>{deliverable}</li>"
            deliverables_html += "</ul>"
        else:
            deliverables_html = "<p>Deliverables to be defined based on detailed requirements.</p>"
        
        return {
            "PROJECT_NAME": project_name,
            "CLIENT_NAME": client_name,
            "PROJECT_PHASE": phase.title(),
            "CURRENT_DATE": datetime.now().strftime("%B %d, %Y"),
            "PROJECT_SCOPE": scope,
            "PROJECT_TIMELINE": timeline,
            "PROJECT_DELIVERABLES": deliverables_html,
            "BUDGET_RANGE": budget_range,
            "AI_GENERATED_CONTENT": ai_content,
            "PROPOSAL_VERSION": "1.0",
            "COMPANY_NAME": "JDA Digital Agency",
            "COMPANY_LOGO": "/assets/jda-logo.png"
        }

    def _substitute_variables(self, template: str, variables: Dict[str, str]) -> str:
        """Substitute template variables with actual values."""
        result = template
        
        for var_name, var_value in variables.items():
            # Replace both {{VAR}} and {{VAR_NAME}} formats
            patterns = [
                f"{{{{{var_name}}}}}",
                f"{{{{ {var_name} }}}}"
            ]
            
            for pattern in patterns:
                result = result.replace(pattern, str(var_value))
        
        return result

    def _ensure_default_template(self):
        """Ensure default JDA template exists."""
        template_path = self.template_dir / self.default_template
        
        if not template_path.exists():
            logger.info("Creating default JDA proposal template")
            default_content = self._get_default_template()
            
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(default_content)

    def _get_default_template(self) -> str:
        """Get default JDA proposal template content."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{PROJECT_NAME}} - Proposal</title>
    <style>
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --accent-color: #e74c3c;
            --text-color: #333;
            --light-bg: #f8f9fa;
            --border-color: #ddd;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background: #fff;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: var(--primary-color);
            color: white;
            padding: 40px 0;
            margin-bottom: 40px;
        }
        
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        .logo {
            font-size: 24px;
            font-weight: bold;
        }
        
        .proposal-info {
            text-align: right;
        }
        
        .proposal-title {
            font-size: 36px;
            font-weight: bold;
            text-align: center;
            margin: 40px 0;
            color: var(--primary-color);
        }
        
        .client-info {
            background: var(--light-bg);
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 40px;
            border-left: 4px solid var(--secondary-color);
        }
        
        .section {
            margin-bottom: 40px;
            padding: 30px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
        }
        
        .section h2 {
            color: var(--primary-color);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--secondary-color);
        }
        
        .section h3 {
            color: var(--secondary-color);
            margin: 20px 0 15px 0;
        }
        
        .deliverables-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .deliverable-card {
            background: var(--light-bg);
            padding: 20px;
            border-radius: 6px;
            border-left: 3px solid var(--accent-color);
        }
        
        .timeline-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        .timeline-table th,
        .timeline-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        .timeline-table th {
            background: var(--primary-color);
            color: white;
        }
        
        .cta-section {
            background: var(--secondary-color);
            color: white;
            padding: 40px;
            text-align: center;
            border-radius: 8px;
            margin-top: 40px;
        }
        
        .footer {
            background: var(--primary-color);
            color: white;
            text-align: center;
            padding: 30px 0;
            margin-top: 60px;
        }
        
        @media (max-width: 768px) {
            .header-content {
                flex-direction: column;
                gap: 20px;
            }
            
            .proposal-title {
                font-size: 28px;
            }
            
            .container {
                padding: 10px;
            }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo">{{COMPANY_NAME}}</div>
            <div class="proposal-info">
                <div>Date: {{CURRENT_DATE}}</div>
                <div>Version: {{PROPOSAL_VERSION}}</div>
                <div>Phase: {{PROJECT_PHASE}}</div>
            </div>
        </div>
    </header>

    <div class="container">
        <h1 class="proposal-title">Project Proposal: {{PROJECT_NAME}}</h1>
        
        <div class="client-info">
            <h2>Client Information</h2>
            <p><strong>Client:</strong> {{CLIENT_NAME}}</p>
            <p><strong>Project:</strong> {{PROJECT_NAME}}</p>
            <p><strong>Phase:</strong> {{PROJECT_PHASE}}</p>
            <p><strong>Date:</strong> {{CURRENT_DATE}}</p>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <!-- AI_SUMMARY -->
            <p>This proposal outlines our approach for the {{PROJECT_NAME}} project in the {{PROJECT_PHASE}} phase. 
            Our team at {{COMPANY_NAME}} is excited to partner with {{CLIENT_NAME}} to deliver exceptional results.</p>
        </div>

        <div class="section">
            <h2>Project Scope</h2>
            <!-- AI_SCOPE -->
            <p>{{PROJECT_SCOPE}}</p>
        </div>

        <div class="section">
            <h2>Deliverables</h2>
            <!-- AI_DELIVERABLES -->
            {{PROJECT_DELIVERABLES}}
        </div>

        <div class="section">
            <h2>Timeline</h2>
            <!-- AI_TIMELINE -->
            <p><strong>Proposed Timeline:</strong> {{PROJECT_TIMELINE}}</p>
            <p>Detailed timeline and milestones will be finalized during the project kickoff phase.</p>
        </div>

        <div class="section">
            <h2>Investment</h2>
            <p><strong>Budget Range:</strong> {{BUDGET_RANGE}}</p>
            <p>Final pricing will be provided upon completion of detailed requirements analysis.</p>
        </div>

        <div class="section">
            <h2>AI-Generated Analysis</h2>
            <!-- AI_CONTENT -->
            {{AI_GENERATED_CONTENT}}
        </div>

        <div class="section">
            <h2>Next Steps</h2>
            <ol>
                <li>Review and approve this proposal</li>
                <li>Schedule project kickoff meeting</li>
                <li>Finalize detailed requirements and timeline</li>
                <li>Begin {{PROJECT_PHASE}} phase activities</li>
            </ol>
        </div>

        <div class="cta-section">
            <h2>Ready to Get Started?</h2>
            <p>We're excited to partner with {{CLIENT_NAME}} on this project.</p>
            <p>Contact us to discuss next steps and begin this exciting journey together.</p>
        </div>
    </div>

    <footer class="footer">
        <div class="container">
            <p>&copy; 2024 {{COMPANY_NAME}}. All rights reserved.</p>
            <p>Professional services delivered with excellence.</p>
        </div>
    </footer>
</body>
</html>""" 