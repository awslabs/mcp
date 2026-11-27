# redshift-guide

A copy of the `redshift-guide` skill. The server's `retrieve_skill_file` tool serves `SKILL.md`
and `references/`; this README is never served.

## Source

- Repository: https://github.com/aws/agent-toolkit-for-aws (Apache-2.0)
- Path: `plugins/aws-data-analytics/skills/redshift-guide`
- Commit: `96a27f273291299666bcc004c7b19f27e7d9986a`, the head of `main` on 2026-10-29

## Refresh

1. Copy `SKILL.md` and `references/` from the latest `main` of the source repository. Never copy
   from a local checkout: it can hold changes not yet published.
2. Reapply the edits below.
3. Record the new commit and its date above.

## Edits

All three are in `SKILL.md`. The references are unedited. Each AWS CLI call left in them is either
a control-plane call with no tool in this server, such as `aws redshift describe-*` or `aws iam`,
or part of a Data API shell recipe for the user's own scripts. CloudWatch metrics appear only in
prose, and no tool here reads them. The paragraph the first edit adds tells the agent what to do
with both kinds of call.

| Site | Change |
|---|---|
| The paragraph after "Redshift is NOT PostgreSQL", which named the AWS MCP server | Replaced. The guide ships with this server: SQL runs through `execute_query`, one statement per call; `list_*` tools discover; `review_cluster` reviews; `retrieve_skill_file` loads a cited reference; no tool runs AWS CLI commands. Adds one sentence on system-view row visibility and on views that refuse with `permission denied`, pointing at `references/redshift-auth-authorization.md` |
| STEP 0, "Serverless or Provisioned?" | Takes the type from the question, else from the target's `list_clusters` entry, and asks only when neither settles it |
| Routing Table, the sentence before the table | Same rule as STEP 0 |
