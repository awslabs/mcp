# End-to-end test: Every tool, both warehouse types

2026-11-03 21:46 UTC

- **Scenario**: `tools`
- **Code under test**: `feat/redshift-guide-skill` at `f67f46ea`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 8.0 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| `retrieve_skill_file` | PASS | Guide served with no argument; single-chunk reference served; two-chunk reference served whole across both chunks with a continuation marker; an unlisted path refused, listing the 12 available files. |
| `list_clusters` | PASS | Both targets found and `available`, with correct types; serverless entries report `node_type`/`master_username` as null and are tagged. Other clusters in the account listed but not touched. |
| `list_databases` | PASS | Identical on both targets: `dev` as `local`, three `auto mounted catalog` entries, isolation level reported. |
| `list_schemas` | PASS | `tickit` present as `local` on both, alongside `public`, `pg_catalog`, `information_schema`. |
| `list_tables` | PASS | Same seven TICKIT tables on both; an unknown schema returned an empty list, not an error. |
| `list_columns` | PASS | `sales` identical on both, with types, precision/scale and nullability; an unknown table returned an empty list, not an error. |
| `execute_query` | PASS | Reads identical on both targets with values typed per contract (ints as integers, DECIMAL and timestamps as strings, booleans as booleans, NULL as null). Empty result and no-result-set statements returned cleanly. Read-only protection, transaction breaker, multi-statement rejection, result cap and failed-SQL reporting all correct. Writes persisted under `rwu_`; `rw_` refused the write because the client cannot prompt. |
| `review_cluster` | PASS | 48 signals and 11 findings on the provisioned cluster; 32 signals and 2 findings on the Serverless workgroup, with provisioned-only sections skipped and `ServerlessScaling` added. Both agreed on the two TICKIT table-design findings (7 tables each). |

- A write that is actually confirmed or declined stays uncovered: this client cannot prompt, so `rw_execute_query` refused the write and named the `UNSAFE_SKIP_WRITE_CONFIRMATION` opt-out. Refusing rather than running unconfirmed is the fail-closed outcome, but accept/decline still needs a person in an MCP client.
- Malformed SQL is caught locally (`SQL could not be parsed`) and never reaches the engine; genuine engine failures (missing relation, divide by zero) pass through with Redshift's own message intact.
- On the batch-denied configurations, a read fell back to single-statement execution and returned correct data, while a write was refused naming `redshift-data:BatchExecuteStatement` and the re-probe window.
- I created two scratch tables in `public` (one per warehouse) for the write tests and dropped both. The seeded `tickit` data was not modified.

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

I'll start by loading the server's guide as instructed, and look at the project's unit tests for scenario ideas.Let me pull scenario ideas from the unit tests and the e2e scenario definitions.list_clusters and the guide work. Now the multi-chunk reference, a refused path, and schema exploration on both warehouses.retrieve_skill_file is solid. Now the catalog tools on both warehouses.Both expose `tickit`. Now tables and columns on both, plus an unknown-schema check.Same seven tables on both. Now columns.Catalog tools agree across both. Now `execute_query` reads, including value typing.Cap is 1000 rows by default. Now the result-size cap, an empty result, a statement with no result set, and failed user SQL.Cap boundary is right. Now the SQL guard: denylisted statements, transaction control, multi-statement, and malformed SQL.Read-only protection holds both ways. Now the transaction breaker, in both modes.Now failed user SQL and empty results.Now named transactions — a read-only one on the provisioned cluster, opened and closed in one stretch.Now that a failed statement aborts its transaction, and that a name is bound to its target.Now a statement that fails inside the transaction, and whether the name is then dropped.Now the write paths. First a read in read-write mode, then a write that needs confirmation.Now the unconfirmed write path. I'll use a new scratch table in `public` and drop it afterwards, leaving the seeded `tickit` data untouched.Now a read-write transaction that gets rolled back.Now the commit path, on the Serverless workgroup.Cleaning up the two scratch tables I created (both disposable, created in this run).Now target resolution: a wrong type and an unknown cluster.Now `review_cluster` on both warehouses. This takes a few minutes each.Two supplementary checks on the batch-denied configurations, since the same tool is exercised there.All eight tools exercised against both warehouse types, with no tracebacks in any server log. Highlights beyond the pass/fail rows:

**Read-only protection** works by two distinct mechanisms, both verified. Statements a read-only transaction cannot neutralize (`VACUUM`, `GRANT`, `SET`, `ANALYZE`) are rejected before execution; an ordinary `UPDATE` passes the guard and is then refused by the engine with `ERROR: transaction is read-only`, so the data is never modified either way.

**The transaction breaker** refuses `BEGIN`, `COMMIT` and `ROLLBACK` in `sql` in both modes. In read-write mode the refusal names the four transaction parameters to use instead; in read-only mode the read-only list catches it first and reports it as a disallowed statement type. A comment plus a leading semicolon did not smuggle `ROLLBACK` past it, and multi-statement submissions were rejected in both modes.

**Named transactions** behaved correctly across every case I could reach: a snapshot held over three calls, a committed write persisting, a rolled-back write discarded, a failed statement releasing the name so nothing could be committed on it afterwards, a guard refusal leaving the transaction open, reopening an open name refused, and the same name on the other warehouse treated as a different (unknown) transaction. `TRUNCATE` inside a named transaction was refused with the reason.

**Result cap** is exact: 1000 rows returned whole, 1001 refused outright with the remedy named rather than silently truncated.

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Reading scenarios.py:1

[tool] Running: cd [package root] && grep -ho 'def test_[a-z0-9_]*' tests/test_sql_guard.py tests/test_transactions.py | sed 's/def //' | sort

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd [package root] && grep -ho 'def test_[a-z0-9_]*' tests/test_server.py | sed 's/def //' | sort | head -120

[tool] Running: cd [package root] && grep -ho 'def test_[a-z0-9_]*' tests/test_redshift.py tests/test_catalog.py tests/test_clusters.py | sed 's/def //' | sort | h...

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] status: Completed

[tool] status: Completed

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

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd [package root] && cat e2e_tests/config.toml && sed -n '1,80p' e2e_tests/agent.py | grep -n -A40 'SERVERS'

[tool] status: Completed

[tool] Running: cd [package root] && sed -n '60,150p' e2e_tests/agent.py

[tool] status: Completed

[tool] Running: cd [package root] && grep -n -i 'MAX_RESULT_ROWS\|MAX_SQL\|SESSION_KEEPALIVE\|MAX_OPEN_TRANS' awslabs/redshift_mcp_server/consts.py awslabs/redshif...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd [package root]/e2e_tests/.logs && for f in *.log; do echo "== $f"; grep -c 'Traceback' "$f" 2>/dev/null; tail -c 400000 "$f" | grep -o 'CRITICAL...

[tool] status: Completed

[tool] Running: cd [package root]/e2e_tests/.logs && tail -c 200000 awslabs.redshift-mcp-server-no-batch.log | grep -i 'batch\|fall' | tail -8

[tool] status: Completed
