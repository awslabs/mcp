# MySQL to DSQL Migration: DDL Operations

Migration patterns for specific MySQL DDL operations to DSQL-compatible equivalents.

**MUST read [type-mapping.md](type-mapping.md) first** for data type mappings and the CRITICAL Destructive Operations Warning.
**MUST read [ddl-migrations/overview.md](../ddl-migrations/overview.md)** for the general Table Recreation Pattern and user verification requirements.

---

## Table Recreation Pattern Overview

**MUST** follow the canonical
[Table Recreation Pattern](../ddl-migrations/overview.md#table-recreation-pattern-overview),
including foreign-key inventory, write fencing, relationship restoration, and recovery.

## Common Verify & Swap Pattern

Use the canonical
[Common Verify & Swap Pattern](../ddl-migrations/overview.md#common-verify--swap-pattern).

---

## Detailed Migration Patterns

Load the relevant file for the specific MySQL DDL operation you need to migrate:

- **[ddl-column-changes.md](ddl-column-changes.md)** — ALTER COLUMN type, DROP COLUMN
- **[ddl-auto-increment.md](ddl-auto-increment.md)** — AUTO_INCREMENT to UUID/IDENTITY/SEQUENCE
- **[ddl-type-alternatives.md](ddl-type-alternatives.md)** — ENUM, SET, ON UPDATE CURRENT_TIMESTAMP, FOREIGN KEY
- **[ddl-constraints.md](ddl-constraints.md)** — SET/DROP NOT NULL, SET/DROP DEFAULT
- **[ddl-structural.md](ddl-structural.md)** — ADD/DROP CONSTRAINT, MODIFY PRIMARY KEY
- **[ddl-batching.md](ddl-batching.md)** — Batched migration pattern, error handling and recovery
