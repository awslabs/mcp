# End-to-end test: Every tool, both warehouse types

2026-09-14 21:41 UTC

- **Scenario**: `tools`
- **Code under test**: `feat/redshift-session-redesign` at `44a721b5`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 16.2 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| list_clusters | PASS | Both harness warehouses listed as available alongside unrelated clusters; unaffected by the batch denial, as it uses the Redshift control-plane APIs |
| list_databases | PASS | Identical on both warehouses; lists the Glue auto-mounted catalogue, which is expected to be unexplorable |
| list_schemas | PASS | Identical on both warehouses; fails with a clear FATAL on the auto-mounted `awsdatacatalog`, as documented |
| list_tables | PASS | Same seven TICKIT tables on both warehouses; unknown schema returns an empty list, not an error |
| list_columns | PASS | Column metadata for `tickit.sales` matches across both warehouses; unknown table returns an empty list |
| execute_query | PASS | Reads, value typing, read-only protection, the transaction breaker, named transactions and failed-SQL behaviour all correct on both warehouses across all five configurations |
| review_cluster | PASS | 11 findings over 11 signals on provisioned; 8 signals on Serverless with node and WLM diagnostics skipped and `ServerlessScaling` added; same result through the fallback path |

- Read-only rests on two independent layers, and both were observed: the deny-list refuses `UNLOAD`, `GRANT`, `TRUNCATE`, `VACUUM` and `SET` before execution, while `INSERT`, `CREATE TABLE`, `SELECT … INTO` and a data-modifying CTE reach the engine and fail on `transaction is read-only`. Nothing persisted in either case.
- `rw_` never completes a confirmation round trip, because the agent CLI does not advertise elicitation. The write was refused with an actionable message and created nothing, which exercises the fail-closed branch only; a confirm and a decline remain unreachable from this client.
- `rwu_` writes persisted, a committed transaction landed both of its rows, and a rolled-back one landed neither.
- The `query_id` sub-statement suffix distinguishes the three execution paths (`:3` read-only wrapped, `:2` read-write unwrapped, none on the fallback), which is useful evidence when reading a transcript.
- Oversized SQL (over 65,536 characters) was not exercised: sending it would mean putting 64 KB into a tool argument. It remains covered by the unit suite only.
- Scratch objects created for the write tests were dropped, and the seeded TICKIT data was verified unchanged on both warehouses afterwards.

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

I'll start by looking at the unit tests to understand what behaviours to check.Now I have the scenario ideas. Starting with cluster discovery.Both harness warehouses are available. Now schema exploration on both.Same seven tables on both. Now columns.Both degrade to an empty list as documented. Now reads through `execute_query` on both warehouses.Typing matches the contract, including a BIGINT past float precision. Now failed user SQL.Both report the caller's own error rather than the wrapper's. Now the read-only protection.The deny-list holds. Now the other half of read-only: a write that passes the guard and must be neutralized by the read-only transaction.Nothing persisted. Now the guard's structural classification: keywords used as identifiers must not be matched by text.The guard passed it through — Redshift itself rejects the bare reserved word. Retrying with quoted identifiers so the statement actually runs.Structural classification confirmed. Now multi-statement, unparseable and comment-smuggling input.Now the transaction control breaker — it must refuse in every access mode, including read-write.The read-write refusal names the parameters. Checking the other forms, including the ones sqlglot parses as bare identifiers.My input had escaped the inequality operator. Retrying.The `:3` vs `:2` sub-statement ids corroborate that the `BEGIN READ ONLY` wrapper is applied only in read-only mode. Now the `rw_` configuration, where writes must be confirmed.Fail-closed confirmed. Now `rwu_`, where writes run unconfirmed. I'll work in a scratch schema and clean up after.Writes persist and are visible from the read-only server. Now transactions — starting with a read-only snapshot on Serverless.Sent bare on its session (`:1`). Now checking the guard still applies inside the open transaction, and that a rejection leaves it open.The transaction survived the rejection. Now closing it, and confirming a closed name is gone.The refusal enumerates every way it could be gone. Now a read-write transaction that rolls back.Rollback discarded the insert. Now a transaction that commits, on Serverless.Both rows committed. Now a failed statement inside a transaction, which should roll it back and drop the name.Now the no-batch fallback. Reads should still work through the single-statement compatibility path.No sub-statement suffix on the query id, consistent with the single-statement path. Confirming the denial is genuinely what triggered it.The latch fired on an explicit session-policy deny and the read fell back within the same call. Now schema exploration through the fallback.Now the fallback's own refusal — a write that the deny-list does not name, so the missing wrapper is the reason.Now named transactions, which need the batch path and must be refused while latched.The name was never claimed. Now `review_cluster` on both warehouses.11 findings on the provisioned cluster. Now Serverless, where provisioned-only diagnostics should be skipped.Provisioned-only diagnostics were skipped and `ServerlessScaling` added. Now the same tool through the fallback path.A few remaining behaviours: allow-listed read commands, write classification of read-shaped statements, and error paths.Now read-shaped statements that actually write — the classifier must not be fooled.Now the error paths: an unknown cluster and an unexplorable auto-mounted catalog.Now cleaning up the scratch objects I created.All seven tools are covered on both warehouses across all five configurations, and the scratch objects are gone with TICKIT intact.

What the run established:

Discovery returned identical results on the provisioned cluster and the Serverless workgroup — same four databases, same four schemas, same seven TICKIT tables, same column metadata for `sales`. Unknown schemas and tables degrade to an empty list rather than an error, and the Glue auto-mounted `awsdatacatalog` is listed by `list_databases` but refuses connection from `list_schemas`, both as documented.

Read-only protection works in two distinct layers. The deny-list refuses `UNLOAD`, `GRANT`, `TRUNCATE`, `VACUUM` and `SET` before anything executes. Writes the deny-list does not enumerate — `INSERT`, `CREATE TABLE`, `SELECT … INTO`, a `DELETE` inside a CTE fronted by a `SELECT` — pass the guard and are stopped by the engine with `transaction is read-only`; I confirmed afterwards that nothing persisted and `tickit.category` still holds 11 rows with max catid 11. Classification is structural: deny-listed words as quoted identifiers and string literals ran fine, while a nested comment attempting to smuggle a `VACUUM` was rejected as unparseable.

The transaction breaker refused `BEGIN`, `COMMIT`, `START TRANSACTION` and `ABORT` in both access modes. In read-write mode the refusal names the four parameters to use instead; in read-only mode the deny-list wording arrives first, which matches the precedence in the guard. `TRUNCATE` inside a named transaction was refused with its own explanation.

Failed user SQL reports the caller's own error rather than the wrapper's — a missing relation and a divide-by-zero both surfaced the engine message. Inside a named transaction a failed statement rolled the transaction back and dropped the name, and the `99` row it had inserted was gone.

A side observation worth keeping: the sub-statement suffix on `query_id` makes the execution path visible. Read-only reads return `:3` (app-name, `BEGIN READ ONLY`, caller, `ROLLBACK`), read-write reads return `:2` (no wrapper), and fallback reads have no suffix at all. That corroborates the wrapper being applied only where it is needed.

The `nb_`/`nbw_` fallback was genuinely reached: the server log shows the latch firing on an explicit session-policy deny of `BatchExecuteStatement`, and the read then completed on the compatibility path within the same call. All five discovery tools and `review_cluster` work there; writes and named transactions are refused with messages specific to each, and a refused open never claimed the name.

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] Reading sql_guard.py:1, consts.py:1

[tool] status: Completed

[tool] Running: grep -h '^def test_\|^async def test_\|^    async def test_\|^    def test_' tests/test_sql_guard.py | sed 's/(.*//' | head -100

[tool] status: Completed

[tool] Running: grep -h 'def test_\|^class ' tests/test_redshift.py | sed 's/(.*//' | sed 's/^ *//' | head -200

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

[tool] Running: grep -n 'READ ONLY\|ROLLBACK\|_WRAP\|wrapper' awslabs/redshift_mcp_server/redshift.py | head -40

[tool] status: Completed

[tool] Reading redshift.py:571-630

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

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: grep -i 'batchexecute\|AccessDenied\|compatibility\|fallback\|latch' e2e_tests/.logs/awslabs.redshift-mcp-server-no-batch.log | tail -5

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] status: Completed
