# End-to-end test: Changes on this branch

2026-09-15 03:51 UTC

- **Scenario**: `branch`
- **Code under test**: `feat/redshift-session-redesign` at `da4a5961`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 16.4 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| Aborted transaction drains the session it rolled back on (`da4a5961`) | PASS | The branch's newest fix, untested by the previous report. Measured twice on the provisioned cluster: a read-only abort rolled back 03:41:19 had released its session by 03:42:28 (≤69s), a read-write abort rolled back 03:49:30 by 03:50:07 (≤37s). Both far inside the 600s keepalive the session was minted with |
| Counterfactual: a transaction left open and idle keeps its session | PASS | Opened 03:42:42, still holding its connection at 03:47:49 (307s idle), which is what makes the two drain measurements above a real result rather than reaping luck |
| Closing a transaction drains its session (`1687d7d4`) | PASS | Closed 03:48:10, released by 03:49:08 (≤58s) |
| Read-only: reads and all five discovery tools, both warehouses | PASS | Identical row counts and catalogue output across warehouses |
| Read-only: deny-list wording preserved (`SET`, `TRUNCATE`, `GRANT`, `COMMIT`) | PASS | "Statement type not allowed in read-only mode: X", unchanged for callers |
| Read-only: engine backstop blocks non-deny-listed writes | PASS | "ERROR: transaction is read-only" from the `BEGIN READ ONLY` wrapper, on both warehouses |
| Single-statement rule enforced | PASS | |
| Read-write with confirmation: a write fails closed | PASS | Names both remedies: an elicitation-capable client, or `UNSAFE_SKIP_WRITE_CONFIRMATION=true` |
| Read-write with confirmation: a recognized read runs unprompted | PASS | Query id `:2` rather than `:3`, so the read-only wrapper is dropped in read-write mode as intended |
| Write classifier: `SELECT ... INTO` treated as a write | PASS | Refused for want of confirmation despite the `SELECT` root, and created no table |
| Write classifier: deny-listed words as identifiers and literals are not flagged | PASS | `SELECT 'commit' AS grant, 'truncate' AS vacuum` ran unprompted at `rw_` |
| Read-write unconfirmed: DDL, DML, `TRUNCATE` and `DROP` execute and persist | PASS | Persistence confirmed by reading back from a different configuration |
| Transaction control refused as a statement (`BEGIN`, `COMMIT`, `ROLLBACK`) | PASS | Refusal names the four transaction parameters to use instead; fires at read-write and at `nbw_` |
| Caller `COMMIT` refused inside a named transaction, transaction left intact | PASS | Refused by the guard before touching the session; the transaction then committed normally |
| `TRUNCATE` refused inside a named transaction, allowed standalone | PASS | Distinct wording: "commits the transaction it runs in and cannot be rolled back" |
| Named transaction: commit persists across calls, both warehouses | PASS | Statements from both `begin_transaction` and `commit_transaction` persisted, on provisioned and serverless |
| Named transaction: rollback discards | PASS | A `CREATE TABLE` staged on serverless was gone afterwards |
| Named transaction: isolation inside vs outside | PASS | 2 rows inside, 1 outside, and the observer saw the transaction's own extra session |
| Statement inside a transaction is sent bare on its session | PASS | Query id `:1`, so no second wrapper is nested inside the transaction |
| Failed statement aborts its transaction, discards its work, drops the name | PASS | An uncommitted `INSERT` vanished; the name then reported unknown |
| Duplicate transaction name refused | PASS | |
| More than one transaction parameter refused | PASS | Both offending parameters named |
| `sql` required except when closing; blank name refused | PASS | Distinct messages for the bare call, for `in_transaction`, and for a whitespace name |
| Transaction name bound to its cluster and database | PASS | The same name against the other warehouse reports no open transaction |
| Read-only named transaction: reads work, write refused by the engine | PASS | |
| Denied batch: reads and all five discovery tools via the fallback, both warehouses | PASS | Against user tables in `tickit`, not only the catalogue; results match the batch path |
| Denied batch: writes refused at both `nb_` and `nbw_` | PASS | One reason at every access mode, citing the missing action rather than a read-only transaction |
| Denied batch: named transactions refused | PASS | Transaction-specific reason, distinct from the write refusal, at `nb_` and `nbw_` |
| Denied batch: the SQL guard still precedes the fallback | PASS | `nb_` gives the read-only wording for `TRUNCATE`; `nbw_` gives the transaction-control wording for `ROLLBACK`, and refuses a standalone `TRUNCATE` as a write |
| Denied batch: the latch holds, then re-probes after its window | PASS | Latched 03:36:41, re-probed 03:42:09 (328s) and 03:47:17 (308s); 8 and 12 fallback statements ran between them with one warning per window, not one per statement |
| Denied batch: `review_cluster` survives the fallback | PASS | 11 signals, 12 findings, 11 queries — identical to the batch path run minutes apart |
| AWS submission errors reach the caller with AWS's own text | PASS | Full `ValidationException`, naming `BatchExecuteStatement` at `ro_` and `ExecuteStatement` at `nb_`, so a submit error is not mistaken for a batch denial |
| A non-denial AWS error does not latch the fallback | PASS | After the `ValidationException` above, the next `ro_` read still carried a `:3` sub-statement id |
| Non-denied configurations unchanged, batch path still in use | PASS | Sub-statement ids (`:1`, `:2`, `:3`) throughout at `ro_`/`rw_`/`rwu_`; fallback ids are bare |

- The `rw_*` confirmation round trip remains unreachable from this client, which does not advertise MCP elicitation, so only the fail-closed branch was exercised. This is the documented limitation in `e2e_tests/README.md`; `rwu_*` covers what happens once a write is allowed through.
- Sessions were counted from the denied-batch identity (`IAMR:mcp-e2e-denied-batch`) against `IAMR:Admin`, so the observing query is never itself counted. `stv_sessions` is readable on the provisioned cluster but not on the serverless workgroup for this identity, so all three drain measurements are provisioned-only; the serverless transaction lifecycle was verified by its effect on data instead.
- The generation guard was not driven end to end: this client serializes tool calls, so two statements cannot contend for one transaction's lock. `TestRedshiftTransactionManager` covers it.
- The per-target open-transaction cap and idle reaping were likewise not driven end to end — both are in-process bookkeeping with no AWS interaction, and exercising the cap would mean opening 11 sessions.
- The unit suite passes on the tree under test (427 tests), and the working tree is clean, so the committed branch diff is the whole scope.
- Scratch tables were created in `public` (this identity has no `CREATE` on `tickit`) and dropped; both warehouses end with no `e2e%` tables. The other four clusters and the unrelated workgroup in the account were left alone.

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

I'll start by understanding the branch changes.Working tree is clean, so scope is the committed branch diff. Let me find the base.Large branch. Let me read the source.Now the server layer.Now let me verify the environment and the denial are in place.Denial confirmed — the `nb_` identity is `IAMR:mcp-e2e-denied-batch` and its query id is bare, not a sub-statement id. Now the baseline reads.Batch path shows `:3` sub-statement ids; the fallback bare. Now the discovery tools at both configurations.All five discovery tools agree across paths. Now the read-only guard.Read-only holds. Now read-write.`rw_` fails closed and its read shows `:2` — the read-only wrapper is dropped in read-write mode. Now unconfirmed writes.Those two raced (parallel dispatch), so the empty read is inconclusive. Re-checking serially.Named transactions next. First, checking I can observe sessions for the drain measurements.`stv_sessions` is readable. Now the transaction lifecycle — commit first.Outside sees 1 row and 2 sessions — the transaction holds its own. Now read inside it.Inside sees 2, and `:1` confirms the statement is sent bare on its session. Now the in-transaction guards.Both refused by the guard. The transaction should be intact — committing with a last statement.3 rows persisted from both the opening and closing statements, and the session already released. Now the name should be gone.Now roll it back and confirm the DDL is discarded.Rollback discards. Now a read-only named transaction.Clean observer. Now a write inside the read-only transaction, which also drives the abort path.Name check, then I'll poll the session.Session `b3779a2e` was dropped at 03:41:19. Let me check what the rollback actually sent.The abort's rollback batch is visible. Now the denied-batch surface while that session ages.The aborted transaction's session went at 03:42:28 — released ~69s after its rollback, not held for the 600s keepalive it was minted with. Now the counterfactual: an open transaction should keep its session.Now `review_cluster` on both paths while that ages.11 signals, 12 findings through the fallback. Now the batch path for comparison.Identical on both paths. Now the AWS submission-error surface and the counterfactual session.That's the engine's text. For a genuine AWS submit-time error, let me push past a Data API parameter limit.AWS's text reaches the caller, naming the right operation on each path. Now checking `ro_` stayed on the batch path and the held session survives.Counterfactual holds — ~5 minutes idle and the session is still there. Now close it and measure the closing drain.tx_hold opened 03:42:42, still alive at 307s idle. The drained one went in 69s. Now closing it to measure the close drain.Closed at 03:48:10. While that drains, the latch and re-probe evidence.Latch held: 8 and 12 fallback statements between re-probes, one warning each window. Now the write classifier end-to-end at `rw_`.Closing drain released the session in 58s, and the refused SELECT INTO created nothing. One more: an abort must discard an uncommitted write.Abort discarded the staged row. Now the name check and cleanup.Cleaning up the scratch table, then I'll confirm this second abort also drained.Second abort drained in 37s. Let me verify the transaction commit path on serverless too, since I only rolled back there.Everything verified and cleaned up; the unit suite is green (427 passed).

The branch's newest commit, `da4a5961`, is the one the previous report predates, and it is the headline result: an aborted transaction's rollback now carries the drain keepalive. I measured it twice against a counterfactual — a transaction left open and idle still held its session at 307s, while the two aborted ones released within 69s and 37s of their rollback, far inside the 600s keepalive their sessions were minted with. The rest of the branch surface behaves as it did, including the denied-batch fallback, whose latch held for 8 and 12 statements between 300s re-probes.

[tool] Running: git status && echo "=== BRANCH ===" && git branch --show-current && echo "=== LOG ===" && git log --oneline -20

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Running: git log --oneline origin/main -1 2>/dev/null; echo "---"; git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main; echo "=== diffstat vs merge-base ==="; B=$(git merge-base HEAD ori...

[tool] status: Completed

[tool] Reading sql_guard.py:1, consts.py:1

[tool] status: Completed

[tool] Reading redshift.py:1-400

[tool] status: Completed

[tool] Reading redshift.py:401-820

[tool] status: Completed

[tool] Reading redshift.py:821-1250

[tool] status: Completed

[tool] Running: grep -n "^async def \|^def \|^class \|^# ---" awslabs/redshift_mcp_server/redshift.py | sed -n '1,200p'

[tool] status: Completed

[tool] Reading redshift.py:1464-1663

[tool] status: Completed

[tool] Running: grep -n "def \|ACCESS_MODE\|UNSAFE_SKIP\|elicit\|confirm" awslabs/redshift_mcp_server/server.py | sed -n '1,150p'

[tool] status: Completed

[tool] Reading server.py:239-348, server.py:706-765

[tool] status: Completed

[tool] Running: git show --stat da4a5961 | cat; echo "=== DIFF (src only) ==="; git show da4a5961 -- awslabs/ | cat

[tool] status: Completed

[tool] Running: B=c9102a9a631fe0d8f4b1671b154ab2bb73484a5c; for f in tests/test_sql_guard.py tests/test_redshift.py tests/test_server.py; do echo "########## $f"; grep -n "^class \|    def test_\|    async def tes...

[tool] status: Completed

[tool] Running: sed -n '1,80p' e2e_tests/report_branch.md

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_databases

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_schemas

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

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

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: grep -n "Closed transaction\|Opened transaction\|Rollback of the aborted" e2e_tests/.logs/awslabs.redshift-mcp-server.log | tail -20

[tool] status: Completed

[tool] Running: sed -n '14360,14385p' e2e_tests/.logs/awslabs.redshift-mcp-server.log

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: grep -n "tx_hold\|tx_commit\|tx_ro" e2e_tests/.logs/awslabs.redshift-mcp-server.log | tail

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: grep -n "Closed transaction mcp-e2e-provisioned:dev:tx_hold" e2e_tests/.logs/awslabs.redshift-mcp-server.log; date -u +%H:%M:%S

[tool] status: Completed

[tool] Running: grep -n "BatchExecuteStatement is denied" e2e_tests/.logs/awslabs.redshift-mcp-server-no-batch.log | tail -8; echo "=== count of fallback statements today ==="; grep -c "on the compatibility path" ...

[tool] status: Completed

[tool] Running: awk '/2026-09-15 03:36:41/,/2026-09-15 03:42:09/' e2e_tests/.logs/awslabs.redshift-mcp-server-no-batch.log | grep -c "on the compatibility path"; echo "--- and in the next window ---"; awk '/2026-0...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: grep -n "tx_abort" e2e_tests/.logs/awslabs.redshift-mcp-server-read-write-unsafe.log | tail -4; echo "now: $(date -u +%H:%M:%S)"

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: uv run pytest -q 2>&1 | tail -5

[tool] status: Completed

[tool] status: Completed
