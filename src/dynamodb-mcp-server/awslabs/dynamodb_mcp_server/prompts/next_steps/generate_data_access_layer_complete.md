
---

## README Template (after tests pass)

Create `README.md` in the timestamped directory (parent of `{output_dir}`). Only generate the structure shown below - do not add additional content:

```markdown
# DynamoDB Data Access Layer - [Application Domain]

This document describes the file organization and structure of the generated DynamoDB data access layer.

## Directory Structure

[folder_name]/
├── README.md
├── dynamodb_requirement.md      (if exists)
├── dynamodb_data_model.md
├── schema.json
├── usage_data.json              (if exists)
└── generated_dal/
    ├── entities.py
    ├── repositories.py
    ├── base_repository.py
    ├── access_pattern_mapping.json
    ├── ruff.toml
    └── usage_examples.py        (if exists)

## File Descriptions

### Design Documents

| File | Purpose |
|------|---------|
| `dynamodb_requirement.md` | (Optional) Business requirements with application overview, access pattern analysis, and design decisions. |
| `dynamodb_data_model.md` | Technical data model with table designs, GSI definitions, and access pattern mappings. |

### Schema Files

| File | Purpose |
|------|---------|
| `schema.json` | Machine-readable JSON schema with tables, entities, GSIs, and access patterns for code generation. |
| `usage_data.json` | (Optional) Sample data for each entity containing `sample_data`, `access_pattern_data`, and `update_data` sections. |

### Generated Code (generated_dal/)

`entities.py`, `repositories.py`, and `base_repository.py` are the three files that enable data access to the designed DynamoDB data model. These files are used in `usage_examples.py` to demonstrate how the generated code can be used.

| File | Purpose |
|------|---------|
| `entities.py` | Pydantic entity classes with PK/SK builders and GSI key builders. |
| `repositories.py` | Repository classes with CRUD operations and access pattern method stubs. |
| `base_repository.py` | Base class with DynamoDB operations: create, get, update (optimistic locking), delete, query. |
| `access_pattern_mapping.json` | JSON mapping of access pattern IDs to method implementations. |
| `ruff.toml` | Ruff linter configuration. |
| `usage_examples.py` | (Optional) Runnable examples demonstrating CRUD and access patterns. |
```
