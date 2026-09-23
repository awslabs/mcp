# End-to-end test: Every tool, both warehouse types

2026-09-18 22:31 UTC

- **Scenario**: `tools`
- **Code under test**: `feat/redshift-session-redesign` at `ba6088c6`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 9.2 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| list_clusters | PASS | Both harness warehouses discovered as available on all five configurations tried; other account clusters listed and untouched. |
| list_databases | PASS | Identical on both warehouses; auto-mounted catalogs typed as `auto mounted catalog`. |
| list_schemas | PASS | Same four schemas on both. Connecting to the auto-mounted `awsdatacatalog` fails with Redshift's own FATAL, as documented. |
| list_tables | PASS | Same seven `tickit` tables on both; unknown schema returns an empty list. |
| list_columns | PASS | Same ten `tickit.sales` columns and types on both; unknown table returns an empty list. |
| execute_query | PASS | Reads, typed values, read-only deny-list, engine read-only backstop, transaction breaker, named transactions with commit and rollback, failed user SQL, fallback reads and refusals, and write confirmation all behaved as the unit tests describe. |
| review_cluster | PASS | 11 findings / 55 signals provisioned; 3 / 37 serverless with the provisioned-only diagnostics skipped and ServerlessScaling added. |

- `rw_*` never completes a confirmation round trip in this client: every write, including `SELECT ... INTO` and a `DELETE` CTE under a `SELECT`, was refused with the message naming the elicitation requirement and the `UNSAFE_SKIP_WRITE_CONFIRMATION` opt-out. The fail-closed branch is covered; a confirm and a decline are not observable here.
- An unquoted deny-listed word as an alias (`SELECT 'grant' AS unload`) is rejected by Redshift itself, not by the guard — the statement reached the engine and came back as a syntax error. Quoting the aliases ran it.
- Serverless `public` holds a pre-existing `mcp_demo_rows` table that this run did not create and left alone; provisioned `public` is empty.
- Oversized-SQL rejection (`MAX_SQL_LEN`) was not exercised end to end; it is a pre-parse length check covered by the unit suite.

## Prompt

Written by the harness, not by hand. The agent derives the cases from the package's unit tests, and is told where to look rather than what to expect.

You have the Redshift MCP server available at several configurations, each running the working tree you are testing. Every configuration exposes the same tools, distinguished by prefix, so `ro_execute_query` and `rw_execute_query` are the same tool at two configurations:
- `ro_*` — default configuration: read-only, which is what a user gets by installing it
- `rw_*` — ACCESS_MODE=read-write, so writes are permitted and each one is confirmed
- `rwu_*` — ACCESS_MODE=read-write with UNSAFE_SKIP_WRITE_CONFIRMATION=true, so writes run unconfirmed
- `nb_*` — default configuration, but its credentials are denied redshift-data:BatchExecuteStatement
- `nbw_*` — ACCESS_MODE=read-write with UNSAFE_SKIP_WRITE_CONFIRMATION=true, and its credentials are denied redshift-data:BatchExecuteStatement

Two warehouses are provisioned and seeded with the TICKIT sample schema `tickit` in database `dev`: provisioned cluster `mcp-e2e-provisioned` and Serverless workgroup `mcp-e2e-serverless`. Both hold the same tables, so a check that holds on one should hold on the other. Other clusters exist in this account; leave them alone.

Run a complete set of end-to-end tests covering all of the server's tools. Check both the provisioned cluster and the Serverless workgroup, including the database schema exploration in both. Check the SQL read-only protection, the transaction breaker protection, and failed user SQL behaviour. Get the test scenario ideas from the unit tests under the project directory.

End your reply with a section that begins on its own line with `## Summary` and holds nothing but,
in this order:

1. A markdown table with the columns Scenario, Result and Comment. One row per tool. Result is
   PASS or FAIL. Leave Comment empty unless there is something to say.
2. Only if anything is worth noting, a short bulleted list under the table.

This section is lifted into a committed report and read on its own, so keep every row
intelligible without the rest of the reply.

## Transcript

I'll start by looking at the unit tests to understand what behaviours to cover.Both warehouses discovered and their databases listed. Now schema exploration on both.Transaction survived a guard rejection. Now a failing statement inside it, which should abort the transaction.Now the read-write configurations.Now the denied-batch fallback configurations.Now the last tool: review_cluster on both warehouses. This takes minutes.All seven tools exercised against both warehouses, plus the protections and failure paths. Everything behaved as the unit tests describe.

What the run covered beyond the plain happy path:

Schema exploration is identical on both warehouses — same four schemas, same seven `tickit` tables, same ten `sales` columns with matching types. Unknown schema and unknown table each return an empty list rather than an error; the auto-mounted `awsdatacatalog` database is listed by `list_databases` but refuses connection in `list_schemas`, as documented.

Read-only protection refused `UNLOAD`, `GRANT`, `TRUNCATE`, `SET transaction_read_only TO off`, `set_config(...)` in a projection, and `PREPARE`, each naming the keyword. Writes the deny-list does not cover (`INSERT`, `CREATE TABLE`) passed the guard and were stopped by the engine with `ERROR: transaction is read-only` on both warehouses. Deny-listed words as quoted aliases, string literals and column names ran normally, so the classification is structural rather than textual.

The transaction breaker refused `BEGIN`, `COMMIT` and `ABORT` — including in read-write mode, where the refusal names the four transaction parameters to use instead. `TRUNCATE` inside a named read-write transaction was refused as an implicit commit, then ran fine standalone.

Failed user SQL surfaced the engine message verbatim (`relation ... does not exist`, `column ... does not exist`). A guard rejection inside a transaction left it open and usable; a statement that failed on the engine aborted it, and the next call under that name reported it gone and listed every way it could be gone.

Transactions: a read-only snapshot spanning three statements committed; a read-write transaction's insert was visible inside it and absent after rollback, and persisted after commit. A name is bound to its cluster and database — the same name against the other warehouse was not found — and reopening an open name was refused.

The denied-batch fallback served reads and all four discovery tools on both warehouses, and refused writes and named transactions with messages naming `redshift-data:BatchExecuteStatement`. `rw_*` refused every write for want of a prompt, including `SELECT ... INTO` and a `DELETE` CTE fronted by a `SELECT`, which confirms both are classified as writes.

`review_cluster` returned 11 findings across 55 signals on the provisioned cluster and 3 across 37 on serverless, where the provisioned-only diagnostics (NodeDetails, WLMConfig, WorkloadEvaluation, CopyPerformance) were skipped and ServerlessScaling ran instead.

Scratch tables I created were dropped; `public` is empty on the provisioned cluster afterwards.

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] Running: git branch --show-current; git log --oneline -5; git status --porcelain; git diff --stat HEAD~3 2>/dev/null | tail -20

[tool] Reading sql_guard.py:1

[tool] status: Completed

[tool] status: Completed

[tool] Running: git diff HEAD~2 -- awslabs/ tests/conftest.py | head -250

[tool] Running: grep -n "def test_\|^class \|# ---" tests/test_sql_guard.py tests/test_transactions.py tests/test_clusters.py | head -200

[tool] status: Completed

[tool] status: Completed

[tool] Running: grep -n "^class \|    def test_\|    async def test_" tests/test_server.py | head -120

[tool] Running: grep -n "^class " tests/test_redshift.py

[tool] status: Completed

[tool] status: Completed

[tool] Running: sed -n 2318,2560p tests/test_redshift.py

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed
