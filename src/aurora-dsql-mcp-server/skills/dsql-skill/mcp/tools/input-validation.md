# Input Validation for DSQL MCP Queries

Part of [Aurora DSQL MCP Tools Reference](../mcp-tools.md).

The `readonly_query` and `transact` tools do not accept bound parameters.
Build every query with the [`safe_query`](safe_query.py) helper. Do not
interpolate values into SQL with f-strings, `%`, `.format()`, or concatenation.

---

## Required Pattern

```python
from safe_query import build, allow, regex, ident, keyword, integer, literal, TENANT_SLUG, UUID

sql = build(
    "SELECT * FROM {tbl} WHERE tenant_id = {tid} AND entity_id = {eid}",
    tbl=ident("entities"),
    tid=regex(tenant_id, TENANT_SLUG),
    eid=regex(entity_id, UUID),
)
readonly_query(sql)
```

`build()` raises `UnsafeSQLError` when a placeholder receives a raw string, so
`build("... {x} ...", x=user_input)` fails loudly at the call site.

## Validator Selection

| Value kind                         | Validator              | Emits                |
|------------------------------------|------------------------|----------------------|
| Known set (tenant ID, status enum) | `allow(v, SET)`        | `'value'`            |
| Known set used as SQL keyword      | `keyword(v, SET)`      | `value` (unquoted)   |
| Strict format (UUID, slug)         | `regex(v, PATTERN)`    | `'value'`            |
| Table or column name               | `ident(name)`          | `"value"`            |
| Integer                            | `integer(v)`           | `value`              |
| Free text (description, comment)   | `literal(v)`           | `$dq_xxx$value$dq_xxx$` |

Built-in patterns in `safe_query.py`: `TENANT_SLUG` (`[a-z0-9-]{1,64}`),
`UUID`, `INT`.

## Authorization Is Separate

Format validation proves the value is shaped correctly. It does not prove the
caller is allowed to act on it. Authorize the caller against the tenant or
resource **before** validating format or calling `build()`:

```python
assert_caller_has_tenant_access(caller, tenant_id)   # authorization
sql = build("... WHERE tenant_id = {tid}", tid=regex(tenant_id, TENANT_SLUG))
```

## Why the Helper Exists

- `readonly_query` and `transact` accept only SQL strings — no parameter
  binding ([`server.py:141-142, 267-272`](https://github.com/awslabs/mcp/blob/296b7aacf733f45bcb2a738875c4694eb3459686/src/aurora-dsql-mcp-server/awslabs/aurora_dsql_mcp_server/server.py#L141)).
- Server-side regex filters reject textbook injection in read-only mode
  (tautologies, `--` comments, stacked queries, `UNION SELECT`) but miss
  subquery exfiltration and non-equality boolean injection.
- Write mode disables those filters entirely
  ([`server.py:295-318`](https://github.com/awslabs/mcp/blob/296b7aacf733f45bcb2a738875c4694eb3459686/src/aurora-dsql-mcp-server/awslabs/aurora_dsql_mcp_server/server.py#L295-L318)).
  Skill-level validation is the only defense.

## Rules

- **MUST** build every SQL string with `safe_query.build()`.
- **MUST** authorize the caller before validating format.
- **MUST NOT** fall back to f-strings, `%`, `.format()`, or concatenation when
  a validator rejects a value — fix the caller or widen the validator.
- **MUST NOT** catch `UnsafeSQLError` to recover silently. Re-raise or return
  an error to the caller.
- **SHOULD** add new patterns to `safe_query.py` rather than inlining regex at
  call sites, so reviewers can audit them in one place.
