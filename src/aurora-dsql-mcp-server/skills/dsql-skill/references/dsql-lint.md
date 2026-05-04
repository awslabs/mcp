# DSQL Lint — SQL Compatibility Validation

`dsql_lint` is an MCP tool that validates SQL for Aurora DSQL compatibility and auto-fixes
common issues. It provides deterministic, rule-based analysis — more reliable than heuristic
reasoning for catching DSQL-specific constraints.

## Table of Contents

1. [MCP Tool Reference](#mcp-tool-reference)
2. [Fix Result Statuses](#fix-result-statuses)
3. [Usage Patterns](#usage-patterns)
4. [Handling Unfixable Errors](#handling-unfixable-errors)
5. [Exit Codes](#exit-codes-for-reference)

---

## MCP Tool Reference

### dsql_lint

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sql` | string | Yes | SQL to validate |
| `fix` | boolean | No | Return DSQL-compatible fixed SQL (default: false) |

**Returns:**

```json
{
  "diagnostics": [
    {
      "rule": "<rule_id>",
      "line": 1,
      "message": "Description of the compatibility issue.",
      "suggestion": "How to fix it.",
      "fix_result": { "status": "fixed | fixed_with_warning | unfixable", "detail": "..." }
    }
  ],
  "fixed_sql": "DSQL-compatible SQL (when fix=true and fixes are possible)",
  "summary": { "errors": 0, "warnings": 1, "fixed": 1 }
}
```

---

## Fix Result Statuses

| Status | Meaning | Agent action |
|--------|---------|--------------|
| `fixed` | Safe mechanical transformation | Accept and execute |
| `fixed_with_warning` | Fix applied, may need app-layer changes | Present to user, explain implications |
| `unfixable` | Cannot auto-fix | Rewrite manually using skill knowledge |

---

## Usage Patterns

### Validate before execute

```
1. dsql_lint(sql="CREATE TABLE ...", fix=false)
2. If diagnostics empty → execute with transact
3. If diagnostics present → use fix=true or rewrite manually
```

### Lint and fix in one step

```
1. dsql_lint(sql="<your SQL>", fix=true)
2. Review fixed_sql and diagnostics
3. Present warnings to user — explain any application-layer changes needed
4. Execute fixed_sql with transact
```

### ORM migration validation

```
1. Obtain ORM-generated SQL (Django sqlmigrate, Prisma migrate, Rails schema dump)
2. dsql_lint(sql=orm_sql, fix=true)
3. For each diagnostic:
   - fixed/fixed_with_warning → accept the fix
   - unfixable → rewrite using skill knowledge (Table Recreation, app-layer patterns)
4. Split fixed_sql into one-DDL-per-transaction calls
5. Execute each with transact
```

---

## Handling Unfixable Errors

When `dsql_lint` reports unfixable errors, use skill knowledge to resolve:

| Rule | Resolution |
|------|-----------|
| `temp_table` | Use a regular table with a session/request identifier column |
| `partition_by` | Omit — DSQL manages distribution automatically |
| `inherits` | Flatten into a single table or use application-layer inheritance |
| `create_table_as` | CREATE TABLE with explicit columns, then INSERT ... SELECT |
| `truncate` | Use `DELETE FROM table_name` (batch if > 3,000 rows) |
| `unsupported_alter_table_op` | Use Table Recreation Pattern (Workflow 6) |
| `add_column_constraint` | Split: ADD COLUMN (name + type only) → UPDATE → ALTER COLUMN |
| `index_using` | Use default B-tree index (DSQL's only supported method) |
| `index_expression` | Create a computed column, then index that column |
| `index_partial` | Create a full index; filter at query time |
| `transaction_isolation` | Omit — DSQL uses Repeatable Read (fixed) |

---

## Exit Codes (for reference)

| Code | Meaning |
|------|---------|
| 0 | Clean — no issues, or all fixes applied without warnings |
| 1 | Errors found (lint mode) or unfixable errors remain (fix mode) |
| 2 | Usage error (invalid arguments) |
| 3 | Fix mode: all fixed, but some produced warnings (review recommended) |

The MCP tool handles exit codes internally. Agents receive structured JSON regardless of exit code.

---

## Additional Resources

- [dsql-lint on PyPI](https://pypi.org/project/dsql-lint/)
- [dsql-lint source (Rust CLI + npm)](https://github.com/awslabs/aurora-dsql-tools/tree/main/dsql-lint)
