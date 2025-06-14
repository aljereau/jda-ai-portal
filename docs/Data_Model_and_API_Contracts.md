# Data Model & API Contracts

## Data Models (ERD-style)
```
[User]---<owns>---[Environment]---<has>---[Integration]
   |                                 |
<uploads>                        <contains>
   |                                 |
[KnowledgeItem]---<refines>---[RefinedDoc]
   |                                 |
<generates>                      <tracks>
   |                                 |
[Proposal]---<has>---[Timeline/Deliverable]
```

## API Endpoint Contracts

### Example: Upload Knowledge Item
- **POST /api/knowledge/upload**
  - Request: file, tags, source_type, environment_id
  - Response: { id, status, ai_tags, refined_doc_id }

### Example: Generate Proposal
- **POST /api/proposals/generate**
  - Request: { environment_id, section_inputs, use_ai }
  - Response: { proposal_id, content, status }

### Auth & Errors
- All endpoints require JWT auth
- Standard error format: { error_code, message } 