# BCM readiness fixture accounts

`capture_fixtures.py` records real (read-only) AWS API responses for a known
account state into `<state>.json`. `test_bcm_readiness_replay.py` replays those
offline through the real `diagnose_readiness` router, so the detection heuristics
are asserted against *observed* AWS behavior rather than hand-authored mocks.

This doc explains how to put accounts into each state so all **12 scenarios** can
be captured.

## The 12 scenarios

| # | Intent | State slug | expect-status | expect-issue |
|---|--------|-----------|---------------|--------------|
| 1 | basic | `basic_ready` | ready | — |
| 2 | basic | `ce_not_enabled` | blocked | `cost_explorer_not_enabled` |
| 3 | basic | `ce_propagating` | pending | `cost_explorer_propagating` |
| 4 | basic | `iam_insufficient` | blocked | `insufficient_iam_permissions` |
| 5 | basic | `iam_explicit_deny` | blocked | `insufficient_iam_permissions` |
| 6 | basic | `iam_cannot_verify` | blocked | `cannot_verify_iam_permissions` |
| 7 | tag_analysis | `tags_ready` | ready | — |
| 8 | tag_analysis | `tags_inactive` | blocked | `tags_not_activated` |
| 9 | tag_analysis | `tags_none` | blocked | `tags_not_activated` |
| 10 | optimization | `coh_ready` | ready | — |
| 11 | optimization | `coh_not_enrolled` | blocked | `cost_optimization_hub_not_enrolled` |
| 12 | tag_analysis | `tags_linked_account` | blocked | `tags_not_available_in_linked_account` |

## Why only 2 accounts

The 12 scenarios collapse onto **2 accounts**:

- **IAM verdicts are role-driven, not account-driven.** IAM checks run first and
  short-circuit, so scenarios 4–6 are reproduced by assuming different roles
  (`--profile`) in any one CE-ready account.
- **Billing states are sequenceable.** `tags_none → tags_inactive → tags_ready`
  and `coh_not_enrolled → coh_ready` are points on one account's configuration
  timeline. Capture each state *before* the change that destroys it (move only
  toward *more* configuration) and one account yields all of them.
- **The CE lifecycle has a tight timing window** (`ce_not_enabled →
  ce_propagating`, before data lands), kept on its own account so a missed
  propagation window doesn't force redoing the tag/COH lifecycle.

## Account A — "Lifecycle" (scenarios 1, 4–11)

CE enabled with real spend up front; tags and COH advanced one step at a time,
capturing the earlier state *before* each transition destroys it. The IAM roles
drive scenarios 4–6 independent of billing state.

> **Critical:** the *capture* role must include `iam:SimulatePrincipalPolicy`
> (e.g. `AWSBillingReadOnlyAccess` + an inline add-on). Without it every capture
> short-circuits to `cannot_verify`.

**Roles** (each capture for 4–6 just re-runs phase 1 under a different profile):

| Role policy | Produces |
|------|----------|
| `AWSBillingReadOnlyAccess` + inline `iam:SimulatePrincipalPolicy` | capture role for 1, 7, 10 |
| Allow `ce:GetCostAndUsage`/`GetDimensionValues` + `SimulatePrincipalPolicy`, **omit `ce:GetCostForecast`** | 4 `insufficient` |
| Full billing read **+ explicit `Deny` on `ce:GetCostForecast`** | 5 `explicit_deny` |
| `AWSBillingReadOnlyAccess` **without** `SimulatePrincipalPolicy` | 6 `cannot_verify` |

**Lifecycle phases** (capture in order — never remove configuration; a removed
tag lingers as `Inactive`, so `tags_none` must come from a truly fresh account):

| Phase | State | Captures |
|-------|-------|----------|
| 1. Fresh | no tags, COH not enrolled, **CE has ≥1 non-zero day** | `tags_none` (9), `coh_not_enrolled` (11), `basic_ready` (1), IAM 4–6 |
| 2. Add inactive tags | resources tagged, none activated | `tags_inactive` (8) |
| 3. Activate a tag (wait ~24h) | one tag `Active` | `tags_ready` (7) |
| 4. Enroll in COH | COH `Active` | `coh_ready` (10) |

> **`tags_none` (9)** needs an account with **CE data *and* zero cost allocation
> tags** — the tags check only runs after the CE check passes. The CE probe also
> rejects a window ending *today* (recent days aren't ingested), so phase 1 needs
> real spend that has propagated through *yesterday*.
>
> **`tags_none.json` is the one fixture that is *derived*, not captured live.**
> `list_cost_allocation_tags` returns every tag key AWS has ever *discovered* on
> account resources, and AWS auto-emits keys (e.g. `aws:createdBy`) on virtually
> any account with resources — so a CE-enabled account that returns an empty list
> is impractical to obtain (and you can't get back to zero: a removed tag lingers
> as `Inactive`). The fixture is therefore derived from the real `tags_inactive`
> capture by emptying `CostAllocationTags`; it carries a `synthetic` field saying
> so. Its verdict is identical to `tags_inactive` (`blocked` / `tags_not_activated`),
> and the zero-tag `else` branch it models is covered directly by the unit test
> `test_tag_analysis_no_tags_exist`.

## Account B — "CE lifecycle" (scenarios 2 + 3)

Two points on one fresh account's timeline; enabling CE is a one-way door, so
capture in order:

1. **Before opening Cost Explorer** → scenario 2 (`ce_not_enabled`).
   `GetCostAndUsage` rejects the call. Two shapes observed:
   `DataUnavailableException`, and `AccessDeniedException` with `User not enabled
   for cost explorer access`. `check_cost_explorer` treats both as not-enabled.
2. **Enable CE, wait ~1h** → scenario 3 (`ce_propagating`), within the
   propagation window before any data lands (all-zero results). A `ready` result
   means data already propagated and you missed the window — use a fresh account.

## Scenario 12 — `tags_linked_account`

Captured from a **linked / member account** in an Organization. Cost allocation
tags are managed only at the management (payer) level, so
`list_cost_allocation_tags` is denied (`AccessDeniedException`: "Linked account
doesn't have access to cost allocation tags"). `check_cost_allocation_tags` turns
that into an actionable blocker. Any member account with CE enabled reproduces
it — capture with the `tag_analysis` intent.

## Capture commands

Run from the package root with the project venv. Each writes `<state>.json`.
`--profile` selects the account/role; `--state` is the fixture filename.

```bash
cd src/billing-cost-management-mcp-server
python tests/fixtures/bcm_readiness/capture_fixtures.py \
  --profile <profile> --account-id <id> --intent <intent> --state <state> \
  --expect-status <ready|blocked|pending> [--expect-issue <issue>]
```

Map `--intent`/`--state`/`--expect-*` from the scenario table above. The script
prints a `WARNING` when the observed status ≠ `--expect-status`, which usually
means the account isn't in the expected phase yet.

## Caveats

- **24h propagation gates the timeline:** enabling CE, activating a tag, and
  seeing first data each take up to 24h, so Account A's lifecycle spans a couple
  of days. Account B's `ce_propagating` is the inverse — capture ~1h after
  enabling CE, before data propagates.
- **Redaction is on by default** — account IDs, session names, and principal IDs
  are scrubbed (`capture_fixtures._redact`). Use `--no-redact` only for local
  debugging.
- **Read-only:** every call the script makes is read-only, safe against
  production-configured billing accounts.
