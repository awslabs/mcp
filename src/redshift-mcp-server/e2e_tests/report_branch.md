# End-to-end test: Changes on this branch

2026-09-18 22:22 UTC

- **Scenario**: `branch`
- **Code under test**: `feat/redshift-session-redesign` at `ba6088c6`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 13.9 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| Nothing to run is refused as absent, not as a write or as too much | PASS | `-- nothing here\n;`, `/* nothing here */ ;`, `;;`, `;`, whitespace, bare comment; verified at `ro_`, `rwu_`, `nb_`, `nbw_` |
| Multiple statements keep their own refusal | PASS | |
| Unparseable input is rejected before submission | PASS | |
| Read-only deny list names all fifteen statement types | PASS | `CANCEL <pid>` answers "SQL could not be parsed", as the guard documents; bare `CANCEL` is deny-listed |
| The function form of SET is denied in read-only mode | PASS | `pg_catalog.set_config('transaction_read_only','off',false)` refused as `SET_CONFIG` |
| Transaction control is refused to a statement at read-write | PASS | `BEGIN`, `COMMIT`, `ABORT`; refusal names the four transaction parameters |
| Batch-denied fallback serves reads on both warehouse types | PASS | provisioned and serverless, user tables |
| Batch-denied fallback serves every catalog tool | PASS | databases, schemas, tables, columns |
| Batch-denied fallback refuses writes with a reason valid at every access mode | PASS | identical refusal at `nb_` (read-only) and `nbw_` (read-write) |
| Batch-denied fallback classifies writes structurally | PASS | `SELECT INTO`, `INTO` behind `UNION`, data-modifying CTE, `MERGE` refused; `EXPLAIN` and keyword-as-alias served |
| Named transactions are refused while the batch action is denied | PASS | both denied configurations, refusal names the grant |
| review_cluster works with the batch action denied | PASS | 37 signals, 8 queries on serverless; 2 findings vs 3 on the permitted run (see notes) |
| Read-write without client elicitation fails closed | PASS | refusal names `UNSAFE_SKIP_WRITE_CONFIRMATION` |
| A read at read-write runs unconfirmed | PASS | |
| Writes run with confirmation skipped | PASS | `CREATE SCHEMA`, `CREATE TABLE`, `INSERT`, `TRUNCATE`, `DROP SCHEMA` |
| A committed transaction persists its writes | PASS | |
| A rolled-back transaction discards its writes | PASS | |
| TRUNCATE and CALL are refused inside a named transaction, allowed standalone | PASS | the transaction survived both refusals and committed its own write |
| A failed statement aborts the transaction and drops its name | PASS | write rolled back; later commit reports the name unknown |
| A transaction is bound to the cluster and database it was opened on | PASS | same name on the other warehouse is unknown, and the original stayed open |
| A read-only transaction spans calls and cannot write | PASS | engine answered "transaction is read-only"; no object left behind |
| Resolved-cluster cache keeps warehouse types apart | PASS | interleaved provisioned/serverless statements in one process |
| A failed resolve is not cached | PASS | absent identifier still "not found" after successful resolves |
| list_clusters reports current state from uncached discovery | PASS | serverless `vpc_id` is a VPC id, status lowercase `available` |
| review_cluster reporting is consistent | PASS | one finding per signal, signals (55/37) exceed queries (11/8), recommendations deduplicated, mixed units |
| Provisioned-only diagnostics are skipped for serverless | PASS | 8 of 12 queries on serverless, 11 on provisioned including `ServerlessScaling` omitted there |

- `rw_` never completes a confirmation round trip: the agent CLI does not advertise MCP elicitation, so only the fail-closed branch was exercised. A confirm and a decline remain unobservable from this client.
- There is no configuration that both confirms writes and is denied the batch action, so the fix that stops a write being confirmed and then refused cannot be observed here; confirmation is checked before the fallback is consulted.
- The latch is keyed per cluster, but both warehouses are denied the action in this harness, so a denial on one cluster coexisting with a permitted other cannot be isolated.
- The denied review saw 2 findings against 3 on the permitted one. The missing signal reads system query history, whose visibility depends on the connected identity, so this is a data difference rather than a behaviour difference; signals evaluated, queries executed and structure matched exactly.
- 523 unit tests pass at this tree. Writes were confined to a scratch schema that was dropped; both warehouses verified free of leftovers.

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

I'll start by understanding what's in the current branch.Working tree is clean; branch is 4 redshift commits past the last e2e report. Let me read the newest changes.Now I have the branch surface. Let me verify baseline reads and the newest guard fix across all five configurations.Fix confirmed on both paths. Now the rest of the nothing-to-run forms and the neighbouring refusals.Now the denied-batch behaviour: what the fallback refuses and why.The fallback's refusals are right. Now what it must still serve, and how it classifies.Non-denied configurations next: the read-only deny list.Read-write mode fails closed without a prompt. Now that writes actually run at `rwu_`, I'll use a fresh scratch schema and drop it afterwards.Committed writes persisted. Now the rollback arm.Now whether a statement that could commit the transaction out from under the server is refused inside one.Now what a failed statement inside a transaction leaves behind.Now that a transaction is bound to the cluster and database it was opened on.Scratch schema dropped. Now a read-only transaction spanning calls at the default configuration.Now the cluster-resolve cache added by the newest perf commit.Provisioned-only diagnostics were skipped (8 of 12 queries ran). Now the provisioned side.Testing is complete. All 25 scenarios passed on both warehouses; 523 unit tests pass at this tree, and both warehouses were verified clean afterwards.

The newest fix behaved as intended: `-- nothing here\n;` and `/* nothing here */ ;` now answer `sql holds no statement to execute` on every configuration, including the two denied ones where the old code had the two paths disagreeing — the batch path submitted the fragment and the fallback called it a write. Multi-statement input still answers `Only a single SQL statement is allowed`, so the two conditions stay distinct.

On the denied configurations the fallback serves reads, every catalog tool, and a full `review_cluster` against both warehouse types, while refusing writes and named transactions with reasons that name `redshift-data:BatchExecuteStatement` and hold at every access mode. Write classification there is structural, not textual: `SELECT ... INTO` is refused even behind a `UNION`, a `DELETE` inside a CTE fronted by `SELECT` is refused, and `SELECT 1 AS commit, 'DELETE FROM tickit.sales' AS abort` is served as the read it is.

The non-denied configurations are unchanged. All fifteen read-only deny-list types are refused by name, `rw_` fails closed on a write and names the opt-out, `rwu_` writes and transactions commit and roll back correctly, a guard refusal inside a transaction leaves it open and committable, and a statement that fails in the engine aborts the transaction, rolls it back and drops its name. The resolve cache added by the perf commit returns the right warehouse type when provisioned and serverless calls interleave, and a miss is still not cached — an absent identifier answers `not found` both before and after successful resolves.

Writes were confined to a scratch schema `e2e_scratch` on the provisioned cluster, dropped at the end; `pg_namespace` and `pg_tables` confirm nothing was left on either warehouse.

[tool] Running: git status && echo "=== BRANCH ===" && git branch --show-current && echo "=== LOG ===" && git log --oneline -20

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Running: git merge-base HEAD main && echo "=== DIFFSTAT vs merge-base ===" && git diff --stat $(git merge-base HEAD main) HEAD && echo "=== LAST 3 COMMITS ===" && git log --oneline $(git merge-base HEAD mai...

[tool] status: Completed

[tool] Running: git show ba6088c6 --stat && echo "#### FULL ba6088c6 ####" && git show ba6088c6 -- src/redshift-mcp-server/awslabs

[tool] Running: git show ebf9be45 --stat && echo "#### FULL ebf9be45 (src only) ####" && git show ebf9be45 -- src/redshift-mcp-server/awslabs

[tool] status: Completed

[tool] status: Completed

[tool] Running: git show ba6088c6 -- awslabs tests && echo "################## ebf9be45 ##################" && git show ebf9be45 -- awslabs tests

[tool] status: Completed

[tool] Running: git show a37021fe --stat | head -40 && echo "==== MESSAGE ====" && git log -1 --format=%B a37021fe

[tool] status: Completed

[tool] Reading sql_guard.py:1

[tool] status: Completed

[tool] Running: grep -n "no_batch\|_no_batch_since\|ACCESS_DENIED\|BatchExecuteStatement\|fallback\|latch" awslabs/redshift_mcp_server/redshift.py | head -80

[tool] Running: for f in tests/test_redshift.py tests/test_transactions.py tests/test_server.py tests/test_settings.py tests/test_clients.py tests/test_catalog.py; do echo "===== $f ====="; grep -n "^class \|    d...

[tool] status: Completed

[tool] status: Completed

[tool] Reading redshift.py:71-190

[tool] Running: sed -n '2318,2560p' tests/test_redshift.py

[tool] status: Completed

[tool] status: Completed

[tool] Running: sed -n '55,290p' tests/test_server.py

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: grep -n "provisioned\|serverless\|name=\|^QUERIES\|QueryDefinition(" awslabs/redshift_mcp_server/review/definitions.py | head -60; echo "=== signal count ==="; grep -c "SignalDefinition(\|Signal(" ...

[tool] status: Completed

[tool] Running: grep -n "^    '[A-Za-z]*':\|'provisioned'\|'serverless'\|^REVIEW\|Signal:" awslabs/redshift_mcp_server/review/definitions.py | grep -v "^2[0-9][0-9]:\|docs.aws" | head -60

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: uv run pytest -q 2>&1 | tail -15

[tool] status: Completed

[tool] status: Completed
