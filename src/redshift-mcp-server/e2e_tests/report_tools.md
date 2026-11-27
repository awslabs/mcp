# End-to-end test: Every tool, both warehouse types

2026-11-13 23:29 UTC

- **Scenario**: `tools`
- **Code under test**: `fix/redshift-read-only-transaction-rollback` at `8998a9d0`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 8.2 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| retrieve_skill_file | PASS | Guide served with no argument; `references/redshift-sql-metadata.md` whole; `references/redshift-storage-utilization.md` joins correctly across both chunks; `references/../consts.py` refused with the list of available files. |
| list_clusters | PASS | Both targets listed `available` with correct types; other clusters in the account listed and left alone. |
| list_databases | PASS | Identical on both warehouses; `dev` as `local`, Glue and S3 Tables catalogs as `auto mounted catalog`. |
| list_schemas | PASS | `tickit` present on both. Wrong `cluster_type` for a known target refused: "No provisioned cluster named mcp-e2e-serverless was found. Found instead: a serverless one." |
| list_tables | PASS | Same 7 TICKIT tables on both; unknown schema returns an empty list, not an error. |
| list_columns | PASS | `tickit.sales` identical on both (10 columns, types and nullability); unknown table returns an empty list. |
| execute_query | PASS | Same aggregate result on both warehouses; read-only guard, transaction breaker, named transactions, MAX_RESULT_ROWS refusal (5000 rows over a limit of 1000) and failed user SQL all behaved as the unit tests specify. Confirmation-accepted and confirmation-declined paths not reachable from this client. |
| review_cluster | PASS | Provisioned: 48 signals, 10 findings. Serverless: 32 signals, 3 findings, with the provisioned-only diagnostics (NodeDetails, WLMConfig, CopyPerformance, WorkloadEvaluation) skipped and ServerlessScaling added. |

- A write at `rw_` was refused with "This MCP client cannot prompt for confirmation... or set UNSAFE_SKIP_WRITE_CONFIRMATION=true" — correct fail-closed behaviour, but it means accept/decline of a confirmation prompt stays a manual check, as `e2e_tests/README.md` states.
- Writes were exercised only at `rwu_`, only on scratch objects of my own (`public.e2e_tx_probe`, `public.e2e_trunc_probe`), and both are gone; `svv_table_info` shows no `e2e_%` tables and no transaction was left open.
- `EXPLAIN DELETE FROM tickit.sales` returned `permission denied for relation sales`: the e2e database user holds SELECT only on `tickit`. That is the cluster's grants, not a server defect, and `EXPLAIN SELECT` returned a plan normally.
- Spot-checked the batch-denied configuration (`nb_execute_query`, `nb_list_tables`): both answered correctly, with `query_id` carrying no statement suffix, consistent with the non-batch path.

## Prompt

Written by the harness, not by hand, and never says what to expect.

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

I'll start by retrieving the guide as the tools require, and look at the project's unit tests for scenario ideas.

list_clusters works; both targets are present with the right types. Now schema exploration on both warehouses.

Identical on both. Now the documented empty-list behaviour and the wrong-type refusal.

Now the read-only SQL guard. Batching the deny-list cases drawn from `test_sql_guard.py`.

Named transactions next. A read-only transaction across calls on the provisioned cluster:

Now the transaction breaker in read-write mode, at the configuration that runs writes unconfirmed.

Now the other half of the breaker: TRUNCATE outside a transaction is an honest write in read-write mode. Using a scratch table of my own.

Now the confirmation path at the configuration that asks before a write.

`retrieve_skill_file` serves the reference whole across its two chunks. Now `review_cluster` on both warehouses.

Every tool was exercised against both `mcp-e2e-provisioned` and `mcp-e2e-serverless`, with the guard, transaction and failure cases drawn from `tests/test_sql_guard.py`, `tests/test_transactions.py` and `tests/test_server.py`.

What the run covered beyond the happy paths:

**Read-only guard.** `COMMIT`, `TRUNCATE"tickit.sales"`, `set_config('transaction_read_only','off',false)`, `pg_terminate_backend(pid) FROM stv_sessions` and the nested-comment prefix `/* a /* b */ SELECT 1 FROM */ TRUNCATE pwned` were each refused by statement type; `SET ...; CREATE TABLE ...` as "Only a single SQL statement is allowed"; `/* nothing here */ ;` as "sql holds no statement to execute"; `SELECT FROM WHERE` as "SQL could not be parsed". No false positives: `SELECT '; COMMIT;' AS literal, 1 AS grant, $$ a ; COMMIT ; b $$` returned its three values. The engine backstop held too — `CREATE TABLE public.ro_backstop_probe` passed the guard and came back "ERROR: transaction is read-only", and the table does not exist.

**Transaction breaker.** `COMMIT` at `rw_` and `BEGIN TRANSACTION` at `rwu_` were both refused with "Transaction control is not available to a statement", naming the four parameters. Inside the named transaction `brk`, `TRUNCATE` and `CALL` were refused as statements that "can commit the transaction it runs in", and the transaction survived both refusals: a `CREATE TABLE` and an `INSERT` staged inside it afterwards, then `rollback_transaction` discarded both and `svv_table_info` shows nothing. Outside a transaction the same `TRUNCATE` ran on a scratch table of mine and emptied it, so the refusal is scoped rather than blanket. A failed statement inside `failtx` released it ("nothing it staged can be committed") and the name could then be opened again.

**Named transaction mechanics.** A read-only transaction on the provisioned cluster kept one session across three calls (`transaction_read_only` = `on` inside it), `commit_transaction` ended it, and the name afterwards reported "No open transaction named 'snap' on mcp-e2e-provisioned (provisioned):dev". Two closer parameters in one call were refused.

**Failed user SQL** reached the caller intact in three shapes: `relation "tickit.no_such_table_xyz" does not exist`, `division by zero`, and `permission denied for relation sales` (that last from `EXPLAIN DELETE` at `rwu_`, where the database user holds only SELECT on `tickit` — `EXPLAIN SELECT` returned a plan, so EXPLAIN itself is still classed as a read).

One behaviour I could not drive to completion: a write at `rw_` was refused with "This MCP client cannot prompt for confirmation", which the e2e README lists as unreachable in a run. Accepting or declining a prompt needs the manual client check.

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: pwd && ls

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd .. && ls && ls tests/ && wc -l tests/* e2e_tests/scenarios.py

[tool] status: Completed

[tool] Reading test_sql_guard.py:1, scenarios.py:1

[tool] status: Completed

[tool] Running: cd [package root] && grep -n "^class \|def test_" tests/test_server.py | head -120 && echo ---- && grep -n "^clas...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

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

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed
