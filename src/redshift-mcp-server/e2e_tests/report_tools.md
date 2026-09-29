# End-to-end test: Every tool, both warehouse types

2026-09-26 00:17 UTC

- **Scenario**: `tools`
- **Code under test**: `feat/redshift-session-redesign` at `6f2ec534`, uncommitted changes
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 9.1 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| list_clusters | PASS | Both harness warehouses found with correct type, status and tags; also works on denied-batch credentials, which do not use the Data API. |
| list_databases | PASS | Identical on both warehouses: `dev` as local, three auto-mounted catalogs. |
| list_schemas | PASS | Four schemas on both, `tickit` among them. An auto-mounted catalog fails with Redshift's refusal to connect, as documented. |
| list_tables | PASS | Same seven TICKIT tables on both; unknown schema returns an empty list. |
| list_columns | PASS | Same ten `sales` columns and types on both; unknown table returns an empty list. |
| execute_query | PASS | Reads, typing, row cap, read-only guard, transaction breaker, named transactions, write confirmation, denied-batch fallback and failed user SQL all behaved as documented. |
| review_cluster | PASS | 48 signals / 12 findings provisioned; 32 signals / 3 findings serverless, with provisioned-only diagnostics skipped and `ServerlessScaling` run instead. |

- Both warehouses hold identical seeded data (424,309 rows), and every check that held on one held on the other.
- A `CREATE TABLE` in read-only mode is not deny-listed: it passes the guard and is stopped by `BEGIN READ ONLY` with `ERROR: transaction is read-only`. Verified nothing persisted.
- A pre-send refusal leaves a named transaction open and usable; a refusal from a statement that ran releases it and discards what it staged. Both confirmed against row counts.
- `rw_` write confirmation cannot complete a round trip from this CLI, which does not advertise MCP elicitation, so only the fail-closed branch was exercised; `rwu_` covered writes once allowed through.
- Not exercised: SQL over the 65,536-character limit, and `review_cluster` on the denied-batch fallback.

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

I'll start by looking at the unit tests to understand what behaviours to cover.Cluster discovery works. Now catalog exploration on both warehouses.Catalog and reads agree across both warehouses. Now the read-only SQL guard.Now the read-write path, which needs actual writes on the harness warehouses.Read-only transaction, then the denied-batch fallback configurations.Cleaning up the probe tables I created.All seven tools exercised against both warehouses. Findings:

Catalog exploration is consistent across the two warehouses — same four databases (one local, three auto-mounted catalogs), same four schemas, the same seven TICKIT tables, the same ten `sales` columns with matching types. Row counts are identical on both: 424,309 rows total (users 49,990 / venue 202 / category 11 / date 365 / event 8,798 / listing 192,497 / sales 172,456). Unknown schemas and tables return empty lists rather than errors; an auto-mounted catalog is listed by `list_databases` but `list_schemas` on it fails with Redshift's own refusal to connect, as documented.

Value typing matches the contract exactly: SMALLINT/INTEGER/BIGINT as integers, REAL/DOUBLE as floats, boolean as boolean, NULL as null, and DECIMAL, dates, times, timestamps and SUPER as strings. VARBYTE `'ab'` came back as `YWI=`, base64 as stated.

The read-only guard refused UNLOAD, GRANT, VACUUM, TRUNCATE, SET, `set_config(...)` and PREPARE by name, and refused multi-statement input, comment-only input and unparseable SQL. A `CREATE TABLE` is not on the deny-list, so it passed the guard and was then stopped by the engine — `ERROR: transaction is read-only` — and `pg_tables` confirmed nothing was left behind. Deny-listed words used as quoted identifiers and string literals were not matched, so classification is structural rather than textual.

The transaction breaker held at every configuration: COMMIT, ROLLBACK, BEGIN, START and ABORT were all refused as SQL. In read-only mode the refusal keeps the read-only wording; in read-write mode it names the four transaction parameters instead. `TRUNCATE` inside a named transaction was refused with its own explanation, and because that refusal happens before the statement is sent, the transaction stayed open and rolled back cleanly afterwards.

Named transactions behaved correctly on both warehouses. A rollback on the provisioned cluster discarded its insert and freed the name; a two-statement commit on Serverless persisted both rows. A statement that failed while opening a transaction reported that the transaction was not opened; a statement that failed inside an open one released it, discarded the staged insert, and the name was then reported unknown with the full list of reasons it could be gone.

Write confirmation fails closed as designed: `rw_` ran a read unconfirmed but refused `CREATE TABLE`, saying the client cannot prompt and naming `UNSAFE_SKIP_WRITE_CONFIRMATION` as the alternative. `rwu_` executed writes, DDL and DML directly.

The denied-batch fallback served reads on both warehouses, against user tables and through the catalog tools, and its query IDs carry no batch-index suffix, which is how the path shows. It refused named transactions and refused writes even at read-write mode, each with the message that says when the denial was seen and when a grant takes effect. The read-only guard still applies on that path.

`review_cluster` returned 48 signals and 12 findings on the provisioned cluster, and 32 signals and 3 findings on Serverless, where `NodeDetails`, `WLMConfig`, `WorkloadEvaluation` and `CopyPerformance` were skipped and `ServerlessScaling` ran instead — the provisioned-only skip works.

The row cap refuses rather than truncates: 1,000 rows returned fine, 1,001 was refused with the count named. A 1,001-row result of 4 KB strings (about 4 MB, certainly several Data API pages) was counted to exactly 1,001, so paging is read to its end before the limit is applied.

I created and dropped `public.e2e_probe` on both warehouses; both are back to their seeded state. The pre-existing `public.mcp_demo_rows` on Serverless is not mine and was left alone.

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] Reading sql_guard.py:1

[tool] status: Completed

[tool] status: Completed

[tool] Running: grep -h '^\s*\(async \)\?def test' tests/test_sql_guard.py tests/test_transactions.py | sed 's/(.*//' | sed 's/^\s*//' | head -200

[tool] Running: grep -h '^\s*\(async \)\?def test' tests/test_server.py tests/test_redshift.py tests/test_catalog.py tests/test_clusters.py | sed 's/(.*//' | sed 's/^\s*//' | wc -l; grep -h 'class Test' tests/test...

[tool] status: Completed

[tool] status: Completed

[tool] Running: grep -n 'class TestTransactionsNeedTheBatch' -A 60 tests/test_redshift.py | head -80; echo ====; grep -n 'class TestCompatibilityPathRouting' -A 50 tests/test_redshift.py | head -60

[tool] status: Completed

[tool] Running: grep -n 'no_batch\|fallback' awslabs/redshift_mcp_server/redshift.py | grep -in 'refus\|cannot\|raise\|ToolError' | head -30

[tool] status: Completed

[tool] Running: grep -n 'Named transactions need\|takes effect within\|read-only cannot be guaranteed\|BatchExecuteStatement' awslabs/redshift_mcp_server/redshift.py | head -30

[tool] status: Completed

[tool] Reading redshift.py:89-118

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: grep -n 'MAX_RESULT_ROWS\|MAX_SQL_LEN' awslabs/redshift_mcp_server/consts.py

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed
