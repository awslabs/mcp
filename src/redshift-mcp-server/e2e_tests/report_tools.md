# End-to-end test: Every tool, both warehouse types

2026-11-05 02:23 UTC

- **Scenario**: `tools`
- **Code under test**: `feat/redshift-guide-skill` at `6d01b634`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 11.6 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| retrieve_skill_file | PASS | Guide served with no argument; the 2-chunk `references/redshift-storage-utilization.md` served in full, across two configurations. |
| list_clusters | PASS | Both test warehouses found with correct types (`mcp-e2e-provisioned` provisioned, `mcp-e2e-serverless` serverless); other account clusters listed only, never touched. |
| list_databases | PASS | Both warehouses; `dev` typed `local` and the Glue/S3 Tables catalogs typed `auto mounted catalog`. An unknown cluster id is refused naming `list_clusters` and the discovery age. |
| list_schemas | PASS | Both warehouses return the same 4 schemas including `tickit`. An auto-mounted catalog fails with Redshift's own "cannot connect to shared database" error, as documented. |
| list_tables | PASS | Same 7 TICKIT tables on both, all `TABLE`. Unknown schema returns an empty list, not an error. Naming the provisioned cluster as `serverless` is refused and says what was found instead. |
| list_columns | PASS | `tickit.sales` returns the same 10 columns with identical types, precision and nullability on both warehouses. Unknown table returns an empty list. |
| execute_query | PASS | Reads correct and identical on both warehouses; typing correct for every class (ints, floats, bool, null, VARCHAR/DECIMAL/date/timestamp/SUPER as strings, VARBYTE base64). Row cap pinned from both sides: 1000 rows returned in full, 1001 and 172,456 refused whole. Guard, READ ONLY wrapper, named transactions (commit, rollback, cross-target isolation, abort-on-failure), the TRUNCATE/CALL breaker, and the batch-denial refusals all behaved as the unit tests specify. |
| review_cluster | PASS | Provisioned: 48 signals, 11 findings, 11 queries. Serverless: 32 signals, 2 findings, with `NodeDetails`, `WLMConfig`, `WorkloadEvaluation` and `CopyPerformance` skipped and `ServerlessScaling` added. Byte-identical result under batch-denied credentials. |

- Accepting or declining a write confirmation was not reachable: this client cannot elicit, so `rw_execute_query` refused the write with the documented message pointing at elicitation or `UNSAFE_SKIP_WRITE_CONFIRMATION`. That refusal path is verified; the accept and decline paths need a person in an MCP client.
- Also not reachable in this run, and so untested here: SQL over the 65,536-character limit, and the batch-denial latch's re-probe finding the action granted.
- Observation, not a failure: in read-only mode `COMMIT` is refused with `Statement type not allowed in read-only mode: COMMIT`, which does not mention the transaction parameters, while the same statement in read-write mode does name them. Read-only named transactions are supported and worked, so a user who reaches for `COMMIT` in the default configuration is not told the supported route exists.
- Write testing used a scratch table `public.e2e_probe` on the provisioned cluster, created and dropped within the run. Final check confirms no `e2e_*` table remains and `tickit.sales` still holds 172,456 rows.

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

I'll start by loading the required guide and exploring the project's unit tests for scenario ideas.Now let me mine the unit tests for scenario ideas.Guide loaded. Now the inventory and the `retrieve_skill_file` chunking path.`list_clusters` and `retrieve_skill_file` work. Now schema exploration on both warehouses.`execute_query` reads, typed values, and the result-size cap.Reads and typing are correct, and the row cap refuses rather than truncates. Now the read-only SQL guard.Read-only guard holds. Now a read-only named transaction across calls.Now read-write mode. A read at `rw_*` should run unconfirmed; a write should require confirmation.`rw_*` correctly refuses rather than running unconfirmed. Now `rwu_*`, where writes run unconfirmed. I'll use a scratch table in `public` and drop it afterwards.Now the transaction breaker in read-write mode. I'll run the whole transaction in one stretch: stage an insert, probe the breaker, roll back.TRUNCATE outside a transaction on the scratch table I created for this test (`public.e2e_probe`, 3 rows, disposable — the rows are unrecoverable, which is the point of the check):Now the batch-denied configurations, in parallel.Cleaning up the scratch table, then the cluster review on both targets.Review works on both and correctly skips provisioned-only diagnostics on Serverless. A few remaining paths:One boundary check left: the result-row cap from both sides.All checks are done and the sandbox is back to its starting state (scratch table dropped, TICKIT row counts unchanged).

What the run covered, in brief:

- **Both warehouse types** for every target-taking tool, with `tickit` explored end to end on each: same 4 schemas, same 7 tables, same 10 columns on `tickit.sales`, and identical aggregate results from a three-table join (Pop/Plays/Musicals/Opera, 172,456 sales rows).

- **Read-only protection** at two levels. The guard refuses `COMMIT`, `TRUNCATE`, `UNLOAD`, `GRANT`, `VACUUM`, `SET`, multi-statement input, empty input and unparseable SQL. Writes the guard lets through (`INSERT`, `CREATE TABLE`) are then neutralized by the `BEGIN READ ONLY` wrapper, and I confirmed neither left a trace. The nested-comment bypass regression holds: the same prefix is refused before `TRUNCATE` and allowed before a benign `SELECT`.

- **Transaction breaker.** `BEGIN` in `sql` is refused in read-write mode and points at the four transaction parameters. Inside an open named transaction, `TRUNCATE` and `CALL` are both refused as implicit committers, the transaction stays open and usable, and a subsequent rollback genuinely discarded the staged row, which is what the breaker exists to protect.

- **Failed user SQL.** A missing relation, a missing column and an unparseable statement each surface the right error. A failure inside a named transaction releases it, and the next call reports the name as unknown rather than letting a commit silently do nothing.

- **Batch-denied credentials.** Reads fall back to the single-statement path (visible in the `query_id`, which carries no sub-statement suffix), discovery and the cluster review work unchanged, and transactions and writes are refused with messages naming `redshift-data:BatchExecuteStatement`.

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd [package root] && grep -h "^def test_\|^async def test_" tests/test_sql_guard.py tests/test_transactions.py | head -120

[tool] Running: cd [package root] && grep -h "^def test_\|^async def test_" tests/test_catalog.py tests/test_clusters.py tests/test_server.py | head -160

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd [package root] && grep -ho "def test_[a-z0-9_]*" tests/test_sql_guard.py | sort -u

[tool] Running: cd [package root] && grep -ho "def test_[a-z0-9_]*" tests/test_transactions.py tests/test_catalog.py | sort -u

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd [package root] && sed -n '1,120p' tests/test_sql_guard.py

[tool] Running: cd [package root] && grep -n "transaction_control_is_rejected\|truncate_is_rejected\|egress_dcl_maintenance\|multi_statement_is_rejected\|the_refus...

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd [package root] && cat awslabs/redshift_mcp_server/consts.py && echo "=== BATCH LATCH ===" && grep -n "Batch\|batch" awslabs/redshift_mcp_server/...

[tool] Running: cd [package root] && cat e2e_tests/scenarios.py

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server-no-batch/retrieve_skill_file

[tool] status: Completed

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/list_databases

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

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

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
