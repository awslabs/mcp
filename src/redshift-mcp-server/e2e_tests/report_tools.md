# End-to-end test: Every tool, both warehouse types

2026-09-17 02:07 UTC

- **Scenario**: `tools`
- **Code under test**: `feat/redshift-session-redesign` at `197b97c0`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 26.6 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| list_clusters | PASS | Both target warehouses reported `available`; serverless correctly has null node_type, number_of_nodes and master_username. Unaffected by the batch denial, since it uses the control-plane APIs. |
| list_databases | PASS | Same four databases on both, with `local` and `auto mounted catalog` types distinguished. An unknown cluster identifier is refused with a pointer to list_clusters. |
| list_schemas | PASS | `tickit` found on both. An unknown database errors, and an auto-mounted Glue catalog errors on connect, both as documented. |
| list_tables | PASS | The same 7 TICKIT tables on both; an unknown schema returns an empty list rather than an error. |
| list_columns | PASS | Identical 10-column definition of `tickit.sales` on both; an unknown table returns an empty list, an unknown database errors. |
| execute_query | PASS | Reads, value typing, the read-only guard and engine backstop, the transaction breaker, named transaction lifecycles, failed user SQL and the denied-batch fallback all behaved as documented, on both warehouses. |
| review_cluster | PASS | 55 signals on the provisioned cluster, 37 on serverless with provisioned-only queries skipped and `ServerlessScaling` added. Also completes over the denied-batch fallback. |

- `rw_*` cannot complete a confirmation round trip, because this client does not advertise elicitation. Both write attempts were refused fail-closed with the message naming `UNSAFE_SKIP_WRITE_CONFIRMATION`, and a refused write left its transaction open and closable. A confirm or a decline remains unobservable from here; `rwu_*` covered writes actually running.
- Redshift rejects data-modifying CTEs at parse time, so that guard case surfaces as a syntax error rather than a read-only refusal. `INSERT`, `CREATE TABLE` and `SELECT ... INTO` were each refused by the read-only wrapper instead.
- `EXPLAIN INSERT ...` is classified as a read and runs unconfirmed in read-write mode. Verified nothing was inserted: Redshift's `EXPLAIN` does not execute its payload, so the classification is sound.
- Concurrent statements on one cluster could not be observed, because tool calls from this client serialize. The underlying property was checked instead: session state does not carry between calls, but does carry between statements inside a named transaction.
- Oversized SQL (`MAX_SQL_LEN`) was not exercised end-to-end. It is a pre-parse local check with no service interaction, covered by the unit suite.
- The fallback latch re-probes every 300 seconds, so during a session this long it re-latched several times, logging one warning per window. Expected behaviour, and how a granted policy would be picked up without a restart.

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

I'll start by looking at the unit tests to understand what behaviours to cover.Unit tests give me the scenario set. Starting with discovery on both warehouses.Catalog matches on both. Now the negative catalog cases.Discovery is done. Now `execute_query` reads and value typing.The guard's deny-list holds. Now the engine backstop, which is what stops ordinary writes in read-only mode.Structural matching, so no false positives. Now the transaction breaker.Transaction control is refused in both modes. Now named transactions, starting read-only.A failed statement dropped the name, as documented. Now a clean lifecycle on Serverless.Now failed user SQL, standalone.Now `rw_*`, where writes need a confirmation this client cannot give.`rwu_*` writes unconfirmed, so now real writes against a scratch table.Now a read-write transaction, rolled back.Rollback discarded both writes. Now a committed one.Now a failed statement inside a read-write transaction.TRUNCATE standalone, which read-write mode should allow.Write parity on Serverless.Read-write mode should permit what read-only denies.Now the denied-batch fallback, `nb_*`.Now `review_cluster` on both warehouses.Concurrency is a documented claim, so let me try to observe it. Two statements at once on the same cluster and database.Tool calls here serialize, so let me check the underlying property instead: no session state carries between calls.Let me confirm the read-only wrapper in query history — the mechanism behind the protection.Verifying that nothing the protections refused was actually created, then cleaning up.Finally, a look at the server logs for anything the client side would not show.All seven tools pass on both warehouses. Nothing was left behind: the two scratch tables I created are dropped, the seeded `tickit` data is unchanged, and none of the refused writes created anything.

What the run established beyond the tool surface:

The read-only protection is two mechanisms, and I saw both. The guard refuses the statement types a read-only transaction cannot neutralize (TRUNCATE, UNLOAD, GRANT, VACUUM, COMMENT, SET, `set_config`, PREPARE, DECLARE), while ordinary writes pass the guard and are stopped by the engine with `ERROR: transaction is read-only`. Query history confirms the mechanism: `BEGIN READ ONLY`, the caller's statement, then `ROLLBACK`, all under one xid. The same lookup on a read-write statement shows an autocommit `COMMIT` and no wrapper, and a fallback statement shows neither wrapper nor `application_name`, exactly as the code comments claim.

The transaction breaker holds in both modes with different wording — read-only reports it as a denied statement type, read-write names the four parameters to use instead — and TRUNCATE and CALL are refused inside a named transaction while TRUNCATE standalone runs. A failed statement inside a transaction aborts it and drops the name, so the following call reports the name as unknown rather than letting a commit report success over nothing; the write staged before the failure did not persist.

The denied-batch fallback is driven by a genuine `AccessDeniedException` with an explicit deny in a session policy. Reads work there against user tables and all four catalog tools work, while writes and named transactions are refused with messages that name the missing grant.

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] Reading sql_guard.py:1, consts.py:1

[tool] status: Completed

[tool] Reading transactions.py:1, test_transactions.py:1

[tool] status: Completed

[tool] Reading server.py:1

[tool] status: Completed

[tool] Running: grep -n "^def \|^async def \|^# ---" /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/awslabs/redshift_mcp_server/redshift.py

[tool] status: Completed

[tool] Reading redshift.py:1020-1439

[tool] status: Completed

[tool] Reading redshift.py:320-1019

[tool] status: Completed

[tool] Running: grep -n "def test_\|'''\|\"\"\"" /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/tests/test_sql_guard.py | head -120

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

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_databases

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

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: grep -n -A 12 "_FALLBACK_NO_BATCH_REFUSES_WRITE = \|_FALLBACK_NO_BATCH_REFUSES_TRANSACTION = " /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/awslabs/redshift_mcp_server/redshift.py

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] status: Completed

[tool] Running: grep -h "is denied on\|WARNING" /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/e2e_tests/.logs/awslabs.redshift-mcp-server-no-batch.log | tail -5

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/e2e_tests/.logs && for f in *.log; do echo "== $f"; awk '$1=="2026-09-17" && $2>"01:44"' "$f" | grep -c "" ; awk '$1=="2026-09-17" && $2>"...

[tool] status: Completed

[tool] Running: grep "Refused a write\|requires confirmation" /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/e2e_tests/.logs/awslabs.redshift-mcp-server-read-write.log | tail -4

[tool] status: Completed
