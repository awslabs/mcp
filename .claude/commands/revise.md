---
description: Address review feedback from the latest /review findings file
---

Read the latest review findings and fix them.

## Procedure

1. Identify the findings file: `/tmp/cr-review-<branch>.md` where `<branch>` is current branch with `/` → `-`. If missing, tell the user to run `/review` first and stop.

2. Parse the file into Blockers, Suggestions, Nits.

3. **Default scope**: address every Blocker and every Suggestion. Skip Nits unless the user passes `--include-nits` (check `$ARGUMENTS`).

4. For each item to address:
   - Read the cited file and surrounding context (not just the cited line).
   - Apply the concrete fix described under `Fix:`. If the fix description is ambiguous, use your judgment and note the decision in the commit message body.
   - If you disagree with a finding after reading the code, skip it and record the reason in the post-run summary rather than the commit message.

5. **Commit strategy**: one commit per severity tier, not one per item.
   - Stage and commit all Blocker fixes together with subject `fix(review): address blockers from /review` and body listing `B1`, `B2`, …
   - Same for Suggestions: `refactor(review): address suggestions from /review`.
   - Same for Nits if included: `chore(review): address nits from /review`.
   - Use Conventional Commits per user's git steering. Follow the user's policy: commit only, never push.

6. **Build/test after each commit tier**. If tests exist in the affected package, run them. If a fix breaks the build, do not proceed to the next tier — fix forward, amend the commit (local only, pre-push), or revert the offending change.

7. **Post-run summary** printed to terminal:
   - Items addressed (by ID): `B1, B2, S1, S3`
   - Items skipped and why: `S2 — disagreed, rationale: …`
   - Commits created (SHAs)
   - Test status per tier

Do NOT:
- Push anything. User pushes manually.
- Re-run `/review` — that's `/auto-revise`'s job.
- Address Nits unless `--include-nits` is in `$ARGUMENTS`.
- Invent new issues outside the findings file.

## Arguments
`$ARGUMENTS` may contain:
- `--include-nits` — also address Nits
- `--only B1,S3` — address only specific IDs
- `--skip N2,S4` — skip specific IDs
