# Access Control Matrix

| Role | Bronze | Silver | Gold detail | Aggregates/BI | Models | Governance register | Approval rights |
|---|---:|---:|---:|---:|---:|---:|---|
| Executive / Category Director | — | — | — | Read | — | Read summary | None |
| Demand Planner | — | Read | Read (assigned categories) | Read | Read forecast output | Create override | Approve store-level replenishment |
| Inventory Analyst | — | Read | Read | Read | Read | Read | Recommend safety-stock changes |
| Supply Chain Manager | — | Read | Read | Read | Read | Manage | Approve supplier and warehouse actions |
| Data Scientist / Model Developer | Read | Read | Read | Read | Develop | Read | Submit model change |
| Model Validator | Read | Read | Read | Read | Validate | Read | Recommend promotion |
| Data Engineer | Write | Write | Write | Write | Deploy artifact | Technical update | Deploy approved release |
| Governance / Data Steward | Read | Read | Read | Read | Read | Manage | Approve master-data changes |
| Auditor | Read logged | Read logged | Read logged | Read | Read | Read | None |

Production access follows least privilege: role-based access control, managed identities and single sign-on, multi-factor authentication for elevated roles, quarterly access recertification, and separation of duties between model development, validation and production approval. Row-level security scopes demand planners and inventory analysts to their assigned regions or categories. All write access to gold tables and model artifacts is via the pipeline service identity only - no interactive user has direct write access to gold or the model registry, preventing undocumented manual edits to published metrics.
