# 🤖 Cursor AI Development System - Auto-Setup Guide

**Purpose**: This file guides Cursor to automatically set up the complete AI Development System in any new project.

## 📋 SETUP CHECKLIST FOR CURSOR

When you copy this repo structure to a new project, follow these steps **IN ORDER**:

### STEP 1: Create Rules Folder Structure
```bash
# Create the rules folder
mkdir rules

# Verify the AI Development_system folder exists
ls -la | grep "AI Development_system"
```

### STEP 2: Copy All Rule Files to ./rules
```powershell
# Copy all .mdc rule files
Get-ChildItem -Path 'AI Development_system' -Filter '*.mdc' -Recurse | Copy-Item -Destination 'rules' -Force

# Copy all .md rule files  
Get-ChildItem -Path 'AI Development_system' -Filter '*.md' -Recurse | Copy-Item -Destination 'rules' -Force

# Verify all files copied successfully
Get-ChildItem rules | Measure-Object | Select-Object Count
# Should show 40+ files
```

### STEP 3: Create .cursorrules File
Create `.cursorrules` file with the complete Universal AI-Driven Development System configuration including:

- **Universal Project Structure** (12-folder core system)
- **Phased Development with Objective Validation**
- **Code Quality Standards** (PEP 8, type hints, docstrings)
- **Testing & Validation Requirements**
- **Architectural Integrity Rules**
- **Version Control Practices**
- **Documentation Standards**
- **Master Workflow System** with 8 core principles
- **Context-Aware Rule Application**

### STEP 4: Verify Setup Complete
```powershell
# Check rules folder has files
Get-ChildItem rules | Select-Object -First 10

# Check .cursorrules exists
Test-Path .cursorrules

# Verify AI Development_system still exists
Test-Path "AI Development_system"
```

### STEP 5: Update Project README
Add AI Development System integration section to README.md explaining the rule system.

## 🎯 POST-SETUP VALIDATION

After completing setup, verify these exist:
- ✅ `./rules/` folder with 40+ rule files
- ✅ `.cursorrules` file with master workflow system
- ✅ `AI Development_system/` folder (original source)
- ✅ Updated README.md (if applicable)

## 🚀 USAGE INSTRUCTIONS FOR CURSOR

**Cursor will now automatically:**
1. **Select context-appropriate rules** based on development task
2. **Follow 8 core development principles** with mapped rule files
3. **Apply proper templates** for project phases and planning
4. **Prevent scope drift** through objective validation
5. **Maintain architectural integrity** across all code changes

**Key Files Cursor References:**
- `./rules/dev-workflow-master-001.md` - Master orchestration system
- `./rules/phase-objective-validation-001.mdc` - Prevents scope drift
- `./rules/universal-project-structure-governance-001.mdc` - Structure consistency
- `.cursorrules` - Main rule file with context-aware selection

## 📚 RULE SYSTEM OVERVIEW

**Total Rules**: 40+ comprehensive development rules
**Categories**: 8 core principle areas  
**Templates**: Project planning and phase tracking
**Automation**: Context-aware rule selection
**Governance**: Objective validation and scope control

This setup provides enterprise-level development standards with AI-driven automation for consistent, high-quality project execution.

---

**Next Steps**: Start your project development following the established templates and let Cursor guide you through the workflow!

## 📋 DETAILED AUTOMATION INSTRUCTIONS FOR CURSOR

### STEP 3A: Complete .cursorrules Template
Copy this EXACT content into `.cursorrules` file:

```
# 🤖 Universal AI-Driven Development System - Cursor Rules
# Integrated from: https://github.com/aljereau/CursorRulesAljereau

## UNIVERSAL PROJECT STRUCTURE
- Follow 12-folder core structure: project-planning/, project-requirements/, project-documentation/, project-architecture/, project-environments/, project-quality/, project-deployment/, project-monitoring/, project-security/, project-research/, project-assets/, project-integrations/
- Add domain-specific extensions only when needed
- Maintain consistent structure across ALL project types and technologies

## PHASED DEVELOPMENT & OBJECTIVE VALIDATION
- Execute projects in clearly defined sequential phases
- MANDATORY validation against original phase objectives before proceeding
- Prevent scope drift through regular validation checkpoints
- Document phase progress in appropriate tracking files

## CODE QUALITY STANDARDS
- Follow language-specific style guides (PEP 8 for Python, etc.)
- Include comprehensive docstrings and type hints
- Use meaningful naming conventions (camelCase for JS, snake_case for Python)
- Implement robust logging with appropriate levels
- Document technical debt when identified

## TESTING & VALIDATION REQUIREMENTS
- Write automated tests for all components
- Apply TDD practices where applicable
- Test edge cases and error conditions
- Perform regression testing before releases
- Document validation evidence

## ARCHITECTURAL INTEGRITY
- Preserve core system integrity - no direct backend modifications
- Use service layer wrappers for interactions
- Implement function contracts and parameter validation
- Consistent error typing and handling
- Safe filesystem operations with validation

## VERSION CONTROL PRACTICES
- Use atomic commits with clear, descriptive messages
- Follow feature branch strategy
- No direct commits to protected main branch
- Require Pull/Merge Requests for integration
- Ensure CI/CD checks pass before merging

## DOCUMENTATION STANDARDS
- Keep README files updated with each phase
- Maintain technical documentation at milestones
- Document component functionality and usage
- Record bug fixes with root cause analysis
- Use established project templates

## ERROR HANDLING & DEBUGGING
- Apply systematic debugging approach
- Log errors with sufficient context
- Include correlation IDs in API responses
- Validate inputs at entry points
- Handle async operations properly

## AI COLLABORATION GUIDELINES
- Reference existing templates before creating new files
- Use established project phase templates for planning
- Follow Universal AI-Driven Development System methodology
- Validate work against defined acceptance criteria
- Maintain consistency with existing codebase patterns

## SPECIFIC RULES

### File & Folder Naming
- Use consistent naming conventions across all projects
- Prefer kebab-case for folder names in most contexts
- Use descriptive names that clearly indicate purpose
- Include version numbers in rule files (e.g., -001, -002)

### Code Generation Guidelines
- Always include necessary imports and dependencies
- Generate complete, runnable code examples
- Include error handling in all functions
- Add appropriate comments and documentation
- Consider performance implications

### Template Usage
- Use project-initiation-scope-definition-template.mdc for initial scoping
- Use project-overview-template.mdc for overall project planning
- Use enhanced-project-phase-template.mdc for detailed phase definitions  
- Use ai-driven-phase-progress-tracking-template.mdc for execution tracking

### Security Practices
- Validate all user inputs
- Use parameterized queries for database operations
- Implement proper authentication and authorization
- Store sensitive data securely
- Follow security best practices for the target platform

## LANGUAGE-SPECIFIC RULES

### Python
- Follow PEP 8 style guidelines strictly
- Use type hints for all function parameters and return values
- Include comprehensive docstrings following Google/NumPy style
- Use meaningful variable names in snake_case
- Implement proper exception handling

### JavaScript/TypeScript
- Use camelCase for variables and functions
- Prefer const over let, avoid var
- Use TypeScript interfaces for object structures
- Implement proper async/await patterns
- Handle promises and errors appropriately

### General Programming
- Write self-documenting code with clear intent
- Avoid deep nesting - prefer early returns
- Use meaningful function and variable names
- Keep functions small and focused on single responsibility
- Comment complex logic and business rules

## QUALITY GATES

### Before Phase Completion
- All tests passing
- Code review completed
- Documentation updated
- Performance requirements met
- Security scan passed

### Before Release
- All acceptance criteria met
- User validation completed
- Regression tests passed
- Documentation finalized
- Deployment procedures validated

## AUTOMATION & TOOLING

### Code Formatting
- Auto-format code using appropriate tools (Black for Python, Prettier for JS/TS)
- Configure pre-commit hooks for quality checks
- Use linters to enforce style guidelines
- Validate code against defined standards

### Testing Automation
- Run unit tests on every commit
- Execute integration tests in CI/CD pipeline
- Perform automated security scans
- Generate test coverage reports

## CONTINUOUS IMPROVEMENT

### Rule Evolution
- Update rules based on project learnings
- Version control all rule changes
- Document rationale for rule modifications
- Review and refine rules regularly

### Knowledge Capture
- Document lessons learned from each project
- Share best practices across teams
- Update templates based on experience
- Maintain knowledge base of solutions

# These rules ensure consistent, high-quality development practices across all projects
# while maintaining flexibility for different domains and technologies. 

## MASTER WORKFLOW SYSTEM
# Based on dev-workflow-master-001.md - AI-Driven Development Rule Orchestration
# The ./rules folder contains the complete rule ecosystem for systematic development execution

### CORE DEVELOPMENT PRINCIPLES
Follow these 8 principles with their corresponding rule files from ./rules folder:

**1. Universal Project Structure & File Organization**
   - ALL projects follow 12-folder core structure regardless of domain/technology  
   - **Key Rules**: `universal-project-structure-governance-001.mdc`, `initial-project-structure-definition-001.mdc`
   - **Templates**: `project-initiation-scope-definition.mdc`, `Project Overview Template.mdc`

**2. Phased & Sequential Development with Objective Validation**
   - MANDATORY validation against original phase objectives to prevent scope drift
   - **Key Rules**: `phase-objective-validation-001.mdc`, `scope-drift-prevention-001.mdc`, `phase-completion-before-next-001.mdc`
   - **Templates**: `enhanced-project-phase-template.mdc`, `AI-Driven Phase Progress Tracking-001.mdc`

**3. Comprehensive Validation & Rigorous Testing**
   - Components validated with automated tests, edge cases, TDD practices
   - **Key Rules**: `automated-test-requirements-001.mdc`, `test-driven-development-adherence-001.mdc`, `component-validation-before-advancement-001.mdc`, `validation-evidence-documentation-001.mdc`

**4. High Code Quality, Style & Maintainability**
   - Adhere to style guides, type hints, comprehensive docstrings
   - **Key Rules**: `code-quality-pep8-python-001.mdc`, `code-quality-typehints-python-001.mdc`, `code-docstring-standard-python-001.mdc`, `technical-debt-logging-format-001.mdc`

**5. Architectural Integrity & Robust Design**
   - Preserve core system integrity, use service layer wrappers
   - **Key Rules**: `backend-integrity-no-direct-modification-001.mdc`, `backend-service-layer-wrappers-001.mdc`

**6. Standardized Version Control & Integration**
   - Atomic commits, branching strategy, PR/MR processes
   - **Key Rules**: `branching-strategy-feature-format-001.mdc`, `commit-standard-format-001.mdc`, `no-direct-commits-main-protected-001.mdc`, `pr-mr-required-for-integration-001.mdc`

**7. Consistent & Timely Documentation**
   - Keep READMEs, technical docs updated with development progress
   - **Key Rules**: `readme-update-per-phase-001.mdc`, `technical-doc-update-milestones-001.mdc`

**8. Systematic Issue, Bug & Patch Management**
   - Immediate logging, root cause analysis, thorough validation
   - **Key Rules**: `issue-blocker-immediate-logging-001.mdc`, `One-Shot Debugging Guarantee System.mdc`

### AI EXECUTOR WORKFLOW COMPLIANCE

**✅ DO - Examples of Proper Execution:**
- Validate ALL development work against original phase objectives before proceeding
- Maintain universal project structure with 12-folder core + domain extensions
- Use established templates for planning: `project-initiation-scope-definition.mdc`, `enhanced-project-phase-template.mdc`
- Follow debugging methodology from `One-Shot Debugging Guarantee System.mdc`
- Complete Phase Progress documents with all DoD items met

**❌ DON'T - Anti-Patterns to Avoid:**
- Building features not defined in original phase objectives without validation
- Generating code that violates PEP 8 without attempting fixes
- Committing directly to main branch without PR
- Proceeding to new phase before previous DoD completion
- Using inconsistent project structure across project types

### MASTER RULE ORCHESTRATION
- **Primary Reference**: `dev-workflow-master-001.md` (contains complete rule mapping)
- **Documentation Templates**: Use established templates for all planning and tracking
- **Rule Relationships**: Each principle maps to specific supporting rules in ./rules folder
- **Validation Required**: Always validate work against original objectives before advancement

### CONTEXT-AWARE RULE APPLICATION
1. **Project Start**: Universal structure + initiation templates
2. **Phase Planning**: Phase templates + objective validation rules  
3. **Python Development**: PEP8 + type hints + docstring rules
4. **Backend Work**: Integrity + service wrapper rules
5. **Testing**: Automated test + TDD + validation rules
6. **Version Control**: Branching + commit + PR/MR rules
7. **Documentation**: README + technical doc rules
8. **Debugging**: Framework + one-shot debugging rules

This system ensures consistent, high-quality development while preventing scope drift and maintaining architectural integrity across ALL projects.
```

### AUTOMATION SEQUENCE FOR CURSOR
When setting up a new project, execute these commands in sequence:

```powershell
# 1. Create rules folder
New-Item -ItemType Directory -Name "rules" -Force

# 2. Copy all rule files
Get-ChildItem -Path "AI Development_system" -Filter "*.mdc" -Recurse | Copy-Item -Destination "rules" -Force
Get-ChildItem -Path "AI Development_system" -Filter "*.md" -Recurse | Copy-Item -Destination "rules" -Force

# 3. Create .cursorrules file with template above
New-Item -ItemType File -Name ".cursorrules" -Force

# 4. Verify setup
Write-Host "Rules count: $((Get-ChildItem rules).Count)"
Write-Host ".cursorrules exists: $(Test-Path .cursorrules)"
```