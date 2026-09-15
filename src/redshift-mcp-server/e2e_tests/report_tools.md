# End-to-end test: Every tool, both warehouse types

2026-09-15 01:06 UTC

- **Scenario**: `tools`
- **Code under test**: `feat/redshift-session-redesign` at `1687d7d4`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 18.4 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| list_clusters | PASS | Both targets found and `available`; other clusters in the account listed and left alone. |
| list_databases | PASS | Same four databases on both warehouses. |
| list_schemas | PASS | `tickit` present on both; unknown database and Glue-catalog database fail with the engine's own reason. |
| list_tables | PASS | Same seven `tickit` tables on both; unknown schema returns an empty list. |
| list_columns | PASS | `tickit.sales` metadata identical on both; unknown table returns an empty list. |
| execute_query | PASS | Reads, typing, read-only protection, transaction breaker, named transactions, engine failures and the denied-batch fallback all behaved as designed. |
| review_cluster | PASS | 11 signals provisioned, 8 serverless with provisioned-only sections skipped; also works on the denied-batch fallback. |

- Read-only protection: statement types (UNLOAD, GRANT, TRUNCATE, VACUUM, SET, RESET) refused, multi-statement and unparseable input refused, comment-nesting smuggling refused, and writes that pass the guard neutralized by the read-only transaction with nothing persisted. Deny-listed words as literals, aliases or column references were correctly allowed.
- Transaction breaker: BEGIN, COMMIT and ABORT in `sql` refused at read-only, read-write and denied-batch configurations; TRUNCATE refused inside a named transaction but permitted standalone in read-write mode.
- Failed user SQL: missing relation and divide-by-zero returned the engine's message verbatim, the connection stayed usable afterwards, and the same failure inside a transaction rolled it back and dropped the name.
- Write confirmation: `rw_*` refused every write because this client cannot prompt, naming the `UNSAFE_SKIP_WRITE_CONFIRMATION` opt-out, and nothing was created. The confirm and decline branches remain unreachable from this client, as the harness documents.
- The execution path was visible in `query_id`: a `:3` suffix under the read-only wrapper, `:2` in read-write, `:1` for a statement sent bare on a transaction's session, and no suffix at all on the denied-batch fallback. Each configuration took the path it should.
- `review_cluster` findings vary run to run on the same warehouse because several signals read live query history and statistics staleness; the count of signals evaluated was stable. My own test table briefly triggered an out-of-date-statistics finding before cleanup.
- Not exercised end to end: rejection of SQL over 65,536 characters, which is impractical to send from this client and is covered by the unit suite.

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

I'll start by looking at the unit tests to understand what behaviours to cover.Now the write configuration. I'll work in a schema I create, `e2e_check`, so nothing touches the seeded `tickit` data, and drop it at the end.Now a read-write transaction that rolls back, to check the grouping actually holds.Now the committing side of a read-write transaction, on the serverless workgroup.Cleaning up the schema I created on both warehouses.All checks passed. What was covered and what it showed:

Discovery ran on both warehouses and agreed: the same four databases, four schemas including `tickit`, the same seven `tickit` tables, and identical column metadata for `tickit.sales`. Unknown schemas and tables returned empty lists rather than errors, and an auto-mounted Glue catalog (`awsdatacatalog`) refused connection as documented. Value typing matched the contract exactly, including a bigint past float precision returned intact and SUPER returned as a string.

`review_cluster` evaluated 11 signals on the provisioned cluster and 8 on serverless, skipping the provisioned-only sections (NodeDetails, WLMConfig, WorkloadEvaluation, CopyPerformance) and adding ServerlessScaling.

Read-only protection held on both warehouses. UNLOAD, GRANT, TRUNCATE, VACUUM, SET and RESET were refused by statement type; multi-statement input, unparseable input and a nested-comment attempt to smuggle a GRANT were all rejected. Deny-listed words used as literals, aliases or column references were allowed through, confirming the classification is structural rather than textual. Writes that pass the guard were neutralized by the read-only transaction — `CREATE TABLE` and `DELETE` both came back `ERROR: transaction is read-only`, and follow-up reads confirmed nothing changed.

The transaction breaker refused BEGIN, COMMIT and ABORT in `sql` at every configuration, naming the parameters to use instead, and refused TRUNCATE inside a named transaction on the grounds that it would commit it. Standalone TRUNCATE in read-write mode worked. A guard rejection inside a transaction left it open; a statement the engine rejected rolled it back and dropped the name.

Writes were exercised in a schema I created (`e2e_check`) and dropped afterwards, leaving `tickit` untouched — final row counts match the seeded 172,456 / 49,990 / 202. A rollback discarded its insert, and a commit made a CREATE, INSERT and UPDATE visible together from a different server process while nothing was visible before it.

The denied-batch configurations served every discovery tool, `review_cluster`, and reads against user tables, then refused writes and named the missing grant; the refused open did not claim the transaction name.

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] Reading sql_guard.py:1

[tool] status: Completed

[tool] Running: grep -h "^\s*\(async \)\?def test" tests/test_sql_guard.py tests/test_server.py | sed 's/^\s*//' | head -200

[tool] status: Completed

[tool] Running: grep -h "^\s*\(async \)\?def test\|^class " tests/test_redshift.py | sed 's/^\s*//' | head -250

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

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

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

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

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

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] status: Completed

[tool] Running: grep -n "MAX_SQL_LEN" awslabs/redshift_mcp_server/consts.py

[tool] status: Completed

[tool] Running: python3 -c "print('SELECT 1 /*' + 'x'*65540 + '*/')" > /tmp/oversize.sql; wc -c /tmp/oversize.sql

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed
