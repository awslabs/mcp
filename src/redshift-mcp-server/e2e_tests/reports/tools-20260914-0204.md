# End-to-end test: Every tool, both warehouse types

2026-09-14 02:04 UTC

- **Scenario**: `tools`
- **Code under test**: `feat/redshift-session-redesign` at `b1ed1958`, uncommitted changes
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 18.1 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| list_clusters | PASS | Both harness warehouses listed with correct type and status; works under denied-batch credentials, which need no Data API |
| list_databases | PASS | Identical on both warehouses; batch and fallback paths agree |
| list_schemas | PASS | `tickit` found on both; unknown database and auto-mounted Glue catalogue fail with the documented connect error |
| list_tables | PASS | Same 7 TICKIT tables on both; unknown schema returns an empty list, not an error |
| list_columns | PASS | Column types and ordinals identical on both; unknown table returns an empty list |
| execute_query | PASS | Reads, type mapping, guard rejections, engine backstop, named transactions, the breaker, the per-target cap and all five configurations behaved as documented |
| review_cluster | PASS | 11 signals on provisioned, 8 on serverless with provisioned-only ones skipped and `ServerlessScaling` added; unknown cluster errors rather than reporting clean |

- TICKIT row counts matched exactly across both warehouses (172,456 sales / 49,990 users / 192,497 listings) before and after the run, and both scratch tables were dropped, so nothing was left behind.
- `rw_*` never completes a confirmation round trip from this client: the write is refused for want of an elicitation channel. That is the fail-closed branch; a confirm and a decline remain unobservable here.
- The guard's oversized-input rejection (>64 KiB) was not re-tested end to end, since it is a pre-parse length check with no server-side interaction beyond what the unit suite already covers.
- One finding worth reading rather than acting on: `review_cluster` reports "should consider migrating to RG instances" against the harness's own `ra3.large` cluster, which is expected for the node type the harness provisions.

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

I'll start by looking at the unit tests to understand what behaviours to cover.Now the live testing. Starting with discovery on both warehouses.Both targets present. Now schema exploration on both warehouses.Now the read-only guard. Deny-listed statements target non-existent objects so nothing is at risk if the guard were to let one through.Now named transactions. Read-only snapshot first, closed cleanly.Now the transaction breaker: a failed statement inside a transaction must abort it and drop the name.Checking the open-transaction cap (default 10 per target).Now review_cluster on both warehouses.Now the write configurations. `rw_*` first — writes must fail closed since this client cannot be prompted.Now `rwu_*`, where writes run unconfirmed. Using a scratch table in `public`.Now a read-write transaction: rollback must discard, commit must persist.Now the breaker where it matters most: a failed statement inside a read-write transaction must not leave partial work.Now the denied-batch configurations. First `nb_*` reads through the fallback path.Cleaning up the scratch tables.All coverage is done and the warehouses are back to their seeded state.

What I exercised, beyond the plain happy path of each of the seven tools on both warehouses:

The SQL guard rejected every deny-listed statement type it is meant to (`TRUNCATE`, `GRANT`, `VACUUM`, `UNLOAD`, `COMMIT`, `ABORT`, `SET transaction_read_only TO off`), stacked statements, and unparseable input, each with the message the unit tests pin. It also declined to fire on deny-listed keyword text used as a literal or alias, and rejected a `TRUNCATE` hidden behind a nested block comment. Ordinary writes that pass the guard on purpose — `INSERT`, `CREATE TABLE`, a data-modifying CTE — were refused by the engine with `ERROR: transaction is read-only` on both warehouses, so the `BEGIN READ ONLY ... ROLLBACK` wrapper is doing its job.

The transaction breaker was checked where it can actually cost data: a read-write transaction wrote a row, the next statement failed, and afterwards the row was gone, the name was dropped, and a `COMMIT` of it was refused rather than reporting success while persisting nothing. A guard rejection inside a transaction, by contrast, left it open and usable, which is right since nothing was submitted. The per-target cap held at 10 and the 11th open was refused while the other warehouse still accepted one.

Failed user SQL surfaced the engine's own message (`relation ... does not exist`, `division by zero`, `VALUES lists must all be the same length`) on both warehouses and on both the batch and fallback paths.

Across configurations: `rw_*` refused writes fail-closed because this client cannot be prompted, and the refused `CREATE TABLE` left nothing behind. `rwu_*` ran writes for real, with rollback discarding and commit persisting both statements. `nb_*` and `nbw_*` served reads and all four metadata tools through the no-batch fallback with results identical to the batch path, and refused writes and named transactions with the fallback's own explanations rather than a confirmation error.

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] Reading sql_guard.py:1

[tool] status: Completed

[tool] Running: grep -n "breaker\|MAX_OPEN_TRANSACTIONS\|SESSION_KEEPALIVE\|no_batch\|BatchExecuteStatement" /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/awslabs/redshift_mcp_server/*.py | head -80

[tool] status: Completed

[tool] Reading redshift.py:241-540

[tool] status: Completed

[tool] Reading redshift.py:546-835

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/tests && grep -n "^async def test\|^def test\|^class Test" test_sql_guard.py

[tool] status: Completed

[tool] Reading test_sql_guard.py:26-445

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/e2e_tests && ls .kiro/agents && sed -e 's/\(AWS_SECRET_ACCESS_KEY\|AWS_SESSION_TOKEN\)":[^,]*/\1": "REDACTED"/g' .kiro/agents/*.json | hea...

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

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: grep -n "MAX_SQL_LEN\|FALLBACK_NO_BATCH_REPROBE" /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/awslabs/redshift_mcp_server/consts.py

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/e2e_tests/.logs && grep -n "Rollback of the aborted\|Closed transaction\|VALUES lists" awslabs.redshift-mcp-server-read-write-unsafe.log |...

[tool] status: Completed
