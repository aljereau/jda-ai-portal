--
title: Development Rules & Workflow Standards (Master Rule)
description: This master rule outlines the overarching development processes, standards, and references specific granular rules for AI-driven project execution.
tags: meta-rule, workflow, development-process, project-governance, ai-automation, cursor
---
 Development Rules & Workflow Standards (Master Rule)
 I. Rule Metadata (Frontmatter)

```yaml
---
ruleId: "dev-workflow-master-001"
description: "Master rule referencing and enforcing overall development workflow, standards, and documentation practices for AI-driven project execution."
severity: "INFO" # This master rule is informational; specific sub-rules will have their own severities.
globs: "" # Applies to the whole project conceptually.
alwaysApply: true
tags: ["workflow", "standards", "process", "documentation", "master-rule", "ai-governance"]
relatedRules: [
  # Foundational Setup & Governance
  "initial-project-structure-definition-001",
  "universal-project-structure-governance-001",
  "visual-folder-enhancement-optional-001",
  # Workflow & Process
  "phase-completion-before-next-001",
  "phase-objective-validation-001",
  "scope-drift-prevention-001",
  "component-validation-before-advancement-001",
  "validation-evidence-documentation-001",
  "issue-blocker-immediate-logging-001",
  "technical-debt-logging-format-001",
  # Code Quality & Style
  "code-quality-pep8-python-001", # Example, create language-specific versions as needed
  "code-quality-typehints-python-001", # Example
  "code-docstring-standard-python-001", # Example
  "commit-atomicity-principle-001",
  "enhanced-logging-practices-001", # Inspired by debugging framework
  "code-annotation-best-practices-001", # Inspired by debugging framework
  # Architecture & Integrity
  "backend-integrity-no-direct-modification-001",
  "backend-service-layer-wrappers-001",
  "function-contract-assertion-generation-001", # Inspired by debugging framework
  "api-parameter-validation-at-entry-001", # Inspired by debugging framework
  "consistent-error-typing-001", # Inspired by debugging framework
  "filesystem-path-validation-001", # Inspired by debugging framework
  # Testing & Validation
  "automated-test-requirements-001",
  "test-driven-development-adherence-001",
  "backend-cli-compatibility-check-001",
  "ui-component-user-validation-prompt-001",
  "regression-testing-execution-001",
  "edge-case-test-creation-and-documentation-001",
  "performance-test-requirements-001",
  "ui-responsiveness-check-001",
  "api-client-error-handling-standard-001", # Inspired by debugging framework
  "api-response-validation-001", # Inspired by debugging framework
  # Version Control & CI_CD
  "branching-strategy-feature-format-001",
  "commit-standard-format-001",
  "no-direct-commits-main-protected-001",
  "pr-mr-required-for-integration-001",
  "ci-cd-pass-required-for-merge-001",
  # Documentation
  "readme-update-per-phase-001",
  "technical-doc-update-milestones-001",
  "component-readme-content-standard-001",
  "bugfix-documentation-standard-001", # Inspired by debugging framework
  "root-cause-causality-chain-documentation-001", # Inspired by debugging framework
  # Patching
  "patch-implementation-guidelines-001" # Inspired by debugging framework
]
autoFixable: "NONE"
version: "1.2"
lastUpdated: "2024-12-22"
---
```

 II. Rule Definition & Explanation

 A. Rule Overview & Rationale

- **Purpose:** To establish a consistent, high-quality, and well-documented development process for all projects executed with AI (Cursor) assistance. This ensures predictability, maintainability, and adherence to best practices while preventing critical issues like scope drift and file organization problems.
- **Rationale/Benefit:** A standardized workflow minimizes errors, improves collaboration (even with AI), ensures deliverables meet quality standards, and makes the project easier to understand and maintain over time. This master rule serves as an index to specific, actionable standards and includes enhanced governance to prevent project management failures.

 B. Core Development Principles (Referenced & Enforced by Specific Rules)

*(This section outlines the high-level principles. Each principle is enforced by one or more specific, granular rule files linked in relatedRules and explicitly mentioned below.)*

1. **Universal Project Structure & File Organization:**
    - ALL projects follow the same universal core structure (12 folders) regardless of domain, technology, or editor. File structures are strictly governed with universal core + domain-specific extensions, preventing confusion and maintaining system integrity across ALL future projects.
    - **Key Supporting Rules:** @initial-project-structure-definition-001.mdc, **@universal-project-structure-governance-001.mdc**. *(Project initiation and overview are guided by their respective templates: @project-initiation-scope-definition-template.mdc, @project-overview-template.mdc)*.

2. **Phased & Sequential Development Workflow with Objective Validation:**
    - Projects are executed in clearly defined, sequential phases with **mandatory objective validation** to prevent scope drift. All development work must align with original phase objectives, and regular validation checkpoints ensure we build what was planned.
    - **Key Supporting Rules:** @phase-completion-before-next-001.mdc, **@phase-objective-validation-001.mdc**, **@scope-drift-prevention-001.mdc**. *(Detailed phase planning uses @enhanced-project-phase-template.mdc)*.

3. **Comprehensive Validation & Rigorous Testing:**
    - Components and features must be rigorously validated with automated tests, edge case considerations, TDD practices where applicable, and user-centric checks. Evidence of validation is mandatory.
    - **Key Supporting Rules:** @component-validation-before-advancement-001.mdc, @validation-evidence-documentation-001.mdc, @automated-test-requirements-001.mdc, @test-driven-development-adherence-001.mdc, @edge-case-test-creation-and-documentation-001.mdc, @regression-testing-execution-001.mdc, @backend-cli-compatibility-check-001.mdc, @ui-component-user-validation-prompt-001.mdc, @performance-test-requirements-001.mdc, @ui-responsiveness-check-001.mdc.

4. **High Code Quality, Style & Maintainability:**
    - Code must adhere to defined style guides (e.g., PEP 8), include type hints and comprehensive docstrings, and aim for clarity and maintainability. Logging should be robust and insightful annotations used where beneficial. Potential technical debt should be identified and logged.
    - **Key Supporting Rules:** @code-quality-pep8-python-001.mdc (and equivalents for other languages), @code-quality-typehints-python-001.mdc (and equivalents), @code-docstring-standard-python-001.mdc (and equivalents), @enhanced-logging-practices-001.mdc, @code-annotation-best-practices-001.mdc, @technical-debt-logging-format-001.mdc.

5. **Architectural Integrity & Robust Design:**
    - Core system integrity (e.g., backend code) must be preserved. Interactions should occur via defined interfaces like service layers. Function contracts, robust parameter validation, consistent error typing, and safe file system operations are crucial. API interactions must be handled resiliently.
    - **Key Supporting Rules:** @backend-integrity-no-direct-modification-001.mdc, @backend-service-layer-wrappers-001.mdc, @function-contract-assertion-generation-001.mdc, @api-parameter-validation-at-entry-001.mdc, @consistent-error-typing-001.mdc, @filesystem-path-validation-001.mdc, @api-client-error-handling-standard-001.mdc, @api-response-validation-001.mdc, @threading-resource-cleanup-001.mdc.

6. **Standardized Version Control & Integration Practices:**
    - Adherence to defined branching strategies, atomic and well-formatted commit messages, and Pull/Merge Request processes (ideally with CI/CD checks) is mandatory for integrating code into protected branches.
    - **Key Supporting Rules:** @branching-strategy-feature-format-001.mdc, @commit-standard-format-001.mdc, @commit-atomicity-principle-001.mdc, @no-direct-commits-main-protected-001.mdc, @pr-mr-required-for-integration-001.mdc, @ci-cd-pass-required-for-merge-001.mdc.

7. **Consistent & Timely Documentation:**
    - Project, phase, and component documentation must be kept up-to-date with development progress. This includes READMEs, technical design documents, and comprehensive bug fix records.
    - **Key Supporting Rules:** @readme-update-per-phase-001.mdc, @technical-doc-update-milestones-001.mdc, @component-readme-content-standard-001.mdc, @bugfix-documentation-standard-001.mdc, @root-cause-causality-chain-documentation-001.mdc.

8. **Systematic Issue, Bug, & Patch Management:**
    - Issues and blockers are logged immediately. Bug fixes follow a robust process including root cause analysis and thorough validation. Patches are implemented carefully to minimize side effects.
    - **Key Supporting Rules:** @issue-blocker-immediate-logging-001.mdc, @one-shot-debugging-guarantee-system-guide.mdc (as the guiding methodology), @patch-implementation-guidelines-001.mdc.

 C. Documentation System & Workflow Adherence

- The AI Executor (Cursor) must utilize the established project documentation templates for planning and tracking:
    - @project-initiation-scope-definition-template.mdc (for initial scoping)
    - @project-overview-template.mdc (for overall project plan)
    - @enhanced-project-phase-template.mdc (for detailed phase definitions)
    - @ai-driven-phase-progress-tracking-template.mdc (for logging phase execution)
- The AI is expected to follow the operational workflows described in the "Working with the AI-Driven Development System in Cursor (Structured Method)" guide (typically the main README.md of this system).

 D. Examples of Compliance (✅ DO)

- AI Executor (Cursor) successfully plans and completes a project phase, with the @[PhaseName]-Progress.mdc document fully populated, all DoD items met, and all relevant granular rules (e.g., for testing, code style, commits specified in Section II.B above) adhered to during code generation and task execution.
- **AI validates all development work against original phase objectives before proceeding** (following @phase-objective-validation-001.mdc).
- **AI maintains universal project structure** with consistent 12-folder core + domain extensions across ALL project types and technologies (following @universal-project-structure-governance-001.mdc).
- When an error occurs, AI consults @one-shot-debugging-guarantee-system-guide.mdc and applies its principles, logging the issue via @issue-blocker-immediate-logging-001.mdc and documenting the fix as per @bugfix-documentation-standard-001.mdc.

 E. Examples of Non-Compliance (❌ DON'T / Anti-Patterns)

- AI Executor (Cursor) generates Python code that fails PEP 8 checks and does not attempt to auto-format or address the issues (violates referenced @code-quality-pep8-python-001.mdc).
- AI Executor (Cursor) commits code directly to the main branch without a Pull Request (violates referenced @no-direct-commits-main-protected-001.mdc).
- AI Executor (Cursor) proceeds to a new phase before the previous phase's Definition of Done is met (violates referenced @phase-completion-before-next-001.mdc).
- **AI builds features not defined in original phase objectives without explicit validation and approval** (violates @phase-objective-validation-001.mdc and @scope-drift-prevention-001.mdc).
- **AI places project progress files in development rules folders** (violates @file-structure-governance-001.mdc).
- **AI uses inconsistent project structure across different project types** (violates @universal-project-structure-governance-001.mdc).

 F. Automated Correction Logic / Suggestions

- Not directly applicable at this master rule level. Specific granular rules linked in relatedRules define their own autoFixable properties and correction logic. This master rule serves to ensure Cursor is *aware* of the entire suite of standards it must consult and adhere to.

 III. Rule Maintenance Log

- **2024-12-22** - v1.2 - Claude-Sonnet-4-Session-20241222: **CRITICAL GOVERNANCE ENHANCEMENT** - Added file-structure-governance-001.mdc, phase-objective-validation-001.mdc, and scope-drift-prevention-001.mdc to address major project management failures discovered during Phase 1. Enhanced principles 1 and 2 to emphasize file organization and objective validation requirements. This update prevents scope drift and file organization issues that caused significant resource waste.
- **[YYYY-MM-DD] - v1.1 - [Your Name/AI Session ID]:** Significantly updated relatedRules to include a comprehensive list of defined granular rules and those derived from the debugging framework. Reorganized and refined "Core Development Principles" to better map to rule categories and explicitly reference key supporting rules.
- **[YYYY-MM-DD] - v1.0 - [Your Name/AI Session ID]:** Initial creation of the master development workflow standards rule.