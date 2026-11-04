# End-to-end test: Changes on this branch

2026-10-01 21:55 UTC

- **Scenario**: `branch`
- **Code under test**: `feat/redshift-session-redesign` at `aa1073db`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 15.3 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| `cluster_type` required on every cluster tool | PASS | Omitted or empty value refused by the schema on `execute_query` and `list_columns` before any AWS call. |
| Invalid `cluster_type` value refused, not guessed | PASS | `Provisioned` rejected as a literal error; only `provisioned`/`serverless` accepted. |
| Name present as the other type is refused, not silently redirected | PASS | `No serverless cluster named mcp-e2e-provisioned was found. Found instead: a provisioned one.` |
| Unknown identifier refused with guidance | PASS | Points at `list_clusters`. |
| Refusal states the age of the stored discovery | PASS | "last looked up 10 seconds ago"; after `list_clusters` the same refusal reported 3 seconds, so the listing refreshes it. |
| Identifier plus type reaches that warehouse and no other | PASS | A schema created on the provisioned cluster is absent from the workgroup under the same database name. |
| Write confirmation names the warehouse the statement would reach | PASS | `rw_*` log: `Refused a write on mcp-e2e-provisioned (provisioned):dev`, built from the call's own arguments. |
| `MAX_RESULT_ROWS` at the cap | PASS | 1000 rows returned, `row_count` 1000, last row present — read to the end across pages. |
| `MAX_RESULT_ROWS` one row over the cap | PASS | `The result has 1001 rows, over the MAX_RESULT_ROWS limit of 1000, so none of it is returned`, with advice on shaping a smaller result. |
| `MAX_RESULT_ROWS` on a large result, both warehouse types | PASS | 172456-row result refused whole on the workgroup; cap and wording identical on the provisioned cluster. |
| Row cap on the batch-denied single-statement path | PASS | Same refusal at 1001 rows, same full read at 1000, through `ExecuteStatement`. |
| Session-control functions refused in read-only mode | PASS | All six refused by name: `SET_CONFIG`, `PG_CANCEL_BACKEND`, `PG_TERMINATE_BACKEND`, `CHANGE_QUERY_PRIORITY`, `CHANGE_SESSION_PRIORITY`, `CHANGE_USER_PRIORITY`. |
| Session-control functions classified as writes in read-write mode | PASS | `rw_*` sent `pg_terminate_backend` to the confirmation gate; `nbw_*` refused `change_user_priority` as a write. Neither ran. |
| Transaction control refused at every access mode | PASS | `COMMIT` refused at `rwu_*` naming the four transaction parameters; `BEGIN` refused at `ro_*` with the read-only wording. |
| A comment followed by a semicolon is nothing to run | PASS | `sql holds no statement to execute`, not the single-statement message. |
| Multi-statement submission refused | PASS | |
| `TRUNCATE` and `CALL` refused inside a named transaction | PASS | Both named in the refusal as able to commit the transaction they run in; both left the transaction open and usable. |
| `TRUNCATE` permitted standalone in read-write mode | PASS | Ran outside a transaction and the table was observably emptied. |
| Read-only protection holds for DML the guard passes through | PASS | `INSERT` at `ro_*` reached the engine and failed `transaction is read-only`. |
| Named transactions, open / statement / commit / rollback | PASS | Three concurrent transactions across both warehouses, each closed independently. |
| Transaction keys are per cluster, type and name | PASS | `load` on the cluster and `load` on the workgroup were separate; `load:step1` and `load` on one target were separate, and committing one left the other open. |
| Failed statement aborts its transaction and drops the name | PASS | Release reported with the engine error; the name then reported unknown, naming the target as `mcp-e2e-provisioned (provisioned):dev`. |
| A failed open reports the transaction was not opened | PASS | `Transaction 'bad' was not opened.` and the name was free to open again. |
| Reopening an open name refused | PASS | |
| Transactions are per server process | PASS | A name opened at `ro_*` is unknown at `rwu_*`. |
| Session state outside a transaction is lost | PASS | `CREATE TEMP TABLE` reported success, then the next call could not find the table; the same table inside a named transaction was usable across calls. |
| Batch-denied fallback serves reads | PASS | Reads against seeded user tables at both `nb_*` and `nbw_*`, on both warehouses. |
| Batch-denied fallback refuses writes at every access mode | PASS | Same refusal at read-only `nb_*` and at unconfirmed read-write `nbw_*`, naming the grant and the 300-second re-probe. |
| Batch-denied fallback refuses named transactions | PASS | Refused at both `nb_*` and `nbw_*`; latched per cluster, the workgroup independently of the cluster. |
| All four list tools work under the batch denial | PASS | `list_databases`, `list_schemas`, `list_tables`, `list_columns` served through `ExecuteStatement`. |
| `list_clusters` unaffected by the batch denial | PASS | Control-plane only. |
| `review_cluster` under the batch denial | PASS | Serverless workgroup reviewed through the fallback: 32 signals, provisioned-only diagnostics skipped, `ServerlessScaling` run. |
| `review_cluster` at the default configuration | PASS | Provisioned cluster: 48 signals evaluated, 12 findings. `signals_evaluated` counts signals, not rows. |
| Serverless workgroups report their tags | PASS | `mcp-e2e-serverless` reported `purpose=redshift-mcp-server-e2e-harness`; another workgroup in the account reported untagged. |
| Unknown schema or table returns an empty list | PASS | |

- The row cap was triggered on `execute_query` on both warehouse types and on the batch-denied path, at the cap and one row over. It was not independently triggered on `review_cluster` or the four list tools, because no reachable catalogue result on these warehouses exceeds 1000 rows; those paths share the same `_read_result` function, so the coverage is by shared code rather than by direct observation.
- `rw_*` never completes a confirmation round trip, as the harness documents: this CLI does not advertise MCP elicitation, so every write there is refused fail-closed. A confirm and a decline remain unobservable from this client.
- The `nbw_*` write refusals prove the ordering the branch intends: confirmation is consulted before the fallback, so the fallback's own explanation only surfaces at a configuration that skips confirmation.
- A denial of only one half of cluster discovery (provisioned or serverless listing) could not be exercised; the credentials here are denied `BatchExecuteStatement` only, so the "listing was denied" clause in the resolution refusal was not observed.
- All writes were confined to a `mcp_e2e_scratch` schema on the provisioned cluster, which was dropped; the seeded `tickit` schema was only read, and no transactions were left open.

## Prompt

Written by the harness, not by hand. The agent derives the cases from the package's unit tests, and is told where to look rather than what to expect.

You have the Redshift MCP server available at several configurations, each running the working tree you are testing. Every configuration exposes the same tools, distinguished by prefix, so `ro_execute_query` and `rw_execute_query` are the same tool at two configurations:
- `ro_*` — default configuration: read-only, which is what a user gets by installing it
- `rw_*` — ACCESS_MODE=read-write, so writes are permitted and each one is confirmed
- `rwu_*` — ACCESS_MODE=read-write with UNSAFE_SKIP_WRITE_CONFIRMATION=true, so writes run unconfirmed
- `nb_*` — default configuration, but its credentials are denied redshift-data:BatchExecuteStatement
- `nbw_*` — ACCESS_MODE=read-write with UNSAFE_SKIP_WRITE_CONFIRMATION=true, and its credentials are denied redshift-data:BatchExecuteStatement

Two warehouses are provisioned and seeded with the TICKIT sample schema `tickit` in database `dev`: provisioned cluster `mcp-e2e-provisioned` and Serverless workgroup `mcp-e2e-serverless`. Both hold the same tables, so a check that holds on one should hold on the other. Other clusters exist in this account; leave them alone.

Run an end-to-end test covering the scenarios for the changes introduced in the current branch only. Scope is the committed branch diff AND the uncommitted working-tree changes, so read `git status` and `git diff` as well as the branch commits: the newest behaviour may not be committed yet. Get the test scenario ideas from the unit tests under the project directory.

Some of the branch behaviour appears only when the AWS principal is denied a specific IAM action, which is what the denied configurations above are for. Work out from the diff and the unit tests what each tool should do under those credentials, and verify it. Verify too that behaviour under the configurations that are not denied it is unchanged.

End your reply with a section that begins on its own line with `## Summary` and holds nothing but,
in this order:

1. A markdown table with the columns Scenario, Result and Comment. One row per scenario. Result is
   PASS or FAIL. Leave Comment empty unless there is something to say.
2. Only if anything is worth noting, a short bulleted list under the table.

This section is lifted into a committed report and read on its own, so keep every row
intelligible without the rest of the reply.

## Transcript

I'll start by understanding what's in the current branch.Working tree is clean, so scope is the committed branch diff. Starting with discovery.Serverless tags are reported from `ListTagsForResource`. Now testing that `cluster_type` is required.Now the `MAX_RESULT_ROWS` cap (default 1000).Read to its end: 1000 rows, last `userid` 1000. Now over the cap.Now the guard's new session-control function rules, in read-only mode.All six refused. Now confirming the same statements are classified as writes in read-write mode, rather than run as reads.Now the batch-denied configurations.Note the fallback read's `query_id` carries no `:N` sub-statement suffix — a bare `ExecuteStatement`, not a batch. Now transactions under denial.Guard rules that apply at every access mode.Now named transactions. Opening three at once: two names on the provisioned cluster (one containing the `:` separator) and the same name on the workgroup.Now a failing statement inside a transaction.Now writes at the unconfirmed read-write configuration.The temp table creation reported success. Checking whether the next call finds it.Now the same inside a named transaction, which is the documented remedy.Now `review_cluster` on both warehouse types, one of them through the batch-denied fallback. These take minutes.One last cap check, on the fallback path.Scratch schema gone, no transactions left open, both warehouses back to their seeded state.

Scope note: `git status` reports a clean working tree, so there were no uncommitted changes to cover. The branch's three newest commits carry the behaviour under test — `aa1073db` (cluster_type required on every cluster tool, typed-tuple keys), `86445391` (result row cap, pagination, guard additions, serverless tags, review_cluster resolution), `fe88f3be` (session state outside a transaction) — on top of the earlier branch work, including the batch-denial fallback.

What the evidence looked like in a few places worth calling out: the fallback's reads come back with a bare `query_id` (`b08b1ebf-…`) rather than a batch sub-statement suffix (`…:3`), so the compatibility path is demonstrably `ExecuteStatement`; the "no open transaction" and write-refusal messages render the target as `mcp-e2e-provisioned (provisioned):dev`, the new typed form, and the denied-batch log shows the latch key changing from `provisioned:mcp-e2e-provisioned` in older runs to `mcp-e2e-provisioned (provisioned)` now; and the serverless latch was taken independently of the provisioned one.

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && git status && echo "=== BRANCH ===" && git branch --show-current && echo "=== LOG ===" && git log --oneline -15

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && echo "=== merge-base with main ===" && git merge-base HEAD main && echo "=== commits unique to branch ===" && git log --oneline main..H...

[tool] status: Completed

[tool] Reading scenarios.py:1

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && git show --stat fe88f3be && echo "=====" && git show --stat 86445391 && echo "=====" && git show --stat aa1073db

[tool] status: Completed

[tool] status: Completed

[tool] Reading clusters.py:1, consts.py:1

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && grep -n "max_result_rows\|MAX_RESULT_ROWS\|MAX_RESULT_PAGES\|too many rows\|row_count\|TotalNumRows" awslabs/redshift_mcp_server/redshi...

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && grep -n "cluster_type\|@mcp.tool\|async def .*_tool\|Field(" awslabs/redshift_mcp_server/server.py | head -80

[tool] status: Completed

[tool] status: Completed

[tool] Reading redshift.py:321-450, server.py:226-345

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && grep -n "no_batch\|batch_denied\|_latch\|BatchExecuteStatement\|fallback" awslabs/redshift_mcp_server/redshift.py | head -70

[tool] status: Completed

[tool] Reading redshift.py:81-210, redshift.py:1266-1465

[tool] status: Completed

[tool] Reading redshift.py:571-900

[tool] status: Completed

[tool] Reading catalog.py:1

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && grep -n "pg_cancel_backend\|pg_terminate_backend\|change_query_priority\|change_session_priority\|change_user_priority\|set_config\|_SE...

[tool] status: Completed

[tool] Reading sql_guard.py:31-180, sql_guard.py:301-420

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && grep -n "raise ToolError\|class ClusterKey\|class Target\|class TransactionKey\|NamedTuple\|def __str__" awslabs/redshift_mcp_server/tr...

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && grep -n "signals_evaluated\|cluster_type\|max_result_rows\|resolve_cluster" awslabs/redshift_mcp_server/review/executor.py

[tool] status: Completed

[tool] status: Completed

[tool] Reading transactions.py:171-290, models.py:26-70

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && grep -n "MAX_RESULT_ROWS\|SERVERS\|env\|ACCESS_MODE\|UNSAFE" e2e_tests/agent.py | head -40 && echo "=== generated agent config ===" && ...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

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

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/e2e_tests/.logs && echo "=== rw: write refusals ===" && grep -h "Refused a write on" awslabs.redshift-mcp-server-read-write.log | tail -3 ...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed
