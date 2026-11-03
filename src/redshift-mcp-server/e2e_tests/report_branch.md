# End-to-end test: Changes on this branch

2026-11-03 21:38 UTC

- **Scenario**: `branch`
- **Code under test**: `feat/redshift-guide-skill` at `f67f46ea`
- **Agent**: `kiro-cli`, model `claude-opus-5`
- **Exit status**: `0`
- **Duration**: 9.1 min
- **Region**: `us-east-1`
- **Provisioned**: `mcp-e2e-provisioned`, ra3.large x2
- **Serverless**: `mcp-e2e-serverless`, 8 RPU
- **Sample data**: `tickit` in `dev`, 424,319 rows each

## Summary

| Scenario | Result | Comment |
|---|---|---|
| `retrieve_skill_file` with no argument returns the guide, frontmatter stripped, single chunk, no structured copy | PASS | |
| Guide pointer leads the server instructions, and the pointer + Current Settings block fits the 2,048-char window (387 chars) | PASS | |
| Guide pointer is first in the description of every tool but `retrieve_skill_file`, at all five configurations | PASS | |
| `retrieve_skill_file` description lists each multi-chunk reference with its chunk count | PASS | Lists exactly the three 35–38 KB files as 2 chunks; matches the files on disk |
| Final chunk of a two-chunk reference is the file's exact tail and carries no continuation marker | PASS | `references/redshift-storage-remediation.md` chunk 2, char 25,000 onward |
| A chunk past the end is refused, naming the last chunk | PASS | `Chunk 3 not found: ... ends at chunk 2.` |
| An unlisted path is refused and the refusal lists the available references | PASS | `SKILL.md` and `references/../../server.py` both refused; 12 references listed |
| Every reference the guide cites is in the served set, and nothing else is | PASS | 12 cited = 12 available |
| Guide files served at a configuration denied `BatchExecuteStatement` | PASS | No AWS call involved |
| Each chunk served is logged by path and number | PASS | `Serving skill file <path> chunk N of M`, the format the harness grades on |
| Eight tools registered per configuration | PASS | |
| Compatibility-path read reports the server's application name, provisioned and serverless | PASS | `awslabs/mcp/redshift-mcp-server/0.1.2`; before this branch the path left it unset |
| The SET and the caller's statement share one session on the compatibility path | PASS | One `session_id` in `sys_query_history`; one SET per read in `list-statements` |
| `query_id` returned is the caller's statement, not the SET | PASS | `describe-statement` returns the caller's SQL and the session id |
| Compatibility-path session is released shortly after the statement | PASS | `Session is not available` when reused minutes later |
| A failing SET fails the call with the engine's message and the caller's statement is never submitted | PASS | Bad database; canary SQL absent from `list-statements`, one statement in the log |
| TICKIT read returns correct data over the compatibility path | PASS | 49,990 users; 8,798 events |
| Catalog discovery over the compatibility path | PASS | `nb_list_tables` (7 tables), `nb_list_columns` |
| `review_cluster` over the compatibility path | PASS | 8 queries, 32 signals, 2 findings; 16 statements with no session exhaustion |
| Write refused at read-write + batch-denied, naming the denied action and the 300s re-probe | PASS | |
| Named transaction refused at both batch-denied configurations | PASS | Read-only and read-write wording both correct |
| `MAX_RESULT_ROWS` still enforced on the compatibility path | PASS | 1,001 rows refused whole |
| Batch-path read unchanged: tagged session, sub-statement `query_id` | PASS | `...:3` suffix distinguishes it from the compatibility path |
| Read-only wrapper still refuses a write on the batch path | PASS | `ERROR: transaction is read-only` |
| Named transaction across calls shares one connection and commits | PASS | Same `pg_backend_pid()` in both calls |
| Unconfirmed write at `rwu_` runs, persists across calls, and was cleaned up | PASS | Scratch table in `public`, dropped |
| Read at `rw_` runs with no confirmation | PASS | |
| `list_clusters` unchanged | PASS | Both harness warehouses `available`, other clusters untouched |

- Not reachable in this run: the `rw_` write confirmation itself (accept/decline needs a client that can prompt), and a compatibility-path result spanning more than one Data API page (it would have to return megabytes through the tool). The statement-id change that page reading depends on was verified instead through `describe-statement`.
- The read-write role has no `CREATE` on schema `tickit`, so the write scenarios used `public`; the scratch table was dropped.
- Both batch-denied configurations now issue two Data API statements per read instead of one, which is inherent to the change and visible as paired `on the compatibility path` log lines.

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

I'll start by understanding the current branch changes, then design and run the tests.Now I'll start the test. First, the new `retrieve_skill_file` tool.Now the compatibility path. First the targets, then the session-tagging behaviour.Now the configurations that are not denied the batch action, to confirm they are unchanged.Testing is complete. What the branch changes, and what I verified:

**`retrieve_skill_file`** (new tool, plus the guide pointer in the instructions and every other tool's description). Served the guide and reference files at both a normal and a batch-denied configuration, compared served chunks byte-for-byte against the files on disk, and exercised the refusals.

**The batch-denied compatibility path** (`nb_*`, `nbw_*`). Previously a read there ran alone with no session; now a `SET application_name` mints a session and the caller's statement runs on it. The observable is `current_setting('application_name')`, which came back `awslabs/mcp/redshift-mcp-server/0.1.2` on both warehouse types. I confirmed the pairing three ways: `sys_query_history` shows the SET and the statement on one `session_id`, `redshift-data list-statements` under the denied role shows one SET per read, and `describe-statement` on the `query_id` the tool returned shows the caller's SQL (not the SET) with the session attached. The session was already gone when probed afterwards, consistent with the drain keepalive.

[tool] Running: cd [package root] && pwd && git status && echo "=== BRANCH ===" && git branch --show-current && echo "=== LOG ===" && git log --oneline -15

[tool] Reading listing redshift-mcp-server

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd [package root] && git status --porcelain && echo "=== merge-base ===" && git merge-base HEAD origin/main 2>/dev/null || git log --oneline -1 HEA...

[tool] status: Completed

[tool] Running: cd [package root] && git diff HEAD~1 HEAD -- awslabs/redshift_mcp_server/redshift.py awslabs/redshift_mcp_server/transactions.py

[tool] status: Completed

[tool] Running: cd [package root] && git diff HEAD~1 HEAD -- awslabs/redshift_mcp_server/server.py README.md .gitignore

[tool] status: Completed

[tool] Running: cd [package root] && git diff HEAD~1 HEAD -- tests/test_redshift.py tests/test_server.py | head -500

[tool] status: Completed

[tool] Running: cd [package root] && git diff HEAD~1 HEAD -- e2e_tests/scenarios.py e2e_tests/agent.py && echo "=== rest of test_server diff ===" && git diff HEAD~...

[tool] status: Completed

[tool] Running: cd [package root] && grep -n "_APP_NAME_SQL\|_SESSION_DRAIN\|_execute_statement_fallback_no_batch\|_no_batch_denied\|FALLBACK_NO_BATCH\|def execute...

[tool] status: Completed

[tool] Running: cd [package root] && grep -n "execute_\|import" awslabs/redshift_mcp_server/catalog.py | head -20 && echo "=== review ===" && grep -rn "execute_sta...

[tool] status: Completed

[tool] Running: cd [package root] && grep -n "_no_batch_latched\|_latched\|def .*(" awslabs/redshift_mcp_server/redshift.py | grep -n "latch" | head -20; echo "---...

[tool] status: Completed

[tool] Running: cd [package root] && grep -rn "execute" awslabs/redshift_mcp_server/review/executor.py | head

[tool] status: Completed

[tool] Reading config.toml:1, SKILL.md:1

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] status: Completed

[tool] Running: cd [package root]/awslabs/redshift_mcp_server/skills/redshift-guide && python3 - <<'EOF' import math,pathlib for p in sorted(pathlib.Path('referenc...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server/retrieve_skill_file

[tool] Running: @awslabs.redshift-mcp-server-no-batch/retrieve_skill_file

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/list_clusters

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: aws redshift-data describe-statement --id c0667556-fd2e-4f87-8315-a7c95beaf858 --profile [profile] --region us-east-1 --query '{Sql:QueryString,Status:Status,Session:SessionId,Sub:S...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: cd [package root] && ACC=$(aws sts get-caller-identity --profile [profile] --query Account --output text) && echo "role arn: arn:aws:iam::$A...

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_tables

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd /tmp && ACC=[account] && creds=$(aws sts assume-role --role-arn "arn:aws:iam::$ACC:role/mcp-e2e-denied-batch" --role-session-name verify --profile [profile] --query 'Credentia...

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server/execute_query

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-read-write-unsafe/execute_query

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/execute_query

[tool] Running: cd [package root] && uv run --frozen python -c " from awslabs.redshift_mcp_server.server import mcp, GUIDE_POINTER, _current_settings i = mcp.instr...

[tool] status: Completed

[tool] status: Completed

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch/review_cluster

[tool] status: Completed

[tool] Running: @awslabs.redshift-mcp-server-no-batch-write/execute_query

[tool] Running: @awslabs.redshift-mcp-server-no-batch/list_columns

[tool] status: Completed

[tool] status: Completed

[tool] Running: cd [package root]/e2e_tests/.logs && for f in awslabs.redshift-mcp-server.log awslabs.redshift-mcp-server-no-batch.log; do echo "=== $f ==="; grep ...

[tool] status: Completed

[tool] Running: cd [package root]/e2e_tests/.logs && echo "=== guide lines at the no-batch config ===" && grep "Serving skill file" awslabs.redshift-mcp-server-no-...

[tool] status: Completed
