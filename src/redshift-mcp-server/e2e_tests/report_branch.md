# End-to-end test: Changes on this branch

2026-09-15 00:48 UTC

- **Scenario**: `branch`
- **Code under test**: `feat/redshift-session-redesign` at `1687d7d4`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 23.6 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| Closing a transaction drains its session (`1687d7d4`) | PASS | Measured on the provisioned cluster: a transaction closed 5s earlier had released its connection while one open and idle 158s still held its. Release observed 42-101s after close, not ~1s: the Data API reaps on its own schedule, well inside the 600s keepalive it used to ask for |
| A transaction still open keeps its session for the configured keepalive | PASS | The counterfactual for the row above; connection alive after 158s idle |
| Read-only: reads and all five discovery tools, both warehouses | PASS | |
| Read-only: deny-list wording preserved (`SET`, `COMMIT`, `TRUNCATE`) | PASS | "Statement type not allowed in read-only mode: X", unchanged for callers |
| Read-only: engine backstop blocks non-deny-listed writes | PASS | "ERROR: transaction is read-only" from the `BEGIN READ ONLY` wrapper, on both warehouses |
| Single-statement rule enforced | PASS | |
| Read-write with confirmation: write fails closed | PASS | Names both remedies: an elicitation-capable client, or `UNSAFE_SKIP_WRITE_CONFIRMATION=true` |
| Read-write with confirmation: recognized read runs unprompted | PASS | |
| Read-write unconfirmed: writes execute (DDL, DML, `DROP`) | PASS | |
| Transaction control refused as a statement (`BEGIN`, `COMMIT`) | PASS | Refusal names the four transaction parameters to use instead |
| Caller `COMMIT` inside a named transaction refused, transaction left intact | PASS | Verified by consequence: 1 row inside vs 0 outside after the refusal, and the rollback then discarded |
| `TRUNCATE` refused inside a named transaction, allowed standalone | PASS | Distinct wording: "commits the transaction it runs in" |
| Named transaction: commit persists across calls | PASS | Rows from both `begin_transaction` and `commit_transaction` persisted |
| Named transaction: rollback discards | PASS | On both warehouses; the serverless case discarded a `CREATE TABLE` |
| Named transaction: isolation inside vs outside | PASS | |
| Failed statement aborts its transaction and drops the name | PASS | Uncommitted write gone; name reported unknown afterwards |
| Duplicate transaction name refused | PASS | |
| More than one transaction parameter refused | PASS | |
| `sql` required except when closing; blank name refused | PASS | Distinct messages for the bare call, for `in_transaction`, and for a whitespace name |
| Read-only named transaction: several reads, write still refused by the engine | PASS | |
| Transaction name bound to its cluster and database | PASS | Same name against the other warehouse reports no open transaction |
| Denied batch: reads and all five discovery tools via the fallback, both warehouses | PASS | Against user tables, not only the catalogue |
| Denied batch: write refused at both `nb_` and `nbw_` | PASS | Cites the missing action and its scope, not a read-only transaction |
| Denied batch: named transactions refused | PASS | Transaction-specific reason, distinct from the write refusal |
| Denied batch: SQL guard still precedes the fallback | PASS | `nb_` gives the read-only wording for `TRUNCATE`/`COMMIT`, `nbw_` the transaction-control wording |
| Denied batch: latch holds, then re-probes after its window | PASS | Latched 00:36:16, 9 fallback statements, re-probed 00:41:18 (302s) |
| Denied batch: `review_cluster` survives the fallback | PASS | 11 signals, 11 findings, same as the batch path |
| AWS submission error text reaches the caller | PASS | Full `ValidationException` text, naming `BatchExecuteStatement` at `ro_` and `ExecuteStatement` at `nb_`, so a submit error is not mistaken for a batch denial |
| Non-denied configurations unchanged, batch path still in use | PASS | Sub-statement query ids (`...:2`, `...:3`) throughout; fallback ids are bare |
| `review_cluster` on the batch path | PASS | 11 signals, 11 findings on the provisioned cluster |

- The `rw_*` confirmation round trip remains unreachable from this client, which does not advertise MCP elicitation, so only the fail-closed branch was exercised. This is the documented limitation in `e2e_tests/README.md`; `rwu_*` covers what happens once a write is allowed through.
- The generation guard (`0e91a137`) was not driven end to end this run: this client serializes tool calls, so the two statements that must contend for one transaction's lock could not be issued concurrently, and every attempt collapsed into the serial abort path, which passed. It fired on a real parallel call in the previous run and is covered by the unit suite.
- The per-target open-transaction cap and idle reaping were not driven end to end either: both are in-process bookkeeping with no AWS interaction, and exercising the cap would mean opening 11 sessions. `TestRedshiftTransactionManager` covers them.
- `stv_sessions` is readable on the provisioned cluster but not on the serverless workgroup for this identity, so the drain was measured on the provisioned cluster only. The serverless transaction lifecycle was verified by its effect on data instead.
- Two harness warehouses only; the other four clusters and the unrelated workgroup in the account were left alone. Scratch tables were created in `public` (the identity has no `CREATE` on `tickit`) and dropped.

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

I'll start by understanding what the branch changes are.Unit suite first, then live checks.Now the read-only guard tiers while that sits open.Now the parameter-validation edges and the standalone TRUNCATE.Now the denied-batch configurations: discovery, then their refusals.Now the denied configurations' refusals.Now serverless coverage of the same behaviours, and review_cluster on both paths.Now a genuine race: two calls on the same transaction at once, the first of which aborts it.Live testing is complete; both warehouses are back to their seeded state (202 venues, 172,456 sales on the provisioned cluster, no scratch objects on either).

Scope: the working tree is clean, so the scope is the committed diff of `feat/redshift-session-redesign` (HEAD `1687d7d4`) against its merge base with `main` (`c9102a9a`) — 6 source files, ~2,070 insertions. The one commit newer than the last committed report is `1687d7d4`, which sends `SessionKeepAliveSeconds=1` on the batch carrying a transaction's `COMMIT` or `ROLLBACK` instead of re-sending `SESSION_KEEPALIVE`. The unit suite is green on this tree (426 tests).

Two things are worth stating beyond the table.

The drain is real, and the cleanest evidence is a single instant. At 00:32:25 the transaction `hold`, open and idle since 00:29:47 (158s), still held its Redshift connection, while `t1`, closed five seconds earlier at 00:32:20, had already released its. Repeating the measurement on a second transaction (`d2`, closed 00:44:28) put the release between 42s and 101s after the close, so the interval is not the one second the parameter asks for: the Data API reaps on its own schedule, and one second is a floor on when it may, not a promise of when it does. What the fix changes is the order of magnitude — a closed transaction's connection goes in tens of seconds rather than sitting out the full 600s `SESSION_KEEPALIVE`, which is what the old code asked for.

The fallback's latch and re-probe were observable again. The `nb_` process latched at 00:36:16, served 9 statements on the compatibility path, and re-probed at 00:41:18 — 302 seconds later, one `FALLBACK_NO_BATCH_REPROBE` window — so the denial costs one warning per window rather than one per statement.

[tool] Running: git status && echo "=== BRANCH ===" && git branch --show-current && echo "=== LOG ===" && git log --oneline -20

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Running: git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main 2>/dev/null || echo NOBASE; echo "=== branches ==="; git branch -a | head -30

[tool] status: Completed

[tool] Running: git diff --stat c9102a9a631fe0d8f4b1671b154ab2bb73484a5c..HEAD -- . | tail -20

[tool] status: Completed

[tool] Running: git show --stat 1687d7d4; echo "=== DIFF ==="; git show 1687d7d4 -- awslabs/ src/redshift-mcp-server/awslabs/

[tool] status: Completed

[tool] Running: git diff --stat c9102a9a..HEAD -- awslabs/ README.md; echo "=== commits touching awslabs ==="; git log --oneline c9102a9a..HEAD -- awslabs/

[tool] status: Completed

[tool] Running: sed -n 1,120p e2e_tests/report_branch.md

[tool] status: Completed

[tool] Reading consts.py:1, sql_guard.py:1

[tool] status: Completed

[tool] Running: grep -n "^def \|^async def \|^class \|^    def \|^    async def \|^_[A-Z_]* = \|^[A-Z_]* = " awslabs/redshift_mcp_server/redshift.py

[tool] status: Completed

[tool] Reading redshift.py:57-226, redshift.py:461-1080

[tool] status: Completed

[tool] Reading redshift.py:1074-1173, redshift.py:1461-1660, redshift.py:285-474

[tool] status: Completed

[tool] Running: grep -n "def \|ACCESS_MODE\|UNSAFE_SKIP\|elicit\|_tool_failed" awslabs/redshift_mcp_server/server.py | head -80

[tool] status: Completed

[tool] Reading server.py:239-378, server.py:701-760

[tool] status: Completed

[tool] Running: git show 1687d7d4 -- src/redshift-mcp-server/tests/ | sed -n 1,80p

[tool] status: Completed

[tool] Running: git show 1687d7d4 --stat --name-only; echo "---"; git show 1687d7d4 -- tests/test_redshift.py | head -60

[tool] status: Completed

[tool] Running: ls .kiro/agents/ 2>/dev/null; cat .kiro/agents/*.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({k:{'command':v.get('command'),'args':v.get('args'),'env':{...

[tool] status: Completed

[tool] Running: grep -n "^class \|^    class " tests/test_redshift.py tests/test_server.py tests/test_sql_guard.py

[tool] status: Completed

[tool] Running: timeout 900 uv run --frozen pytest -q 2>&1 | tail -8

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: sleep 10; echo waited

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: sleep 25; echo waited

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

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

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

[tool] Running: for f in .logs/*.log; do echo "=== $f"; grep -c . "$f"; grep -E "WARNING|ERROR" "$f" | tail -5; done

[tool] status: Completed

[tool] Running: grep -n "_latch_no_batch" .logs/awslabs.redshift-mcp-server-no-batch.log | awk -F'|' '{print $1}' ; echo "--- fallback statements today:"; grep -c "on the compatibility path" .logs/awslabs.redshift...

[tool] status: Completed

[tool] Running: awk '$0 >= "2026-09-15 00:36:16" && $0 <= "2026-09-15 00:41:19"' .logs/awslabs.redshift-mcp-server-no-batch.log | grep -c "on the compatibility path"

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: sleep 20; echo waited

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: sleep 45; echo waited

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: grep -E "Opened transaction|Closed transaction|Reaped transaction" .logs/awslabs.redshift-mcp-server.log | awk '$0 >= "2026-09-15 00:24"'

[tool] status: Completed

[tool] Running: grep -n "1073750330" .logs/*.log | awk -F'|' '{print $1, substr($0, index($0,"SQL:"), 90)}' | head

[tool] status: Completed

[tool] Running: grep -E "Opened transaction|Closed transaction" .logs/awslabs.redshift-mcp-server-read-write-unsafe.log | awk '$0 >= "2026-09-15 00:30"' | head -20

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed
