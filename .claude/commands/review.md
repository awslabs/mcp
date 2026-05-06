---
description: Review local changes against origin/main for bugs, security, code quality, and token/context usage. Writes findings to /tmp/cr-review-<branch>.md for /revise and /auto-revise to consume.
---

You are an expert code reviewer. Review the local changes on this branch relative to `origin/main` — the same surface a PR would expose. Produce a high-signal findings file; do **not** post anywhere.

Reviews come in two distinct modes. **Read this first — it determines everything downstream.**

## Mode detection

Before anything else, ask yourself: is this the first review of this branch, or a follow-up round after you already pushed fixes?

- **First-pass mode** — no prior review state exists for this branch. Do the exhaustive multi-pass audit in Step 2A. Flag issues at all severities (Blockers / Suggestions / Nits).
- **Follow-up mode** — a prior review state file exists (see Step 1). Use the scoped flow in Step 2B. **Only new code in the diff since the last reviewed SHA is in scope for all severities.** Pre-existing code can be flagged only at Suggestion-or-above, and only when you can produce strong justification for breaking the review cycle.

The reason: repeatedly surfacing Nits that existed in earlier revisions makes reviews a never-ending ratchet. Close out the diff, don't re-audit the world.

## Where to write working files

- **Findings file** (the contract with `/revise` and `/auto-revise`): `/tmp/cr-review-<branch>.md` where `<branch>` is the current branch with `/` replaced by `-`. This path is load-bearing — do not change it.
- **State file** (persistent across review rounds, for follow-up mode): `/tmp/cr-review-<branch>-state.json`.
- **Scratch file** (multi-pass audit notes): `/tmp/cr-review-<branch>-scratch.md`. Append as you work.

`/tmp` may be cleared on reboot; a missing state file falls back to first-pass mode. That's fine.

## Step 1: Gather context and detect mode

```bash
git fetch origin main
git -P log --oneline $(git merge-base origin/main HEAD)..HEAD
git -P diff $(git merge-base origin/main HEAD)...HEAD --stat
git -P diff $(git merge-base origin/main HEAD)...HEAD > /tmp/cr-review-<branch>.diff
git -P rev-parse HEAD  # record the head SHA
```

If the branch is identical to `origin/main` (no commits ahead), write a stub findings file with all zeros and stop.

**Check for prior review state.** If `/tmp/cr-review-<branch>-state.json` exists, you're in follow-up mode:

```json
{
  "last_reviewed_sha": "<full SHA from the previous round>",
  "rounds": [
    {"sha": "...", "reviewed_at": "...", "blockers": N, "suggestions": N, "nits": N}
  ]
}
```

If the file exists → **follow-up mode** (go to Step 2B).
If not → **first-pass mode** (go to Step 2A).

## Step 2A: First-pass review (multi-pass rubric)

Do **three passes** over the changed files. Each pass uses a different lens. Write findings to the scratch file as you go — don't try to hold them all in your head.

### Pass 1 — Per-function rubric

For each public function or class added/changed in the diff, run through this checklist and **write down the result for every item** (either "found: <description>" or "checked: OK"). Forcing the write-down is what makes coverage exhaustive — a vibes-based scan will skip dimensions.

- [ ] **Every `except` block**: what's caught, what escapes, is the shape consistent with the rest of the module (`error_type` conventions, etc.)?
- [ ] **Every user-controlled string**: escaped for the target grammar (Logs Insights, SQL, regex, shell)? Length capped? Validated against an allowlist?
- [ ] **Every numeric input**: handles zero, negative, absurdly large? Upper cap applied? Type-coerced safely?
- [ ] **Every range param (start/end pairs)**: what happens at `start == end`? `start > end`? Explicit rejection or silent empty result?
- [ ] **Every `async def`**: any blocking calls (sync boto3, `time.sleep`, file I/O)? Any sequential `await` that could be `asyncio.gather`?
- [ ] **Every pagination API**: `NextToken` / `nextToken` followed? Page cap in place? Truncation surfaced to the caller?
- [ ] **Every cache (`@lru_cache`, manual dict)**: correct invalidation? Test fixtures clear it? Are errors accidentally cached?
- [ ] **Every response shape**: does the worst-case fit in ~5k tokens? `json.dumps(..., indent=2)` (doubles whitespace)? Hard `[:N]` truncation that cuts mid-word?
- [ ] **Every docstring claim**: does the code actually do what the docstring says? "parallel queries" that run serially, "cached" that aren't cached, parameters documented but ignored, etc.
- [ ] **Every parameter in the signature**: actually used in the body? Or is it accepted and silently ignored?

### Pass 2 — Cross-cutting / security lens

Read the changed files end-to-end again with these questions in mind (no per-function breakdown, just scan):

- **Injection surfaces**: any `f"..."` or `.format(...)` or `+` concatenation that builds a query/URL/command/filter clause from user input?
- **ReDoS**: any `re.search`/`re.match` with `.*` or nested quantifiers on user-provided input? Length-capped?
- **Escape hatches**: any "run arbitrary X" action (raw query, eval, exec)? Documented with a scope warning? IAM scope as the authorization boundary?
- **Secrets in responses**: could a stack trace, error message, or log line leak credentials, ARNs with account IDs, or private resource names into the LLM context?
- **IAM / resource policies**: newly permissive grants? Wildcards?
- **Tool-definition token cost**: count optional parameters on each `mcp.tool()`. Count docstring length. Flag tool definitions >500 tokens.
- **Worst-case response size**: for each tool, what's the biggest response the LLM could get back? Multiply rows × fields × avg chars. If >5k tokens, flag.

### Pass 3 — Test and contract lens

- **Tests**: do tests pass against the new code? `cd` into the package and run `pytest` if possible. If a test asserts `<= 5` but the code was changed to `<= 2`, the test is stale — flag as a bug.
- **Error contract**: is there a consistent error-shape convention (e.g., `{'error': ..., 'error_type': ...}`)? Does every error path follow it?
- **Tool-level idempotency**: are any non-idempotent operations reachable? (Usually out-of-scope for read-only MCP, but worth a check.)
- **Mocks**: do tests actually mock the boundary they claim to? (E.g., patching the wrong module path means production code isn't exercised.)

### Finalize first-pass

After three passes, de-duplicate findings in the scratch file. Group by Blocker / Suggestion / Nit per Step 4. Continue to Step 3.

## Step 2B: Follow-up review (scoped, ratchet-preserving)

In follow-up mode, the default is: **close out the diff since the last reviewed SHA, do not re-audit the whole branch.**

1. **Scope new findings to the diff since last round**:
   ```bash
   git -P diff <last_reviewed_sha>..HEAD > /tmp/cr-review-<branch>-new.diff
   ```
   Run Pass 1 + Pass 2 from Step 2A **only on the lines that appear in this diff**.

2. **Blame every candidate finding**. Before adding any item to the findings file, run `git blame -L <line>,<line> <file>` on the anchor line. If blame points to a commit older than `last_reviewed_sha`, the finding is pre-existing code — apply the ratchet rule below.

### The ratchet rule for pre-existing code

Pre-existing findings are only worth raising if they meet **all three** of:

- **Severity is Suggestion or higher** (no Nits, no style, no "consistency would be nicer")
- **Strong justification** you can articulate in one sentence: why is disrupting the review cycle worth it here?
- **Concrete user impact** described in the finding (data loss, crash, wrong answers, security blast radius)

Examples of strong justifications:
- "Silently returns empty results for a range of valid user inputs, producing wrong answers"
- "Data loss under concurrent invocation"
- "Escape hatch for arbitrary query execution without scope warning"
- "Token bloat: worst-case response is 80k tokens, exceeds most context budgets"

Examples that do **not** meet the bar:
- "Error shape is inconsistent with the new `error_type` convention" — stylistic, pre-existing.
- "Could parallelize with `asyncio.gather` for a 2x speedup on a rarely-used path" — nit, pre-existing.
- "Variable name is misleading" — no.

**When you flag pre-existing code, mark it in the finding** with a `(pre-existing at <short-sha>)` tag so the user and `/revise` can drop it if they want to preserve the ratchet.

### Findings on new diff lines

For lines that `git blame` points to the diff since `last_reviewed_sha`, **all severities are in scope** — flag every issue you find, just like first-pass mode.

## Step 3: Verify before you write a finding

- If a finding claims an API parameter is wrong, check at least one of: the SDK docs, similar usages elsewhere in the repo, or live data.
- If a finding claims "this parameter is ignored", grep for every usage of the variable in the function body.
- If a "bug" is actually a local convention (e.g., module-level AWS clients tied to `AWS_REGION`), it's not a bug. Read the surrounding module before claiming parameters are ignored.

**A finding that's wrong costs time later than a finding you didn't write.** When in doubt, phrase as a question or mark lower-severity.

## Step 4: Categorize

- **Blocker** — bugs that produce wrong answers, security issues with real blast radius, crashes, broken contracts.
- **Suggestion** — quality issues with clear user impact (latency, cost, context bloat), inconsistencies that will cause future bugs.
- **Nit** — naming, minor style, optional optimizations, tradeoff discussions.

## Step 5: Write the findings file

Write to `/tmp/cr-review-<branch>.md` using this **exact structure** — `/revise` and `/auto-revise` parse it:

```markdown
# CR Review — <branch> vs origin/main

Base: <merge-base sha>
Head: <head sha>
Commits reviewed: <N>
Files changed: <N>
Mode: first-pass | follow-up (last reviewed: <short-sha>)

## Blockers
### B1. <short title>
`path:line` — <why, 1–2 sentences>. Fix: <concrete change, with code snippet if it fits on a few lines>.

## Suggestions
### S1. <short title>
`path:line` — <why>. Fix: <concrete change>.

## Nits
### N1. <short title>
`path:line` — <why>. Fix: <concrete change>.

## What's solid
- <1–3 bullets — keep it honest, skip if nothing stands out>

## Summary
Blockers: <N>  Suggestions: <N>  Nits: <N>
```

**Constraints for each finding:**
- `path:line` anchors a specific line in the current HEAD (open the file and verify the line number hasn't drifted).
- Tag each finding with a single leading category if it helps: `**Bug:**`, `**Security:**`, `**Token/Context:**`, `**Code Quality:**`, `**Minor:**`.
- Concrete fixes beat vague advice. Include a snippet when it clarifies the change.
- Pre-existing findings (follow-up mode only) must include `(pre-existing at <short-sha>)` in the title.

Print the file path and the summary line (`Blockers: X  Suggestions: Y  Nits: Z`) to the terminal so `/auto-revise` can parse it.

## Step 6: Update state file and report back

After the findings file is written, update `/tmp/cr-review-<branch>-state.json`:

```json
{
  "last_reviewed_sha": "<HEAD sha you just reviewed>",
  "rounds": [
    ...previous rounds,
    {
      "sha": "<HEAD sha>",
      "reviewed_at": "<ISO timestamp>",
      "blockers": <N>,
      "suggestions": <N>,
      "nits": <N>
    }
  ]
}
```

Then report back in the terminal:
- Findings file path
- Summary counts
- One-line teaser per Blocker
- **If in follow-up mode**: which pre-existing findings (if any) you chose to surface, so the user can drop them before running `/revise`.

## Dimensions (reference — used by Pass 1 and Pass 2)

### Bugs
- Does it do what the commit message / PR description says it does?
- Parameters accepted but ignored.
- Off-by-one, wrong comparisons, wrong field names, wrong types (e.g. `filterLogGroupArn=<name>` instead of ARN).
- Uncaught exceptions that escape a dispatcher boundary.
- Race conditions in async code (singleton init that yields between "set instance" and "load instance").
- Pagination not followed.
- Dead code / fields collected but never consumed.
- Inconsistent error handling across a single function.
- Logic that depends on `dir()`, variable names not matching their values, docstrings contradicting code.

### Security
- Input passed into query/regex/shell/SQL without escaping. Especially: Logs Insights, OpenSearch, Cypher, any string-templated query language.
- ReDoS on regex with `.*` patterns fed user-controlled input.
- No input length caps on fields that feed into expensive matchers.
- Arbitrary code / query execution "escape hatches" — flag them even if intentional.
- Secrets in logs, error messages, or response bodies.
- Overly permissive IAM / resource policies introduced.

### Code quality
- Blocking I/O inside `async def`.
- Sequential awaits where `asyncio.gather` would fit.
- Duplicate imports inside function bodies.
- Silent exception swallowing (`except Exception: pass` with no logger).
- Missing resource cleanup (e.g., no `stop_query` on Logs Insights timeout).
- Inconsistent patterns within a module (half uses `logger.warning`, half swallows).
- Misleading variable names.

### Token / context window (most-missed dimension)
- **Tool definition cost**: how many tokens does registering this tool add to every LLM request? Docstring + optional-parameter lists can be sizeable.
- **Response cost**: worst-case size of a tool response. Run the math: rows × fields × avg chars. Flag >5k tokens.
- `json.dumps(..., indent=2)` roughly doubles whitespace tokens.
- Missing `max_results` defaults or caps.
- Hard `[:N]` truncation that cuts mid-word.
- Healthy-case paths that accidentally run heavy pipelines.
- Expensive upstream work to produce tiny LLM output.
