# End-to-end tests

## Verifying a change

1. **Unit gate**:

   ```bash
   uv run --frozen ruff format awslabs tests e2e_tests && uv run --frozen ruff check awslabs tests e2e_tests && uv run --frozen pyright && uv run --frozen pytest -q --cov=awslabs.redshift_mcp_server --cov-fail-under=100 && uvx --quiet bandit==1.8.5 -r awslabs
   ```

2. **End-to-end run** on a committed tree, left unchanged until the run ends ([Running](#running),
   [Reports](#reports)). A PASS counts only if the report's transcript, or that run's lines in
   `e2e_tests/.logs/`, show the agent reached the change
   ([What a run cannot reach](#what-a-run-cannot-reach)).
3. **Review** by three independent reviewers in parallel, one lens each: runtime correctness of
   the riskiest area touched; caller-facing text (errors, tool descriptions, server instructions,
   README); everything else, including whether the tests fail without the fix. Fix, rerun the
   checks the fix affects, and repeat until a round finds no wrong data, wrong or misleading
   outcome, crash or false caller-facing text.
4. **Checks a person makes** in each target MCP client, with the server running this working tree
   as `agent._server` in `agent.py` does and restarted after the last edit:
   - write confirmation: accept, accept with `confirmed` unticked, decline, close;
   - with no copy of the guide the client loads itself, such as a `redshift-guide` skill, a
     Redshift question gets `retrieve_skill_file` called before the first query.

## Running

A run needs a sandbox AWS account and `kiro-cli` signed in. Start a run detached (macOS has no
`setsid`):

```bash
setsid nohup uv run python -u -m e2e_tests.run test > /tmp/e2e.log 2>&1 < /dev/null &
```

- Run one at a time.
- Killing a run skips teardown, so the cluster bills compute until you run `pause`.

## What a run cannot reach

Report a case that needs one of these as not covered:

- A write confirmed or declined.
- What a less privileged user sees.
- A result longer than one page, and the batch-denial latch's re-probe finding the action granted.

## Reports

Before committing a report (`report_*.md`), remove any credentials, user names, account ids and
profile names.
