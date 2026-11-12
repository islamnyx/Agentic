# Architecture — Company Brain (Knowledge Base)

Shared knowledge layer that holds company documents and procedures, products and pricing, customer information, business rules, internal knowledge, and department-specific information.

## Components

- **knowledge_items** — documents, procedures, products, pricing, customer info, business rules, internal knowledge
- **knowledge_access** — per-item access permissions (read/write) scoped to organization, department, team, or agent
- **Ingestion pipeline** — document import, chunking, embedding (optional), ACL tagging at ingest time
- **Knowledge query API** — retrieval with ACL enforcement applied before results returned

## Security principle

Access permissions apply to the knowledge itself, enforced outside the language model. An agent working for Sales must not automatically access confidential HR or finance information. Default deny: a knowledge item is invisible unless the requesting agent's department/team/agent is explicitly granted access.

## Links

- Parent: [[modules]]
- Strategy: [[../../../../planning/product/capabilities]]
- Data model: [[../../data-model]]
