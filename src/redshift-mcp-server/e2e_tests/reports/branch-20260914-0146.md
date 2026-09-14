# End-to-end test: Changes on this branch

2026-09-14 01:46 UTC

- **Scenario**: `branch`
- **Code under test**: `feat/redshift-session-redesign` at `b1ed1958`, uncommitted changes
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 16.3 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| `list_clusters` unaffected by the denied batch action | PASS | Identical output at `ro_*` and `nb_*`; the tool sends no SQL |
| Discovery SQL served by the fallback (databases, schemas, tables, columns) | PASS | Provisioned and Serverless, as the denied role `IAMR:mcp-e2e-denied-batch` |
| Read falls back on the same call that hit the denial | PASS | Same 172,456 rows as the baseline; bare statement id, so no batch |
| Fallback read on Serverless | PASS | Workgroup addressing exercised at both `nb_*` and `nbw_*` |
| `review_cluster` under the fallback | PASS | 11 signals provisioned, 8 on Serverless, matching `ro_*` on the same workgroup |
| Write refused at the denied read-only configuration | PASS | Refusal names `redshift-data:BatchExecuteStatement` |
| Write refusal wording at denied read-write | PASS | "serves reads only, whatever the access mode"; no mention of a read-only transaction |
| `SET` at denied read-write takes the write refusal | PASS | Deny list is off at read-write, so `might_write` routes it |
| Read-only deny list still fires first at denied read-only | PASS | `SET transaction_read_only TO off` → "not allowed in read-only mode: SET" |
| `begin_transaction` refused under the fallback | PASS | Names the action and why grouping is impossible |
| `in_transaction` refused with the transaction refusal, not "unknown name" | PASS | Caller is not misled into thinking the name was mistyped |
| Latch holds without a denied call per statement | PASS | One warning across 17 fallback statements |
| Batch path re-probed after its window, without a restart | PASS | Second warning 610s later; the read was still served |
| Latch under two concurrent first calls | PASS | Both raced and each warned, 9ms apart; one call yields one warning |
| Baseline read uses the batch and reports the caller's sub-statement | PASS | `query_id` `…:3` of `SET`, `BEGIN READ ONLY`, sql, `ROLLBACK` |
| Read-only deny list at the default configuration | PASS | `GRANT` rejected by name |
| Wrapper stops a write the deny list does not enumerate | PASS | `INSERT` → `ERROR: transaction is read-only` |
| Multi-statement submission rejected | PASS | At `ro_*` and at `rwu_*`, so read-write does not relax it |
| Named transaction spans calls on one connection | PASS | Same `pg_backend_pid`; later statements sent bare (`…:1`) |
| Guard applies inside a read-only transaction and leaves it open | PASS | `SET` rejected, next statement in the same transaction succeeded |
| Closing with a last statement, and the name gone afterwards | PASS | Reuse of the name reports no open transaction |
| Invalid transaction parameter combinations | PASS | `in_transaction` without sql, and two parameters at once, both named |
| A failed statement aborts the transaction and drops its name | PASS | Division by zero on Serverless; the name was free to reopen |
| Reopening an already-open name | PASS | Refused, pointing at `in_transaction` |
| Read at read-write mode needs no confirmation | PASS | `query_id` `…:2`, so no read-only wrapper is applied |
| Write at read-write fails closed when the client cannot be asked | PASS | Names `UNSAFE_SKIP_WRITE_CONFIRMATION`; nothing submitted |
| `SELECT … INTO` classified as a write | PASS | Read-shaped root, still demanded confirmation |
| Write executes and autocommits with confirmation skipped | PASS | Row read back through the read-only server |
| Transaction rollback discards, commit persists | PASS | Verified from a different configuration after each |
| Session state lives exactly as long as the transaction | PASS | `SET search_path` carried across calls, gone after rollback |
| Writes on Serverless as well as provisioned | PASS | CTAS created and dropped on both |
| `MAX_OPEN_TRANSACTIONS_PER_TARGET` enforced, and per target | PASS | 11th refused on Serverless while provisioned accepted one |
| Startup warnings per configuration | PASS | Read-write and unsafe-skip warned; read-only warned neither |
| Anticipated failures reach the model | PASS | Engine, guard, transaction and cap errors all arrived as text |
| Refused writes left nothing behind | PASS | No `mcp_e2e_rw`, `mcp_e2e_nbw`, `mcp_e2e_into`; no `venue` 9999 |
| Batch path keeps connections identifiable | PASS | `awslabs/mcp/redshift-mcp-server/0.1.0` in `stl_connection_log` |
| Unknown schema answers an empty list | PASS | `list_tables` on a missing schema, no error |

- Scope check: the only uncommitted changes were the deletion of two earlier reports, so the branch commits were the whole surface under test.
- `rw_*` cannot complete a confirmation round trip from this client, so only the fail-closed branch was reachable; `rwu_*` covered what happens once a write is allowed through.
- The Data API tags its own connections `DataAPIBatch` or `DataAPISingle` in `stl_connection_log`, which independently corroborates which path each configuration took.

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

I'll start by understanding the branch changes.Branch scope is clear: read-write mode, batch execution, named transactions, the `no_batch` fallback and its refusal wording. Starting with the baseline configuration.Fallback path verified. Now the configurations that are not denied the action, starting with the read-only guard and the batch wrapper.Writes land and are visible from another configuration. Now the transaction semantics that matter: rollback discards, commit persists.All scenarios ran against both warehouses. Findings, briefly:

The `no_batch` fallback behaves as the diff describes. A read at the denied configurations returns the same rows as the baseline but with a bare statement id (`af63e95d-…`) where the batch path returns the caller's sub-statement (`140c5661-…:3`), and the Data API's own connection tag in `stl_connection_log` shows `DataAPISingle` for those calls against `DataAPIBatch` elsewhere. Discovery, `review_cluster` and reads all keep working; writes and named transactions are refused with messages naming `redshift-data:BatchExecuteStatement`. The refusal wording from the newest commit holds: at `ACCESS_MODE=read-write` the write refusal says the server "serves reads only, whatever the access mode" rather than blaming a read-only transaction it never tried to open. The latch logged one warning across 17 statements, and after the 300s window a later read re-probed the batch action, latched again and was still served — a second warning 10 minutes on, with no restart.

The configurations that are not denied the action are unchanged. Read-only still refuses deny-listed types by name and lets the `BEGIN READ ONLY` wrapper stop the rest (`ERROR: transaction is read-only`). Named transactions carry one connection across calls (same `pg_backend_pid`, and a `SET search_path` visible to the next call and gone once the transaction closes), a failed statement aborts and drops the name, and the cap of 10 is enforced per cluster-and-database — the 11th was refused on Serverless while the provisioned cluster still accepted one. `rw_*` refused both writes before submitting anything, naming the opt-out; `rwu_*` executed writes, autocommitted them outside a transaction, discarded a rolled-back insert and persisted committed ones, verified by reading them back through the read-only server.

Scratch objects were dropped and the refused writes left nothing behind: no `mcp_e2e_rw`, `mcp_e2e_nbw` or `mcp_e2e_into` table on either warehouse, and no `venue` row 9999.

[tool] Running: git status && echo "=== BRANCH ===" && git branch --show-current && echo "=== LOG ===" && git log --oneline -20

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Running: git log --oneline origin/main -1 2>/dev/null; echo "---mergebase---"; git merge-base HEAD 6d6067cd; echo "--- diffstat vs 6d6067cd ---"; git diff --stat 6d6067cd HEAD

[tool] Running: git diff --stat; echo "=== unstaged full (non-report) ==="; git diff -- . ':!e2e_tests/reports' | head -100

[tool] status: Completed

[tool] status: Completed

[tool] Running: git diff --stat c9102a9a HEAD -- src/redshift-mcp-server

[tool] Running: git log c9102a9a..HEAD --format='=== %h %s%n%b'

[tool] status: Completed

[tool] status: Completed

[tool] Reading consts.py:1, sql_guard.py:1

[tool] status: Completed

[tool] Running: grep -n "no_batch\|NO_BATCH\|FALLBACK\|AccessDenied" awslabs/redshift_mcp_server/*.py | head -60; echo "=== banner ==="; grep -n "^# ---" awslabs/redshift_mcp_server/redshift.py

[tool] status: Completed

[tool] Reading redshift.py:56-175, redshift.py:431-680

[tool] status: Completed

[tool] Reading redshift.py:829-968

[tool] status: Completed

[tool] Running: grep -n "^async def test_\|^def test_\|^class Test" tests/test_redshift.py | sed -n '1,400p'

[tool] status: Completed

[tool] Running: sed -n '2368,2760p' tests/test_redshift.py

[tool] status: Completed

[tool] Running: grep -n "class Test\|    async def test_\|    def test_" tests/test_server.py | sed -n '1,250p'

[tool] status: Completed

[tool] Running: sed -n '1949,2100p' tests/test_redshift.py; echo ...; grep -n "    async def test_\|    def test_\|        \"\"\"" tests/test_redshift.py | sed -n '/^19[5-9][0-9]/,$p' | sed -n '1,140p'

[tool] status: Completed

[tool] Running: grep -n "def \|ACCESS_MODE\|_skip_write_confirmation\|_current_settings\|elicit\|ToolError" awslabs/redshift_mcp_server/server.py | sed -n '1,80p'

[tool] status: Completed

[tool] Running: ls e2e_tests/.kiro/agents/; python3 - <<'EOF'

import json,glob

for f in glob.glob('e2e_tests/.kiro/agents/*.json'):

    d=json.load(open(f))

    for name,srv in d.get('mcpServers',{}).items():

    ...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: for f in e2e_tests/.logs/awslabs.redshift-mcp-server-no-batch.log e2e_tests/.logs/awslabs.redshift-mcp-server-no-batch-write.log; do echo "=== $f"; grep -c "BatchExecuteStatement is denied" $f; gre...

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

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

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

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: date -u +%H:%M:%S; grep -n "BatchExecuteStatement is denied" e2e_tests/.logs/awslabs.redshift-mcp-server-no-batch.log | cut -c1-120; echo "-- total compat statements:"; grep -c "on the compatibilit...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: for f in e2e_tests/.logs/*.log; do echo "=== $(basename $f)"; grep -c "AccessDenied" $f; grep "| ERROR" $f | sed 's/.*ERROR *| *//' | cut -c1-110 | sort | uniq -c | sort -rn | head -8; done

[tool] status: Completed

[tool] Running: grep -n "WARNING\|elicit\|confirm\|Batch" e2e_tests/.logs/awslabs.redshift-mcp-server-read-write.log | cut -c1-160 | tail -12; echo "-- submits:"; grep -c "Executed batch\|batch " e2e_tests/.logs/a...

[tool] status: Completed

[tool] Running: head -3 e2e_tests/.logs/awslabs.redshift-mcp-server-read-write-unsafe.log | cut -c1-260; echo "== nbw:"; head -2 e2e_tests/.logs/awslabs.redshift-mcp-server-no-batch-write.log | cut -c1-200; echo "...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/review_cluster

[tool] status: Completed

[tool] status: Completed
