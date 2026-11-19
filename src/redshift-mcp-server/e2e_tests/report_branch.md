# End-to-end test: Changes on this branch

2026-11-13 23:20 UTC

- **Scenario**: `branch`
- **Code under test**: `fix/redshift-read-only-transaction-rollback` at `8998a9d0`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 12.6 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
| --- | --- | --- |
| Read-only `commit_transaction` closes the transaction with `ROLLBACK` (provisioned) | PASS | `sys_query_history` for the session shows `BEGIN READ ONLY`, the two reads, then `ROLLBACK`; no `COMMIT` |
| Read-only `rollback_transaction` closes with `ROLLBACK` (provisioned) | PASS | Unchanged closer, same session trace |
| Read-only statement plus `commit_transaction` in one call closes with `ROLLBACK` (serverless) | PASS | Session shows the caller's `SELECT` then `ROLLBACK`, in that order |
| Read-only `commit_transaction` reports success and drops the name | PASS | Closing again is refused with `No open transaction named 'ro_commit'` |
| Read-only `commit_transaction` that fails once sent says the transaction is discarded | PASS | With the session terminated: `failed before its ROLLBACK was confirmed, and is discarded either way`; server log names `ROLLBACK unconfirmed` |
| Read-write `commit_transaction` still issues `COMMIT` (confirming configuration) | PASS | Session shows `BEGIN` then `COMMIT` |
| Read-write commit persists rows and rollback discards them | PASS | Of two inserts into a scratch table, only the committed row was readable afterwards |
| Read-write `commit_transaction` that fails once sent still reports the `COMMIT` as possibly applied | PASS | Same forced failure: `was never seen to finish its COMMIT, which may have applied` |
| Read-only standalone statement still wraps in `BEGIN READ ONLY … ROLLBACK` | PASS | The parity the change is modelled on; confirmed from the session trace |
| A write inside a read-only transaction is refused and the name released | PASS | Engine answers `ERROR: transaction is read-only`; tool reports the transaction released |
| `TRUNCATE` refused inside a transaction in read-write mode, transaction left open | PASS | Refusal names the implicit commit; a later read on the same name still worked |
| `TRUNCATE` refused in read-only mode, with no transaction name reserved | PASS | `Statement type not allowed in read-only mode: TRUNCATE`; the name was never opened |
| Read-only guard still refuses `pg_terminate_backend` | PASS | Refused at the read-only configuration, allowed at read-write |
| Denied `BatchExecuteStatement`, read-only: named transaction refused, reads still work | PASS | Refusal names the grant and its 300s latency; the read ran bare on the compatibility path, with no `BEGIN READ ONLY` wrapper |
| Denied `BatchExecuteStatement`, read-only: a closer on an unknown name reports it missing | PASS | Reports `No open transaction`, not the batch denial |
| Denied `BatchExecuteStatement`, read-write: named transaction refused, standalone write refused | PASS | Write refusal says the server serves reads only whatever the access mode |
| Denied `BatchExecuteStatement` refusal holds on serverless as well as provisioned | PASS | Latch is per cluster; both targets refuse named transactions |
| `execute_query` description carries the new Transactions text at every configuration | PASS | All five configurations expose the same wording: ends in `ROLLBACK`, `commit_transaction` included, and the read-only/read-write split on a failed commit |

- The branch's denied-credential link is unit-only: with the batch action denied, `begin_transaction` is refused before any transaction exists, so the stale-latch path in `_execute_statement_in_transaction` (the test the commit switched to `enforce_read_only=False`) has no end-to-end route. The closer substitution itself was verified at the granted configurations instead.
- The README edit in this commit is documentation the server does not serve, so it was checked by reading, not through a tool.
- Forcing a closer to fail needed `pg_terminate_backend` on the transaction's own backend from the read-write configuration, plus a ~100s wait for the Data API to reject the next submit with `Session is not available`. Without the wait the submit is accepted and the statement fails instead, which both modes report identically.
- Scratch table `public.e2e_txn_probe` was created on `mcp-e2e-provisioned` for the persistence check and dropped at the end; no other data was written on either warehouse, and no other cluster in the account was touched.

## Prompt

Written by the harness, not by hand, and never says what to expect.

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

I'll start by understanding the branch changes, then design and run the scenarios.

Now let me read the code the change touches, to pin down what is externally observable.

Starting with the core branch behaviour: a read-only transaction closed by `commit_transaction`.

Read-only `commit_transaction` issued `ROLLBACK`. Now the rollback closer and the serverless/statement-plus-closer variant.

Read-only closes with ROLLBACK on both warehouses. Now the name after closing, and read-write mode unchanged.

Now the functional read-write check: whether a committed transaction still persists and a rolled-back one still discards.

Now the read-only guard inside a transaction, and the standalone read-only wrapper the change is modelled on.

Now the configurations denied `redshift-data:BatchExecuteStatement`.

Now the read-only failure path: what a `commit_transaction` reports when it fails once sent.

Let me try once more to reach the read-only closer-failure wording, by letting the killed session be noticed before closing.

That is the branch's new wording. Now the read-write contrast on the same failure path.

All scenarios ran. The working tree was clean, so the scope was the single branch commit `8998a9d0` (read-only transactions ending in `ROLLBACK`), and I verified each claim it makes against `sys_query_history` on the cluster rather than from tool return values alone.

Key evidence: a read-only transaction closed by `commit_transaction` left `SET application_name → BEGIN READ ONLY → <reads> → ROLLBACK` on its session with no `COMMIT`, on both warehouses; a read-write transaction on the same cluster still left `BEGIN → COMMIT`, and its committed row persisted while a rolled-back one did not. The failure wording split out too: with the session killed, read-only reported `failed before its ROLLBACK was confirmed, and is discarded either way`, read-write `was never seen to finish its COMMIT, which may have applied`.

The scratch table `public.e2e_txn_probe` used for the persistence check was created and dropped on `mcp-e2e-provisioned`; nothing else was modified.

[tool] Running: pwd && git status && echo "=== BRANCH ===" && git log --oneline -15 && echo "=== MERGE BASE ===" && git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main 2>/dev/null

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Running: git status --porcelain=v1 -uall . | head -30; echo "=== DIFF STAT vs merge-base ==="; git diff --stat c9102a9a631fe0d8f4b1671b154ab2bb73484a5c HEAD; echo "=== uncommitted ==="; git diff HE...

[tool] status: Completed

[tool] Running: git show --stat 8998a9d0 && echo "=== FULL DIFF ===" && git show 8998a9d0

[tool] status: Completed

[tool] Running: sed -n 640,1010p awslabs/redshift_mcp_server/redshift.py

[tool] status: Completed

[tool] Running: grep -n "_forget_closed_transaction\|def _transaction_outcome\|stands\|may have applied\|discarded\|_FALLBACK_NO_BATCH_REFUSES_TRANSACTION" awslabs/redshift_mcp_server/redshift.py | head -...

[tool] status: Completed

[tool] Running: sed -n 60,140p awslabs/redshift_mcp_server/redshift.py; echo "=== LATCH ==="; sed -n '/def _latch_no_batch/,/^async def \|^def _is_no_batch/p' awslabs/redshift_mcp_server/redshift.py | hea...

[tool] status: Completed

[tool] Running: sed -n '/class TestTransactionsNeedTheBatch/,/^class /p' tests/test_redshift.py

[tool] status: Completed

[tool] Running: grep -n "logger\.\(debug\|info\)" awslabs/redshift_mcp_server/redshift.py | head -40

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

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

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: grep -n "SESSION_KEEPALIVE\|session_keepalive" awslabs/redshift_mcp_server/settings.py awslabs/redshift_mcp_server/consts.py | head; echo "=== e2e config ==="; cat e2e_tests/config.toml | ...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: sleep 100; echo waited

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: sleep 100; echo waited

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: grep -n "ro_fail2\|rw_fail\|ro_commit\|ro_rollback" e2e_tests/.logs/awslabs.redshift-mcp-server.log e2e_tests/.logs/awslabs.redshift-mcp-server-read-write-unsafe.log | grep -i "rollback\|c...

[tool] status: Completed
