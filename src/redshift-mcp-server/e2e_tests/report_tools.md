# End-to-end test: Every tool, both warehouse types

2026-09-14 07:31 UTC

- **Scenario**: `tools`
- **Code under test**: `feat/redshift-session-redesign` at `6eda5981`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 20.1 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| list_clusters | PASS | Both target warehouses found on `ro_*` and on the batch-denied `nb_*`; unrelated clusters listed but untouched. Serverless `vpc_id` reports a subnet id, matching what the unit tests pin. |
| list_databases | PASS | Identical output on both warehouses. |
| list_schemas | PASS | `tickit` present on both. An auto-mounted Glue catalog database fails with Redshift's explanatory message, as documented. |
| list_tables | PASS | Same 7 tables on both; unknown schema returns an empty list, not an error. |
| list_columns | PASS | `tickit.sales` identical on both; unknown table returns an empty list, not an error. |
| execute_query | PASS | Reads, value typing, read-only guard, engine backstop, transactions, breaker, failed SQL and the no-batch fallback all verified on both warehouses across all five configurations. |
| review_cluster | PASS | 11 signals / 10 findings on provisioned, 8 signals / 2 findings on Serverless; provisioned-only diagnostics skipped and `ServerlessScaling` added. Same result on the fallback path. |

- Read-only protection: deny-listed types (`COMMIT`, `ROLLBACK`, `TRUNCATE`, `GRANT`, `UNLOAD`, `VACUUM`, `SET`) refused with the statement type named; nested-comment prefix, leading semicolon, mixed case and `truncate"t"` did not smuggle anything past it; stacked statements and unparseable SQL refused; the same keywords as aliases or literals ran normally. Non-deny-listed writes (`INSERT`, `CREATE TABLE`, a data-modifying CTE) were passed to the engine on purpose and rejected there as `transaction is read-only`, with nothing persisted.
- Transaction breaker: a failing statement inside a read-write transaction discarded an earlier committed-looking `INSERT` and dropped the name, so the follow-up commit was refused instead of silently doing nothing. A guard rejection, by contrast, left the transaction open and usable, which is correct since nothing was executed.
- The guard is enforced inside open transactions, not only outside them: `SET transaction_read_only TO off` was refused as an in-transaction statement, which is the reason that pair is deny-listed.
- `nb_*` and `nbw_*` served reads against user tables and refused writes and named transactions with their own explanations. At `nbw_*` a deny-listed `TRUNCATE` reached the fallback's write refusal rather than the read-only refusal, confirming the mode was genuinely read-write.
- `rw_*` never completes a confirmation round trip from this client, so only the fail-closed refusal was observed; `rwu_*` covered the allowed-write path. `MAX_OPEN_TRANSACTIONS_PER_TARGET` was not driven to its limit and idle expiry was not waited out.
- Incidental: `SELECT ... AS unload` passed the guard and then failed at Redshift as a reserved word. That is the engine, not the guard, and is itself evidence the guard does not match keywords by text.

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

I'll start by exploring the project structure and unit tests to understand what behaviours to verify.Let me read the guard implementation and its unit tests to derive scenarios.Now I'll begin testing. Starting with cluster discovery.Both target warehouses are discovered. Now schema exploration on both, in parallel.Schema exploration matches on both. Now the documented empty-result cases for unknown objects.Both return empty lists as documented. Now `execute_query` reads on both warehouses.Now the read-only SQL protection. First the deny-list.Now the smuggling and fail-closed paths.Now the other side of the guard: deny-listed keyword text that is only an identifier or literal must still run.The guard passed that through; Redshift itself rejects `unload` as an alias. Retrying with aliases Redshift accepts.Now the engine backstop: ordinary writes pass the guard on purpose and must be stopped by the read-only transaction.Confirming nothing was actually persisted by those attempts.Now failed user SQL behaviour in more depth.Now transactions. A read-only transaction across calls, on the provisioned cluster.Checking the guard still applies inside an open transaction — this is the reason `SET` is deny-listed.Transaction survived the guard rejection. Now testing the duplicate-name gate while it is still open.Now the transaction breaker: a failing statement inside a transaction must abort it and drop the name.Now the same transaction surfaces on Serverless, including a bare rollback.Now `review_cluster` on both warehouses.`review_cluster` skips provisioned-only diagnostics on Serverless as documented. Now the `rw_*` configuration, where writes need confirmation.Now `rwu_*`, where writes run unconfirmed. I'll work in a dedicated scratch schema and clean up after.Now a read-write transaction, rolled back.Rollback discarded it. Now the commit path, and then the breaker inside a write transaction.Now the breaker where it matters most: a failed statement after a successful write inside a transaction.The breaker rolled back the earlier successful write too. Now the write path on Serverless.Now the `nb_*` configuration, which reaches the no-batch fallback.The fallback served the read; note the query id carries no sub-statement suffix. Now its refusals.Now the discovery tools on the fallback path, and on Serverless too.Now `nbw_*`, where write confirmation is out of the way so the fallback's own refusal surfaces.One documented edge remains: an auto-mounted Glue catalog database cannot be explored.Matches the documented behaviour. Now cleaning up the objects I created.All checks are done and both warehouses are back to their seeded state (identical row counts across all seven TICKIT tables, no leftover objects).

What I covered: all seven tools, each against both `mcp-e2e-provisioned` and `mcp-e2e-serverless`, plus `execute_query` across all five configurations. Scenario ideas came from `tests/test_sql_guard.py` (deny-list, smuggling, fail-closed, no-false-positives, write classification), `tests/test_redshift.py` (transaction lifecycle, breaker, no-batch fallback), and `tests/test_server.py`.

The three protections behaved as designed. The read-only guard refused the deny-listed statement types structurally — nested-comment prefixes, leading semicolons, mixed case and the no-space `truncate"t"` form were all rejected, while the same keywords used as aliases or string literals ran fine. Ordinary writes are deliberately passed through and were stopped by the `BEGIN READ ONLY` wrapper with `ERROR: transaction is read-only`; I confirmed afterwards that nothing persisted. The transaction breaker rolled back a whole read-write transaction when a later statement failed, discarding an earlier successful `INSERT`, and dropped the name so a subsequent commit was refused rather than reporting success. Failed user SQL surfaced the engine's own message in every case, including full Redshift detail blocks, and the connection stayed usable.

Three things I could not reach. The `rw_*` confirmation round trip is unobservable from this client, so only the fail-closed branch was exercised, as the harness README says. I did not drive `MAX_OPEN_TRANSACTIONS_PER_TARGET` to its limit, since that means holding ten live connections; the duplicate-name gate that shares the same code path was verified. Idle-transaction expiry was not waited out.

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] Reading sql_guard.py:1, consts.py:1

[tool] status: Completed

[tool] Reading test_sql_guard.py:1

[tool] status: Completed

[tool] Running: grep -n '^class ' tests/test_redshift.py tests/test_server.py tests/test_review_executor.py | sed 's/:.*class /: /'

[tool] status: Completed

[tool] Running: awk '/^class TestRedshiftTransactionManager|^class TestResolveTransaction|^class TestTransactionLifecycle|^class TestTransactionsNeedTheBatch|^class TestBatchDeniedDetection|^class TestCompatibilit...

[tool] status: Completed

[tool] Running: grep -rn 'breaker\|MAX_OPEN_TRANSACTIONS\|aborted\|is unknown\|too many' awslabs/redshift_mcp_server/redshift.py | head -40

[tool] status: Completed

[tool] Reading redshift.py:331-390, redshift.py:651-740, redshift.py:801-860

[tool] status: Completed

[tool] Running: grep -n '_FALLBACK_NO_BATCH\|def _no_batch_active\|def _latch_no_batch\|def _is_no_batch' -A 12 awslabs/redshift_mcp_server/redshift.py | head -80

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] Running: grep -n 'subnetIds\|vpc_id' awslabs/redshift_mcp_server/redshift.py

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

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

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

[tool] Running: @awslabs.redshift-mcp-server/list_tables

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/list_tables

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Reading redshift.py:571-630

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed
