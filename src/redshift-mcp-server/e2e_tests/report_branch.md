# End-to-end test: Changes on this branch

2026-09-14 21:25 UTC

- **Scenario**: `branch`
- **Code under test**: `feat/redshift-session-redesign` at `44a721b5`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 14.0 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| Read-only: reads and all five discovery tools, both warehouses | PASS | |
| Read-only: deny-list wording preserved (`COMMIT`, `SET`, `RESET`, `TRUNCATE`) | PASS | Reports "Statement type not allowed in read-only mode: X", unchanged for callers |
| Read-only: engine backstop blocks non-deny-listed writes (`INSERT`, `CREATE TABLE`) | PASS | "ERROR: transaction is read-only" from the `BEGIN READ ONLY` wrapper |
| Single-statement rule enforced | PASS | |
| Read-write with confirmation: write fails closed | PASS | Names both remedies: an elicitation-capable client, or `UNSAFE_SKIP_WRITE_CONFIRMATION=true` |
| Read-write with confirmation: recognized read runs unprompted | PASS | |
| Read-write unconfirmed: writes execute (DDL, DML, `DROP`) | PASS | |
| Transaction control refused as a statement in read-write (`BEGIN`, `COMMIT`, `ROLLBACK`) | PASS | Refusal names the four transaction parameters to use instead |
| Caller `COMMIT` inside a named transaction refused, transaction left intact | PASS | The `44a721b5` regression; verified by consequence, not just message |
| `TRUNCATE` refused inside a named transaction, allowed standalone | PASS | Distinct wording: "commits the transaction it runs in" |
| Named transaction: commit persists across calls | PASS | Rows from both `begin_transaction` and `commit_transaction` persisted |
| Named transaction: rollback discards | PASS | |
| Named transaction: isolation inside vs outside | PASS | 2 rows inside, 0 outside |
| Failed statement aborts its transaction and drops the name | PASS | Uncommitted write gone; name reported unknown afterwards |
| Duplicate transaction name refused | PASS | |
| More than one transaction parameter refused | PASS | |
| `sql` required except when closing a transaction | PASS | |
| Read-only named transaction: several reads, write still refused by the engine | PASS | |
| Transaction name bound to its cluster and database | PASS | Same name on the other warehouse reports no open transaction |
| Name that closed while a statement waited on its lock is refused | PASS | Generation guard from `0e91a137`; fired on a real parallel call |
| Denied batch: reads and all five discovery tools via the fallback, both warehouses | PASS | Against user tables, not only the catalogue |
| Denied batch: write refused at both `nb_` and `nbw_` | PASS | The `b1ed1958` wording; cites scope, not a read-only transaction |
| Denied batch: named transactions refused | PASS | Transaction-specific reason, distinct from the write refusal |
| Denied batch: SQL guard still precedes the fallback | PASS | `nb_` gives the read-only wording, `nbw_` the transaction-control wording |
| Denied batch: latch holds, then re-probes after its window | PASS | Two latches 309s apart with 14 fallback statements between them |
| Denied batch: `review_cluster` survives the fallback | PASS | 8 signals on serverless; provisioned-only diagnostics skipped |
| AWS submission error text reaches the caller | PASS | The `8e56cd96` fix; full `ValidationException` text naming the operation |
| Non-denied configurations unchanged, batch path still in use | PASS | Sub-statement query ids (`...:2`) confirm the batch; fallback ids are bare |
| `review_cluster` on the batch path | PASS | 11 signals, 10 findings on the provisioned cluster |

- The `rw_*` confirmation round trip remains unreachable from this client, which does not advertise MCP elicitation, so only the fail-closed branch was exercised. This is the documented limitation in `e2e_tests/README.md`, not a new finding; `rwu_*` covers what happens once a write is allowed through.
- One ordering nuance, not a defect: `in_transaction` against a never-opened name on a *not yet latched* denied-batch process answers "No open transaction named ..." rather than the batch-denial reason, because the latch is set by the first refused call. Once latched it gives the intended batch reason, which I re-confirmed. Both messages are truthful.
- The per-target open-transaction cap and idle reaping were not driven end to end: both are in-process bookkeeping with no AWS interaction, and exercising the cap would mean opening and closing 21 sessions. They are covered by `TestRedshiftTransactionManager` in the unit suite.
- Two harness clusters only; the other four clusters and the unrelated workgroup in the account were left alone. Scratch tables were created in `public` (the identity has no CREATE on `tickit`) and dropped; the sample schema is unchanged.

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

I'll start by understanding what changed in this branch.Working tree is clean, so the scope is the committed branch diff. Let me find the branch point.Now let me look at the unit tests for scenario ideas, especially the newest commits.Unit suite is green (424 tests). Now the live checks — starting with baseline connectivity and confirming the denied configuration is actually in effect.Denial confirmed in effect (explicit deny in session policy) and the read fell back. Now the read-only guard at the default configuration.The INSERT hit a column-range error before reaching the guarantee. Retrying with values that fit, plus a DDL probe.Read-only holds. Now the read-write configurations — the confirmation gate first.Writes at the unconfirmed configuration, then the transaction-control denial that is this branch's newest fix.CREATE in `tickit` is not granted to this identity. Let me find a schema it can write to.Writes work (identity `IAMR:Admin`, scratch table in `public`). Now the named-transaction lifecycle, including the desync the newest commit fixes.Now the desync attempt: a caller's own `COMMIT` passed inside the open transaction.Both refused by the guard before reaching the session. Confirming the transaction survived intact and that a rollback genuinely undoes.Isolation is intact — 2 inside, 0 outside, so the refused `COMMIT` really did not commit. Now the rollback must actually discard.Now the commit path, and the parameter-validation edges.Commit path persists both rows. Now `TRUNCATE` standalone (must be allowed) and a failed statement inside a transaction.Failed statement aborts, drops the name, and its write is gone. Now read-only transactions.The generation guard fired: the parallel `CREATE TABLE` aborted the transaction, and the queued read was refused rather than waking into a dead transaction. Re-running the snapshot serially.Now the branch's headline: the denied-batch configurations. Discovery and reads first.All discovery works through the fallback. Now the fallback's refusals at both denied configurations.The fourth returned the unknown-name reason rather than the batch reason — likely because those four calls raced and the `nbw_` server had not yet latched. Re-testing now that it certainly has.Confirmed — once latched, the batch reason wins as intended; the earlier answer was my own race on an unlatched process, and was truthful regardless.review_cluster is healthy on the batch path (11 signals, 10 findings). Now a genuine AWS submission error, to check its text reaches the caller.AWS text reaches the caller in full, naming the operation — the fix in `8e56cd96` holds. Now review_cluster through the fallback, and writes on the serverless warehouse.review_cluster survives the fallback on serverless (8 signals; provisioned-only diagnostics correctly skipped). Now a transaction on serverless, and whether a transaction name is bound to its warehouse.Now checking the server logs for anything unexpected, including the fallback re-probe.The logs surface a live re-probe. Confirming.Two latches 309s apart with 14 fallback statements in between — the latch held and the re-probe fired on schedule. Now cleaning up the scratch tables.Live testing is complete and both warehouses are back to their seeded state (202 venues, 172,456 sales; scratch tables dropped).

Scope confirmed first: working tree is clean, so the scope is the committed diff of `feat/redshift-session-redesign` (HEAD `44a721b5`) against its merge base with `origin/main` (`c9102a9a`) — 6 source files, ~2,060 insertions. The substantive changes are the named-transaction redesign replacing the old per-target session pool, the batch path with `ExecutionMode=AUTO_COMMIT`, the `no_batch` fallback for credentials denied `redshift-data:BatchExecuteStatement`, `ACCESS_MODE`/`UNSAFE_SKIP_WRITE_CONFIRMATION`, the three-tier SQL guard, and routing every tool's failure through `_tool_failed`. The unit suite passes on this tree (424 tests).

Two results are worth calling out beyond the table.

The regression that commit `44a721b5` fixes is genuinely closed, and I checked the consequence rather than just the message. With a transaction open and two uncommitted rows in it, `in_transaction='t1'` with `sql='COMMIT'` was refused by the guard; the transaction then still showed 2 rows inside against 0 outside, and `rollback_transaction` left 0 rows behind. Before the fix that `COMMIT` would have persisted the rows and the rollback would have reported success having undone nothing.

The fallback's re-probe was observable live. The `nb_` server latched at 21:13:37, served 14 statements on the compatibility path, then latched a second time at 21:18:46 — 309 seconds later, one `FALLBACK_NO_BATCH_REPROBE` window. So the latch holds without paying a denied call per statement, and a re-grant would be picked up without a restart.

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && git status && echo "=== BRANCH ===" && git branch --show-current && echo "=== LOG ===" && git log --oneline -15

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && git log --oneline -3 origin/main 2>/dev/null || git branch -r | head -20

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && for b in origin/main main origin/master; do if git rev-parse --verify -q $b >/dev/null; then echo "=== base $b: $(git merge-base HEAD $...

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && git diff --stat c9102a9a HEAD -- awslabs README.md

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && git diff c9102a9a HEAD -- awslabs/redshift_mcp_server/redshift.py > /tmp/diff_redshift.txt; wc -l /tmp/diff_redshift.txt

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && git diff c9102a9a HEAD -- awslabs/redshift_mcp_server/sql_guard.py awslabs/redshift_mcp_server/consts.py

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && git diff c9102a9a HEAD -- awslabs/redshift_mcp_server/server.py | head -700

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && git diff c9102a9a HEAD -- awslabs/redshift_mcp_server/server.py | sed -n '700,1100p'

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && sed -n '1,600p' /tmp/diff_redshift.txt

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && sed -n '600,1150p' /tmp/diff_redshift.txt

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && sed -n '1150,1703p' /tmp/diff_redshift.txt

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && echo "=== 44a721b5 ===" && git show --stat 44a721b5 && echo "=== 0e91a137 ===" && git show --stat 0e91a137 && echo "=== 8e56cd96 ===" &...

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && grep -n "class Test\|    def test_\|def test_" tests/test_sql_guard.py | head -120

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && grep -n "^class Test" tests/test_redshift.py

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && grep -n "^class Test" tests/test_server.py

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && sed -n '2451,2530p;2625,2810p' tests/test_redshift.py

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && sed -n '88,140p;200,340p' tests/test_sql_guard.py

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && git diff c9102a9a HEAD -- awslabs/redshift_mcp_server/review/executor.py

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server && timeout 900 uv run pytest -q 2>&1 | tail -8

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/e2e_tests/.logs && grep -c "BatchExecuteStatement is denied" awslabs.redshift-mcp-server-no-batch.log; echo "--- last denial lines ---"; g...

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

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

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

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

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

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/e2e_tests/.logs && for f in *.log; do echo "=== $f ==="; awk '$0 ~ /2026-09-14 21:1[3-9]|2026-09-14 2[2-3]:/' "$f" | grep -E "WARNING|ERRO...

[tool] status: Completed

[tool] Running: cd /local/home/sergkono/AWSLabsMCP/src/redshift-mcp-server/e2e_tests/.logs && echo "=== nb latches today after 21:00 ===" && grep "_latch_no_batch" awslabs.redshift-mcp-server-no-batch.log | awk '$...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed
