---
description: Loop /review → /revise until the review is clean (or only Nits remain)
---

Run review/revise in a loop until the review surfaces no actionable findings, or the iteration cap is hit.

## Arguments

- `--include-nits` (optional): also address Nits each round. Termination requires `B == 0 AND S == 0 AND N == 0`. Pass the flag through to `/revise`.

Without the flag, Nits are skipped and act as the termination signal (terminate when `B == 0 AND S == 0`).

## Procedure

Iteration cap: **10 rounds**. If still not clean after round 10, stop and report — likely signals that findings are being re-introduced or `/revise` can't make progress unassisted.

For each round `i` from 1 to 10:

1. Invoke `/review`. Wait for the findings file to be written.
2. Parse the summary line: `Blockers: B  Suggestions: S  Nits: N`.
3. Print a one-line round banner: `Round i — Blockers: B  Suggestions: S  Nits: N`.
4. **Termination check**:
   - Default: if `B == 0 AND S == 0`, stop. Report final state and exit.
   - With `--include-nits`: if `B == 0 AND S == 0 AND N == 0`, stop. Report final state and exit.
5. Otherwise invoke `/revise`. Pass `--include-nits` through if the loop was invoked with it. Wait for it to commit its changes.
6. If `/revise` reports it made no changes (disagreed with everything, or no items in scope), stop — further rounds will be identical. Report stall.
7. Archive the findings file as `/tmp/cr-review-<branch>-round-<i>.md` before the next round overwrites it, so the loop history is inspectable.

## Final report

Print a concise summary:
- Rounds executed
- Blocker/Suggestion/Nit count per round (should trend to zero for B and S — and N too if `--include-nits`)
- All commit SHAs created across rounds
- Final state: `CLEAN` (termination condition met), `STALLED` (no progress), or `CAPPED` (hit round 10)
- If CLEAN without `--include-nits`: remind the user that Nits are intentionally unaddressed and can be handled with `/revise --include-nits` if desired.

## Do not

- Push commits. User pushes manually at the end.
- Skip the cap. Infinite loops are worse than a partial result.
- Address Nits in the loop unless `--include-nits` was passed — otherwise they are the termination signal.
- Run `/review` or `/revise` in parallel — they share state in `/tmp/cr-review-<branch>.md` and must be sequential.
