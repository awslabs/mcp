# End-to-end test: Every tool, both warehouse types

2026-10-01 22:09 UTC

- **Scenario**: `tools`
- **Code under test**: `feat/redshift-session-redesign` at `aa1073db`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 14.4 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| list_clusters | PASS | Both harness warehouses listed as `available` with correct type, node type and tags; unrelated clusters in the account listed but untouched. Also works under the denied-batch fallback, which uses the control plane rather than the Data API. |
| list_databases | PASS | Identical on both warehouses: `dev` as `local`, three `auto mounted catalog` entries. Also passes under the denied-batch fallback. |
| list_schemas | PASS | `tickit`, `public`, `information_schema`, `pg_catalog` on both, with ACLs showing the grants to both database identities. Also passes under the denied-batch fallback. |
| list_tables | PASS | Same 7 TICKIT tables on both warehouses. An unknown schema returns an empty list rather than an error. Also passes under the denied-batch fallback. |
| list_columns | PASS | `tickit.sales` columns, types, precision/scale and nullability identical on both warehouses. An unknown table returns an empty list rather than an error. Also passes under the denied-batch fallback. |
| execute_query | PASS | Reads, type mapping, the row cap, named transactions, read-only protection, the transaction breaker, write confirmation and failed-SQL behaviour all as documented, on both warehouses. Detail in the notes below. |
| review_cluster | PASS | Provisioned: 48 signals, 12 findings, 11 queries. Serverless: 32 signals, 2 findings; provisioned-only diagnostics (`NodeDetails`, `WLMConfig`, `WorkloadEvaluation`, `CopyPerformance`) skipped and `ServerlessScaling` added. Identical result under the denied-batch fallback. |

- SQL read-only protection (PASS): the guard refuses `TRUNCATE`, `UNLOAD`, `GRANT`, `VACUUM`, `SET`, `set_config`, `pg_terminate_backend` and `change_query_priority` before execution, naming the statement type. `INSERT`/`UPDATE`/`DELETE`/`DROP`/`CREATE` pass the guard and are neutralized by the engine with `ERROR: transaction is read-only`. Verified on both warehouses that neither layer changed any data or left a table behind.
- Guard evasion attempts all refused (PASS): a mixed-case `tRuNcAtE` behind a leading semicolon was named as `TRUNCATE`; a nested-comment prefix was refused as unparseable; `SELECT 1; SELECT 2` was refused as multi-statement. Keyword text used as a literal or quoted alias, and `current_setting(...)`, remain allowed.
- Transaction breaker (PASS): `BEGIN`, `COMMIT`, `ROLLBACK` and `START TRANSACTION` in `sql` are refused in every mode. In read-write modes the refusal names the four transaction parameters to use instead; in read-only mode the read-only guard reaches them first and refuses with its own message. `TRUNCATE` and `CALL` are refused inside a named transaction with an explanation, and run normally outside one.
- Named transactions (PASS): held open across calls on a single session (`transaction_read_only` = `on` in read-only mode); rollback discarded a staged insert and commit persisted one; a temp table survived across calls inside a transaction but not outside one. A failing statement released the transaction and dropped its name; duplicate-open, wrong-target, multiple-parameter and missing-`sql` calls were each refused and left any open transaction as it was.
- Failed user SQL (PASS): syntax errors, unknown relations and divide-by-zero come back as `Statement failed: ERROR: ...` with Redshift's own message and position intact. An unresolvable cluster identifier is refused before reaching the warehouse.
- Row cap (PASS): 1001 rows was refused outright with guidance rather than truncated; 1000 rows came back whole across multiple result pages.
- Write confirmation: `rwu_*` ran a full create/insert/update/delete/truncate/drop lifecycle on both warehouses, with results visible from the read-only server. `rw_*` fails closed on every write — including `SELECT INTO` and a data-modifying CTE, both correctly classified as writes — because this client does not advertise elicitation; the refusal names the `UNSAFE_SKIP_WRITE_CONFIRMATION` opt-out. A confirm-then-proceed and a decline round trip cannot be reached from this client and were not exercised.
- Denied-batch fallback (PASS): reads and all catalogue tools work; writes and named transactions are refused with messages that name the missing `redshift-data:BatchExecuteStatement`, the 300-second window and what granting it restores. Under `nbw_*` (confirmation skipped) the fallback's own write refusal surfaces, including for `TRUNCATE`, which the read-write guard allows through.
- Not exercised: the 65 KB `MAX_SQL_LEN` rejection, which is impractical to send through this client and is covered by the unit suite.

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

I'll start by looking at the unit tests to understand what behaviours to cover.Let me pull scenario ideas from the unit tests and source.Both targets available. Now schema exploration on both warehouses.Catalogue surface matches on both. Now reads through `execute_query`, including type mapping.Now the read-only protection. First the statement types the guard refuses before execution.Now the writes the guard lets through in read-only mode, which the `READ ONLY` transaction must neutralize at the engine.Data intact. Now the transaction breaker: transaction control in `sql` must be refused in every mode.Now named transactions. A read-only transaction across several calls:Now failed user SQL, and what a failure does to an open transaction.Now the `rw_` configuration, where each write must be confirmed:`rw_` fails closed. Now `rwu_`, where writes run unconfirmed — a full write lifecycle:Now a read-write named transaction, to check rollback really discards and commit really persists.Now the documented session-state behaviour: a temp table needs a transaction to survive.Same write lifecycle on the Serverless workgroup:Now the denied-batch fallback path. Catalogue and reads under `nb_`:Pagination reads the whole result. Now `review_cluster` on both warehouses.`review_cluster` scopes correctly per type. Now under the denied-batch fallback:All checks complete. Seeded data is byte-identical on both warehouses after the run, and nothing I created was left behind (the one `public` table on Serverless, `mcp_demo_rows`, pre-dates this run).

A few things worth recording beyond the tool-by-tool result. The denied-batch fallback was verifiably in effect rather than silently falling back to the normal path: reads under `nb_*`/`nbw_*` returned `current_user` = `IAMR:mcp-e2e-denied-batch` and a bare `query_id` UUID, where the batch path returns `uuid:N`. And the read-only protection works in two distinct layers — the guard refuses `TRUNCATE`/`UNLOAD`/`GRANT`/`VACUUM`/`SET`/`set_config`/`pg_terminate_backend`/`change_query_priority` before execution, while `INSERT`/`UPDATE`/`DELETE`/`DROP`/`CREATE` pass the guard and are stopped by the engine with `ERROR: transaction is read-only`. I confirmed both leave the data untouched.

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] Running: grep -h "^\s*\(async \)\?def test" tests/test_sql_guard.py | sed 's/(.*//' | head -120

[tool] status: Completed

[tool] Running: for f in tests/test_transactions.py tests/test_catalog.py tests/test_server.py; do echo "=== $f"; grep -h "^\s*\(async \)\?def test" $f | sed 's/(.*//'; done

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/list_columns

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: grep -rn "MAX_RESULT_ROWS\|max_result_rows" awslabs/redshift_mcp_server/consts.py awslabs/redshift_mcp_server/settings.py e2e_tests/agent.py 2>/dev/null | head -20

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] Running: grep -n "LENGTH\|DEPTH\|NEST" awslabs/redshift_mcp_server/consts.py

[tool] status: Completed

[tool] Running: grep -n "MAX_SQL\|max_sql\|too long\|oversiz\|depth\|recursion" awslabs/redshift_mcp_server/sql_guard.py | head -20

[tool] status: Completed

[tool] Running: grep -n "MAX_SQL_LEN" -A2 -B2 awslabs/redshift_mcp_server/consts.py

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed
