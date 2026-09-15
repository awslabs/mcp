# End-to-end test: Every tool, both warehouse types

2026-09-15 04:07 UTC

- **Scenario**: `tools`
- **Code under test**: `feat/redshift-session-redesign` at `da4a5961`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 16.0 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| list_clusters | PASS | Both harness warehouses listed as available alongside unrelated clusters; identical output on the denied-batch configuration, which does not use the Data API. |
| list_databases | PASS | Same four databases on both warehouses. A non-existent cluster identifier is refused with a message pointing at list_clusters. |
| list_schemas | PASS | Same four schemas on both warehouses. An auto-mounted Glue catalog database fails with the documented "Cannot connect to shared database" error. |
| list_tables | PASS | The same seven `tickit` tables on both warehouses; an unknown schema returns an empty list, not an error. |
| list_columns | PASS | Column metadata matches across both warehouses; an unknown table returns an empty list. |
| execute_query | PASS | Reads, typed values, read-only guard, engine backstop, transaction lifecycle, transaction breaker, failed SQL and the denied-batch fallback all behaved as specified on both warehouses. |
| review_cluster | PASS | 11 signals on the provisioned cluster, 8 on Serverless with provisioned-only diagnostics skipped and `ServerlessScaling` added; same 8 through the denied-batch fallback. |

- Read-only protection: `UNLOAD`, `GRANT`, `SET transaction_read_only TO off`, `TRUNCATE` and multi-statement input were refused before execution; `CREATE TABLE` and a `WITH`-fronted `UPDATE` passed the guard by design and were refused by the engine with `ERROR: transaction is read-only`, leaving nothing behind. Deny-listed keyword text as a literal, alias or `$$` body was allowed, and a nested block comment did not desync the guard from the statement the engine runs.
- Transaction breaker: `COMMIT`, `BEGIN TRANSACTION` and `ABORT WORK` were refused as statements at `rwu_*` as well as `ro_*`, each naming the transaction parameters to use instead. `TRUNCATE` was refused inside a named transaction and ran standalone.
- Named transactions: a read-only transaction survived a guard rejection and closed on a last read; a read-write one rolled back a staged insert and another committed two; a statement that failed in the engine aborted its transaction and dropped the name.
- `rw_*` fails closed: this CLI does not advertise elicitation, so a write was refused for want of a confirmation and did not reach the engine. A confirm or decline round trip is unreachable from this client.
- Denied-batch fallback: reads and all four discovery tools work; writes are refused naming `redshift-data:BatchExecuteStatement` at both `nb_*` and `nbw_*`, and named transactions are refused without reserving the name. The read-only refusal matters most, since the `BEGIN READ ONLY` wrapper is unavailable there.
- Not exercised: the oversize (>65,536 characters) and deep-nesting rejections, which need multi-kilobyte literals in a tool argument and are covered by unit tests.
- All scratch objects created during the run were dropped; both warehouses end with only the seeded `tickit` tables.

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

I'll start by looking at the unit tests to understand what behaviors to cover.Unit tests give me the scenario set. Starting with discovery.Discovery holds on both. Now reads and typed values.Now the read-only protection.Now the false-positive side of the guard, so it isn't just refusing everything.Now the transaction breaker: transaction control is refused in every mode, including read-write.Read-only named transaction, statements decided up front: two reads on one snapshot, with a guard rejection in the middle.Failed user SQL, standalone.A failing statement inside a named transaction should abort it and drop the name.Now the parameter rules on execute_query.The `rw_*` configuration, where each write is confirmed.The `rwu_*` configuration, where writes run. Using scratch tables in `public` on the harness warehouses.A read-write named transaction, rolled back: statements decided up front, closed in this stretch.Now the same on serverless, committing this time.Now the compatibility path, where `BatchExecuteStatement` is denied.A user-table read through the fallback, on both warehouses.The fallback's own refusals: transactions, and writes at `nbw_*`.The critical fallback case: in read-only mode the wrapper is gone, so an ordinary write has no backstop.Now `review_cluster` on both warehouses.Oversize and deep-nesting fail-closed paths need multi-kilobyte literals in a tool argument; they are unit-covered and I am skipping them here. Continuing with the fallback against `review_cluster`.Read classification at `rw_*`, where a misclassified read would be blocked for want of confirmation.Cleaning up the scratch tables.All seven tools exercised against both warehouses, and every protection behaved as the unit tests specify.

Discovery agrees across the provisioned cluster and the Serverless workgroup: same four databases, same four schemas, the same seven `tickit` tables, and matching column metadata; unknown schemas and tables come back as empty lists rather than errors. The read-only guard refused `UNLOAD`, `GRANT`, `SET transaction_read_only TO off`, `TRUNCATE` and statement stacking before execution, while ordinary writes it deliberately passes through — `CREATE TABLE`, and an `UPDATE` behind a `WITH` — were stopped by the engine with `ERROR: transaction is read-only`, and I confirmed neither left anything behind. The guard did not overreach: deny-listed keyword text as a literal, alias or `$$`-quoted body ran fine, and a nested block comment classified the statement the engine would actually run rather than the decoy.

Transaction control is refused as a statement in every mode, `rwu_*` included, with the refusal naming the parameters to use instead. A named read-write transaction staged an insert, refused `TRUNCATE` inside itself, and rolled back cleanly; another committed two inserts that a different configuration then read back. A statement that failed in the engine aborted its transaction and dropped the name, so the following commit reported the name as unknown instead of committing nothing.

`rw_*` fails closed as documented: this CLI does not advertise elicitation, so a write was refused for want of a confirmation and never reached the engine, while reads, `SHOW` and `EXPLAIN` ran untouched. On the denied-batch path reads and all four discovery tools work through the fallback, but writes are refused naming `redshift-data:BatchExecuteStatement` — including at read-only, where the `BEGIN READ ONLY` wrapper is unavailable and running the write unwrapped would have lost the backstop entirely.

Two things I did not exercise: the oversize and deep-nesting fail-closed rejections, which need multi-kilobyte literals in a tool argument and are covered by unit tests, and a completed confirmation round trip, which no client here can perform.

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] Reading sql_guard.py:1

[tool] status: Completed

[tool] Reading test_sql_guard.py:1

[tool] status: Completed

[tool] Running: grep -n '^class \|^    def test' tests/test_server.py | head -150

[tool] status: Completed

[tool] Running: grep -n '^class ' tests/test_redshift.py

[tool] status: Completed

[tool] Running: sed -n '2091,2140p;2493,2560p;2667,2860p' tests/test_redshift.py

[tool] status: Completed

[tool] Running: sed -n '1895,2495p' tests/test_redshift.py | grep -n 'def test\|"""' | head -120

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_columns

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: grep -n 'MAX_SQL_LEN' awslabs/redshift_mcp_server/consts.py

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed
