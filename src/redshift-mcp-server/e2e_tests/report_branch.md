# End-to-end test: Changes on this branch

2026-09-17 01:41 UTC

- **Scenario**: `branch`
- **Code under test**: `feat/redshift-session-redesign` at `197b97c0`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 27.9 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| list_clusters mapping: lowercase status on both warehouse types | PASS | All 6 clusters report `available`; serverless no longer reports `AVAILABLE` |
| list_clusters: serverless vpc_id is a real VPC | PASS | `vpc-07563c7a` from `endpoint.vpcEndpoints[]`, matching the provisioned mapper, not a `subnet-*` |
| Catalog discovery (databases, schemas, tables, columns) on both warehouses | PASS | 7 tickit tables and full column metadata on each; `database_type` includes `auto mounted catalog`, as documented |
| A database is connected to, a schema and a table are filtered for | PASS | Unknown database errors (`FATAL: database "no_such_db" does not exist`); unknown schema and unknown table return empty |
| Unknown cluster identifier | PASS | "not found. Please use list_clusters" with no spurious denied-listing clause, both discovery halves being permitted |
| Absent sql refused as absent, not as multi-statement | PASS | Blank, whitespace, `;` and comment-only all answer `sql holds no statement to execute`; two statements still answer the single-statement rule |
| Statements carrying hidden SQL denied in read-only mode | PASS | PREPARE, EXECUTE, DECLARE and FETCH each refused by name, on both warehouses |
| The function form of SET denied in read-only mode | PASS | Bare and `pg_catalog.`-qualified `set_config` refused as `SET_CONFIG`; `current_setting` and the string literal `'set_config'` still read, with `transaction_read_only = on` |
| SELECT ... INTO behind a set operation or parentheses is a write | PASS | Both the UNION and doubly-parenthesised forms refused by the fallback, where `might_write` is the only gate |
| TRUNCATE and CALL refused inside a named transaction | PASS | Both refused in read-write mode; standalone TRUNCATE runs, so the refusal is scoped to a transaction being in play |
| Transaction control refused to a statement in read-write mode | PASS | A bare `COMMIT` is pointed at the transaction parameters |
| A transaction name is stored stripped | PASS | Opened as `'  pad  '`, took a statement as `'pad'`, committed as `'\tpad\n'` |
| A closed name reports the commonest cause first | PASS | "An earlier call committed or rolled it back" leads the disjunction, and the just-committed work was in fact present |
| A missing transaction names the pair it searched | PASS | Same name open on serverless answers `No open transaction named 'xdb' on mcp-e2e-provisioned:dev` |
| Transaction round trips: commit persists, rollback discards | PASS | Verified by reading the table from another configuration; both warehouses |
| A failed statement aborts the transaction and releases its name | PASS | Its insert was discarded and the name answers as missing rather than as a retryable AWS error |
| A write that concluded badly is reported plainly | PASS | No "may or may not have been applied" hedge on an unwrapped failing INSERT |
| A lost session is recognised at the default keepalive | PASS | Service answered `Session is not available`; name released and reported as missing rather than a raw ValidationException |
| review_cluster counts signals, not queries, and keys findings by signal | PASS | 37 signals / 8 queries on serverless, 55 / 11 on provisioned; nested-loop signal carries REC_009 and REC_019 as one finding; REC_019 appears under three distinct signals as three findings |
| Review sort-key signal tests NULL rather than the empty string | PASS | 1 of 9 tables matches `sortkey1 IS NULL`; the old `= ''` and the old NOT LIKE guard both match 0 |
| Review diststyle signal relabelled "named like a date" | PASS | `KEY(dateid)` on a smallint is what matches, as the new label admits; the added `AUTO%` guard changed nothing here for want of an AUTO-diststyle table |
| Fallback serves reads under denied credentials | PASS | User-table reads, all four catalog tools and a full review_cluster on both warehouses |
| Fallback refuses writes with the corrected wording | PASS | Identical refusal at `nb_*` and `nbw_*`, naming the action and stating that granting it restores writes in read-write mode while read-only refuses either way |
| Fallback refuses named transactions | PASS | Both the pre-emptive arm and the mid-call arm (first serverless call at `nbw_*`) reached, each with its own wording |
| Batch-denied latch is scoped per cluster and names it | PASS | Two separate latch warnings in one process, each naming its cluster; the previous run's lines in the same log name none |
| One ERROR line per failed statement | PASS | Division by zero logged once at ERROR via `_tool_failed`, twice at DEBUG |
| Read-write mode fails closed when the client cannot confirm | PASS | Write refused naming UNSAFE_SKIP_WRITE_CONFIRMATION; a recognized read ran unconfirmed |
| Configurations not denied the batch action are unchanged | PASS | `ro_*`, `rw_*` and `rwu_*` behaved identically throughout, on both warehouses, while the denied pair was latched |

- Not reachable in this run, and left to the unit suite: the per-action confirmation wording (this CLI does not advertise elicitation, so `rw_*` refuses instead of prompting); closing a transaction while latched (a transaction cannot be open under denied credentials, since opening needs the batch action); the refusal naming a denied discovery half (both halves are permitted for all five configurations); `NoRegionError` (the servers carry a fixed profile and region); and the injected-failure and race paths behind `9a12af51`, `b08a6aff`, `c12da0b1` and `f44ce066`.
- Environment, not the server: the `ro_*`, `rw_*` and `rwu_*` servers initially failed every call with "Cannot detect shell" from the profile's isengardcli `credential_process`. Fixed by writing `shell = bash` to `~/.aws/isengardcli`; a run on a fresh machine will hit the same thing.
- Scratch objects created for the write scenarios (schema `e2e_scratch` on the provisioned cluster) were dropped, and the seeded `tickit` schema is intact on both warehouses.

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

I'll start by understanding the branch changes.Working tree is clean, so scope is the committed branch diff. Let me find the branch point.Large branch. Let me read the code the fixes landed in, starting with the guard and the fallback.Now let me verify the environment and the denial are in effect.The `ro_*`, `rw_*`, `rwu_*` servers can't fetch credentials: isengardcli's `shell = detect` fails inside the MCP server process. Setting the shell explicitly in the isengardcli config is a local, reversible fix.S1 holds: lowercase status on both types, and serverless reports `vpc-07563c7a` rather than a subnet. Now the catalog tools on both warehouses.Now the write and transaction paths under `rwu_`. Creating a scratch schema on the e2e cluster (not touching the seeded `tickit` tables).Cleaning up the scratch objects I created.One branch fix (session-gone detection at the default 600s keepalive) is reachable live. Opening a transaction to leave idle.Test run complete. Everything I could reach live behaved as the branch claims; below is what I checked and where the evidence sits.

Scope was the 24 commits since the last committed e2e report (`58ad5966`), which is everything the existing `report_branch.md` does not cover; the working tree is clean, so there were no uncommitted changes to add. The unit suite also passes on this tree (517 tests).

One environment fix was needed first: the `ro_*`, `rw_*` and `rwu_*` servers could not fetch credentials at all, because the profile's `credential_process` runs isengardcli with `shell = detect`, which fails inside the server process. I set `shell = bash` in `~/.aws/isengardcli`. That is a local, reversible change outside the package, but worth knowing for the next run.

Highlights of the evidence:

- The batch-denied latch is now per cluster and names it. Today's log lines read `BatchExecuteStatement is denied on mcp-e2e-provisioned` and, separately, `... on mcp-e2e-serverless` in the same process — the second cluster still attempted a batch, which a process-global latch would have skipped. The pre-fix lines from the previous run, in the same file, say only "is denied".

- The session-gone widening is reachable at the default 600s keepalive. A transaction left idle for ~12 minutes was answered by the service with `Session is not available` — the marker the old expiry-only match missed — and the server recognised it, released the name and returned the missing-transaction message rather than a raw `ValidationException`.

- `review_cluster` now reports 37 signals across 8 queries on serverless and 55 across 11 on provisioned, rather than the query count; findings are unique per signal and section, the nested-loop signal carries both `REC_009` and `REC_019` as one finding, and `REC_019` appears under three distinct WLM signals as three findings.

- The sort-key predicate matches: 1 of 9 tables has `sortkey1 IS NULL`, while both the old `= ''` test and the old `NOT LIKE` guard match 0.

- A write that concluded badly is reported as `Statement failed: ERROR: division by zero` with no "may or may not have been applied" hedge, and a failed statement writes exactly one ERROR line, with the two inner sites at DEBUG.

[tool] Running: git status && echo "=== BRANCH ===" && git branch --show-current && echo "=== LOG ===" && git log --oneline -15

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Running: git log --oneline -30 | tail -20; echo "=== branches ==="; git branch -a | head -20; echo "=== merge-base with main ==="; for b in main master origin/main origin/master; do git rev-parse --verify -...

[tool] status: Completed

[tool] Reading scenarios.py:1

[tool] Running: git log --oneline -3 -- e2e_tests/report_branch.md; echo "=== unpushed ==="; git log --oneline origin/feat/redshift-session-redesign..HEAD | cat

[tool] status: Completed

[tool] status: Completed

[tool] Running: echo "=== since last e2e report (58ad5966..HEAD) ==="; git diff --stat 58ad5966..HEAD | cat; echo; echo "=== vs main ==="; git diff --stat main...HEAD | cat

[tool] status: Completed

[tool] Running: git log 58ad5966..HEAD --format='===== %h %s%n%b' | cat

[tool] status: Completed

[tool] Reading sql_guard.py:1

[tool] Reading transactions.py:1

[tool] status: Completed

[tool] status: Completed

[tool] Running: grep -n "_FALLBACK\|no_batch_latched\|_no_batch_active\|_no_batch_since\|denied_sink\|Grant the action\|holds no statement" awslabs/redshift_mcp_server/*.py | head -60

[tool] status: Completed

[tool] Reading redshift.py:61-190, redshift.py:441-700

[tool] status: Completed

[tool] Reading clusters.py:31

[tool] Reading server.py:181-360

[tool] status: Completed

[tool] status: Completed

[tool] Running: git diff 58ad5966..HEAD -- tests/ | grep -E '^\+\s*(def|async def) test' | sed 's/^+\s*//' | sort -u

[tool] status: Completed

[tool] Running: grep -n -A 22 "def test_statements_carrying_hidden_sql_are_rejected\|def test_the_function_form_of_set_is_rejected_too\|def test_set_config_as_a_string_literal_is_still_a_read\|def test_select_into...

[tool] status: Completed

[tool] Running: sed -n '280,300p' tests/test_sql_guard.py; echo "=== padded ==="; grep -n -B2 -A 20 "def test_a_padded_name_is_the_same_transaction_as_an_unpadded_one" tests/test_server.py tests/test_transactions....

[tool] status: Completed

[tool] Running: grep -rn "padded_name" tests/ | head; echo "=== signals_evaluated ==="; grep -n -B4 -A 12 "signals_evaluated" awslabs/redshift_mcp_server/review/executor.py | head -60; echo "=== sortkey signal ===...

[tool] status: Completed

[tool] Running: grep -n -B3 -A 20 "_resolve_transaction_action" awslabs/redshift_mcp_server/redshift.py | head -70; echo "=== padded test ==="; sed -n '1080,1115p' tests/test_redshift.py

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] Running: cat e2e_tests/config.toml; echo "=== profile ==="; grep -A5 -i "$(grep profile e2e_tests/config.toml | head -1 | sed 's/.*= *//;s/"//g')" ~/.aws/config | head -20

[tool] status: Completed

[tool] status: Completed

[tool] Running: env -u SHELL isengardcli credentials 103299721769 --role Admin --awscli 2>&1 | tail -5; echo "--- with SHELL ---"; isengardcli credentials 103299721769 --role Admin --awscli 2>&1 | head -c 200

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] Running: isengardcli configshow 2>&1 | head -30; echo "=== config file ==="; ls -la ~/.isengardcli* 2>/dev/null; cat ~/.isengardcli/config 2>/dev/null | head -20

[tool] status: Completed

[tool] Running: ls -la /home/sergkono/.aws/isengardcli 2>&1; echo "---"; cat /home/sergkono/.aws/isengardcli 2>/dev/null

[tool] status: Completed

[tool] Running: printf '[isengardcli]\nshell = bash\n' > /home/sergkono/.aws/isengardcli && cat /home/sergkono/.aws/isengardcli && env -i PATH="$PATH" HOME=/home/sergkono isengardcli credentials 103299721769 --rol...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_databases

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_columns

[tool] Running: @awslabs.redshift-mcp-server/list_columns

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

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

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/review_cluster

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: sed -n '696,712p' awslabs/redshift_mcp_server/review/definitions.py

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] Running: cd e2e_tests/.logs; for f in awslabs.redshift-mcp-server-no-batch.log awslabs.redshift-mcp-server-no-batch-write.log; do echo "=== $f ==="; grep -h "BatchExecuteStatement is denied\|denied on\|comp...

[tool] status: Completed

[tool] Running: cd e2e_tests/.logs; awk '/2026-09-17/' awslabs.redshift-mcp-server-read-write-unsafe.log | grep -c "division by zero"; echo "--- ERROR lines today ---"; awk '/2026-09-17/' awslabs.redshift-mcp-serv...

[tool] status: Completed

[tool] Running: cd e2e_tests/.logs; awk '/2026-09-17/' awslabs.redshift-mcp-server-read-write-unsafe.log | grep "division by zero" | sed 's/\(.\{130\}\).*/\1/'

[tool] status: Completed

[tool] Running: grep -n -A 30 "def test_a_read_only_failure_says_nothing_of_the_kind" tests/*.py | head -45

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: timeout 900 uv run pytest -q > /tmp/unit.log 2>&1; tail -5 /tmp/unit.log

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server/list_tables

[tool] status: Completed

[tool] status: Completed

[tool] Running: grep -n "KEEPALIVE\|REPROBE\|MAX_OPEN" awslabs/redshift_mcp_server/consts.py

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] Running: sleep 300; date -u +%H:%M:%S

[tool] status: Completed

[tool] Running: sleep 300; date -u +%H:%M:%S

[tool] status: Completed

[tool] Running: grep "Opened transaction mcp-e2e-serverless:dev:expire" e2e_tests/.logs/awslabs.redshift-mcp-server-read-write-unsafe.log | tail -1; date -u +%H:%M:%S

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: grep -A2 -B2 "expire" e2e_tests/.logs/awslabs.redshift-mcp-server-read-write-unsafe.log | grep -i "session\|expire\|not available\|Closed" | tail -8

[tool] status: Completed
