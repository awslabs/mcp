# End-to-end test: Changes on this branch

2026-09-26 00:08 UTC

- **Scenario**: `branch`
- **Code under test**: `feat/redshift-session-redesign` at `6f2ec534`, uncommitted changes
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 15.0 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| `cluster_type` accepted for the matching type on every cluster-taking tool, both warehouses | PASS | Checked on `execute_query`, all four discovery tools and `review_cluster`. |
| `cluster_type` naming the other type is refused and names what was found | PASS | "No serverless cluster named mcp-e2e-provisioned was found. Found instead: a provisioned one." |
| A refusal states how old the stored cluster lookup is, and `list_clusters` resets it | PASS | 58 seconds before `list_clusters`, 5 seconds after. |
| The old `provisioned:<identifier>` qualified form no longer resolves | PASS | Read as a plain identifier: "Cluster provisioned:mcp-e2e-provisioned not found", pointing at `list_clusters`. |
| One cluster addressed with and without `cluster_type` is one transaction namespace | PASS | Opened with the type, continued and committed without it; reopening the bare name was refused as already open. |
| The batch-denial latch is keyed the same way however the cluster was addressed | PASS | Denied-batch write refused identically with and without the type; log keys the latch `mcp-e2e-provisioned (provisioned)`. |
| A result over `MAX_RESULT_ROWS` is refused, quoting the result's real size | PASS | 172456 rows and 1001 rows both refused; nothing returned. |
| A result exactly at the cap is returned whole | PASS | 1000 rows, `row_count` 1000. |
| The result cap applies on the denied-batch fallback path | PASS | Same refusal for 1001 rows through `nb_execute_query`. |
| An over-cap result inside an open transaction: the statement ran, the transaction survives | PASS | Told not to rerun a write; the transaction's staged rows were then read back successfully. |
| An over-cap result submitted with `commit_transaction`: the COMMIT stands and the name is released | PASS | "ran its COMMIT, which stands, and then failed while its result was being read"; the name was then unknown. |
| Session-control functions are refused in read-only mode | PASS | `set_config`, `pg_terminate_backend`, `change_query_priority`; also `pg_catalog.`-qualified and inside a WHERE clause. |
| Those same function names as string data are still reads | PASS | |
| A session-control call counts as a write in read-write mode | PASS | `rw_*` refused it for want of elicitation; `nbw_*` refused it as a write on the fallback. |
| `CALL` and `TRUNCATE` are refused inside a named transaction and as an opening statement | PASS | Reworded advice: "Run it without a transaction parameter, after closing any transaction it belongs with." |
| A failed `CALL` outside a transaction is hedged as possibly part-committed; an ordinary failed write is not | PASS | Control case returned the bare engine error. |
| A failed statement inside a transaction releases it and says nothing it staged can be committed | PASS | No false "may still be running" clause, since the batch was seen to conclude. |
| A failed opening statement reports the transaction as not opened and frees the name | PASS | "Transaction 'badopen' was not opened. Statement failed: ERROR: division by zero"; the name reopened cleanly. |
| A statement the guard refuses leaves an open transaction as it was | PASS | Transaction still usable after two refusals. |
| Denied-batch fallback: reads work, writes and transactions refused naming the grant and the re-probe window | PASS | Both `nb_*` and `nbw_*`; refusals now name the 300-second window in both directions. |
| Denied-batch: a statement or closer on a name that is not open reports it missing, not a denial | PASS | Target written as `mcp-e2e-provisioned (provisioned):dev`, with the reworded list of causes. |
| The batch path is re-probed once per window rather than per statement | PASS | Latch re-set 23:40:30 then 23:58:19 for the same cluster, with reads served in between. |
| Value typing matches the documented contract | PASS | SMALLINT/INTEGER/BIGINT as integers, REAL/DOUBLE as floats, boolean, null, VARBYTE as base64 text, DECIMAL/date/SUPER as strings. |
| Serverless workgroup fields are complete without the per-workgroup `GetWorkgroup` call | PASS | Endpoint, port 5439, real `vpc_id`, `publicly_accessible` and tags all present. |
| `review_cluster` takes `cluster_type`, refuses a mismatch, and resolves freshly | PASS | Mismatch refusal carried no lookup-age note, which only a fresh resolve produces. |
| `review_cluster` scoping and signal counting | PASS | 48 signals evaluated with the provisioned-only queries on the cluster; 32 with `ServerlessScaling` on the workgroup. |
| Client construction reports the profile and region it resolved | PASS | Profile servers log their profile; the denied servers log `default` with `AWS_REGION`, i.e. no inherited profile. |
| Behaviour under the configurations not denied the batch action is unchanged | PASS | `ro_*` still wraps a write into "transaction is read-only", `rw_*` runs reads unconfirmed, `rwu_*` writes and drops a real table unconfirmed. |
| Package unit suite against this working tree | PASS | 717 passed. |

- Multi-page result reading was not verified live. A result spanning more than one Data API page needs rows wide enough that returning them would be megabytes in the transcript, and anything over 1000 rows is refused from the first page, so the only reachable multi-page case is one this harness cannot afford to receive. Covered by unit tests.
- Four branch behaviours are unreachable from this harness and were left to the unit suite: the empty-`AWS_*` scrub and the malformed `LOG_LEVEL` / empty `LOG_FILE` startup paths, since the generated config sets valid values; `list_clusters` refusing an empty list when one half of discovery is denied, since both listings are permitted here; `MAX_RESULT_PAGES` and a repeated page token; and a confirmed write on a latched cluster, since no configuration combines write confirmation with the batch denial.
- `rw_*` never completes a confirmation round trip — the CLI advertises no elicitation, so every write there is refused fail-closed. That is the documented limit of this harness, not a branch regression; `rwu_*` covers what happens once a write is allowed through.
- Unrelated to the branch: the IAM role cannot read `stv_slices` on the Serverless workgroup, so warehouse-identity probes there used `tickit` tables instead.

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

I'll start by understanding the branch changes.Branch scope is large. Starting with cluster discovery and the new `cluster_type` parameter.Discovery looks healthy on both configurations, with serverless fields (port, vpc_id, publicly_accessible, tags) intact now that `GetWorkgroup` is gone. Now the new `cluster_type` parameter.Discovery tools all accept and forward `cluster_type`. Now the new result-size cap.Result cap holds on both paths, including the exact boundary. Now the SQL guard's new session-control functions.Fallback path next: the denied-batch configurations.Unit suite is green (717 passed) and I have live coverage of the branch surface. Cleanup done: no transactions left open, no scratch objects.

What I exercised, in brief:

- **`cluster_type`** (new parameter on all six cluster-taking tools): accepted for the matching type on both warehouses, refused when it names the other type, and the old `provisioned:<identifier>` qualified form is gone — it now reads as a plain identifier that is not found. Refusals carry the age of the stored cluster lookup ("last looked up 58 seconds ago"), and `list_clusters` resets it (next refusal said 5 seconds). `review_cluster` resolves fresh, so its refusal carries no age note at all.

- **`MAX_RESULT_ROWS`** (new, default 1000): 172456 and 1001-row results refused quoting the real total, 1000 returned whole, and the cap holds on the denied-batch fallback path too. Inside an open transaction the over-cap failure reports the statement as having run with the transaction still open — verified by reading its staged rows afterwards — and submitted with `commit_transaction` it reports the COMMIT as standing and releases the name.

- **New session-control denials** (`set_config`, `pg_cancel_backend`, `pg_terminate_backend`, the three `change_*_priority`): refused in read-only mode including schema-qualified and buried in a predicate; treated as writes in read-write mode; the same names as string literals are still reads.

- **`CALL`**: refused inside a named transaction and as an opening statement, and a failed `CALL` outside one is hedged as possibly having committed part of its work, where an ordinary failed write is not.

- **Denied-batch configurations**: reads work, writes and transactions refused with wording that now names the 300-second re-probe window, and a statement or closer on a name that is not open reports it missing against the canonical target `mcp-e2e-provisioned (provisioned):dev` rather than as a denial. The server log shows the latch keyed that same way per cluster, and one latch per re-probe window (23:40:30, then 23:58:19).

- **Transaction outcome reporting**: a failed statement releases the transaction with the new wording and frees the name; a failed opening statement says it "was not opened" with no false claim that anything may still be running; a guard refusal leaves an open transaction untouched.

[tool] Running: git status && echo "=== BRANCH ===" && git branch --show-current && echo "=== LOG ===" && git log --oneline -15

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Running: git diff --stat && echo "=== BASE ===" && git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main 2>/dev/null || echo "no main"

[tool] status: Completed

[tool] Running: git diff -- awslabs/redshift_mcp_server/consts.py awslabs/redshift_mcp_server/settings.py awslabs/redshift_mcp_server/clients.py awslabs/redshift_mcp_server/catalog.py

[tool] status: Completed

[tool] Running: git diff -- awslabs/redshift_mcp_server/clusters.py awslabs/redshift_mcp_server/models.py

[tool] status: Completed

[tool] Running: git diff -- awslabs/redshift_mcp_server/sql_guard.py awslabs/redshift_mcp_server/transactions.py awslabs/redshift_mcp_server/review/executor.py

[tool] status: Completed

[tool] Running: git diff -- awslabs/redshift_mcp_server/server.py

[tool] status: Completed

[tool] Running: git diff -- awslabs/redshift_mcp_server/redshift.py | head -700

[tool] status: Completed

[tool] Running: git diff -- awslabs/redshift_mcp_server/redshift.py | sed -n '700,1500p'

[tool] status: Completed

[tool] Running: git diff -- awslabs/redshift_mcp_server/redshift.py | sed -n '1500,2000p'

[tool] status: Completed

[tool] Running: git diff -U0 -- tests/ | grep -E '^\+.*(def test_|async def test_)' | sed 's/^+ *//' | sed 's/(self.*//;s/(.*//' | sort -u

[tool] status: Completed

[tool] Reading scenarios.py:1

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_clusters

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_schemas

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

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

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: sed -n '250,400p' awslabs/redshift_mcp_server/sql_guard.py

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] status: Completed

[tool] Running: python3 -c "

import json,glob

for p in glob.glob('e2e_tests/.kiro/agents/*.json'):

    d=json.load(open(p))

    for name,cfg in d.get('mcpServers',{}).items():

        env=cfg.get('env',{})

       ...

[tool] status: Completed

[tool] Running: cd e2e_tests/.logs && for f in awslabs.redshift-mcp-server.log awslabs.redshift-mcp-server-no-batch.log; do echo "== $f"; grep -h 'Created .* client with' "$f" | sort -u | tail -5; done; echo "== l...

[tool] status: Completed

[tool] Running: echo "== latch events per cluster, this run"; grep -h '_latch_no_batch' e2e_tests/.logs/awslabs.redshift-mcp-server-no-batch.log | awk '{print $1, $2, $0}' | grep -o '2026-09-25 23:[0-9][0-9]:[0-9]...

[tool] Running: timeout 900 uv run pytest -q 2>&1 | tail -15

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] status: Completed
