# System Architecture & Technical Design

## High-Level Architecture
```
[Frontend (React)] <-> [Backend (FastAPI)] <-> [Database (PostgreSQL/Redis)]
                                 |
                        [AI/LLM Services]
                                 |
                        [External Integrations]
```

## Component/Module Breakdown
- Frontend: Dashboard, Knowledge Base, Proposal Editor, Timeline, Integrations, Auth
- Backend: API, Auth, Knowledge Processing, Proposal Engine, Timeline/Deliverables, Integrations, Audit
- AI/LLM: Summarization, Tagging, Proposal Generation, Q&A
- Integrations: Notion, Email, Docs, Custom APIs

## Data Flow
- User uploads/ingests data -> Backend processes & stores -> AI refines & tags -> Frontend displays/searches/uses

## Integration Points
- API endpoints for all major features
- Modular integration registry for future services 