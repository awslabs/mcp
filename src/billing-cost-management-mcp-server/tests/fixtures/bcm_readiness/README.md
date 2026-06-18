# BCM readiness fixture accounts

`capture_fixtures.py` records real (read-only) AWS API responses for a known
account state into `bcm_readiness/<state>.json`. `test_bcm_readiness_replay.py` then replays
those offline through the real `diagnose_readiness` router, so the detection
heuristics are asserted against *observed* AWS behavior rather than hand-authored
mocks.

This doc explains how to put accounts into each state so all **12 scenarios** can
be captured.

## Why only 2 accounts

The 11 scenarios collapse onto **2 accounts** because of three observations:

1. **IAM verdicts are role-driven, not account-driven.** IAM checks run **first
   and short-circuit** (`bcm_readiness_operations.diagnose_readiness`), so the
   three IAM scenarios (`cannot_verify`, `insufficient`, `explicit_deny`) are
   reproduced by assuming different roles in **any one** CE-ready account — no
   dedicated accounts needed.
2. **Billing states are sequenceable.** `tags_none → tags_inactive →
   tags_ready` and `coh_not_enrolled → coh_ready` are points on a single
   account's configuration timeline. Capture each state *before* the change that
   destroys it (move in the direction of increasing configuration) and one
   account yields all of them.
3. **The CE lifecycle has a tight timing window** (`ce_not_enabled →
   ce_propagating`, before data lands). It's kept on its own account so a missed
   propagation window doesn't force redoing the whole tag/COH lifecycle.

| Axis | Controlled by | Scenarios |
|------|---------------|-----------|
| **IAM verdict** | *Which role you assume* (the `--profile`) | `cannot_verify`, `insufficient`, `explicit_deny` |
| **Billing state** | The account's CE / tags / COH configuration over time | CE not-enabled / propagating / ready, tags ready/inactive/none, COH ready/not-enrolled |

## The 11 scenarios

| # | Intent | State slug | expect-status | expect-issue |
|---|--------|-----------|---------------|--------------|
| 1 | basic | `basic_ready` | ready | — |
| 2 | basic | `ce_not_enabled` | blocked | `cost_explorer_not_enabled` |
| 3 | basic | `ce_propagating` | pending | `cost_explorer_propagating` |
| 4 | basic | `iam_insufficient` | blocked | `insufficient_iam_permissions` |
| 5 | basic | `iam_explicit_deny` | blocked | `insufficient_iam_permissions` |
| 6 | basic | `iam_cannot_verify` | blocked | `cannot_verify_iam_permissions` (captured) |
| 7 | tag_analysis | `tags_ready` | ready | — |
| 8 | tag_analysis | `tags_inactive` | blocked | `tags_not_activated` |
| 9 | tag_analysis | `tags_none` | blocked | `tags_not_activated` |
| 10 | optimization | `coh_ready` | ready | — |
| 11 | optimization | `coh_not_enrolled` | blocked | `cost_optimization_hub_not_enrolled` |
| 12 | tag_analysis | `tags_linked_account` | blocked | `tags_not_available_in_linked_account` |

> **Scenario 12 (`tags_linked_account`)** is captured from a **linked / member
> account in an AWS Organization**. Cost allocation tags are managed only at the
> management (payer) account level, so `list_cost_allocation_tags` is denied
> outright (`AccessDeniedException`: "Linked account doesn't have access to cost
> allocation tags"). `check_cost_allocation_tags` turns that into an actionable
> blocker instead of raising. Any Organization member account with CE enabled
> reproduces it - capture with the `tag_analysis` intent.

## Account setup matrix (2 accounts)

### Account A — "Lifecycle" (scenarios 1, 4–11)

One account walked through a configuration timeline. CE is enabled with real
spend up front; tags and COH are then advanced one step at a time, capturing the
earlier state *before* each transition destroys it.

**Up-front config:**

- **Enable Cost Explorer** and let it accrue real spend (≥1 non-zero day in the
  last 14 days). Console → Cost Management → Cost Explorer. *Wait ~24h* for data.

**Roles to create** (these drive the IAM scenarios, independent of billing
state):

| Role | Policy | Produces |
|------|--------|----------|
| `BCM-Test-FullAccess` | `AWSBillingReadOnlyAccess` **+ inline `iam:SimulatePrincipalPolicy`** | The capture role for scenarios 1, 7, 10 |
| `BCM-Test-No-Forecast` | Allow `ce:GetCostAndUsage`, `ce:GetDimensionValues`, `iam:SimulatePrincipalPolicy` only — **omit `ce:GetCostForecast`** | Scenario 4 `insufficient` |
| `BCM-Test-Explicit-Deny` | Full billing read **+ an explicit `Deny` on `ce:GetCostForecast`** | Scenario 5 `explicit_deny` |
| `BCM-Test-No-Sim` | `AWSBillingReadOnlyAccess` **without** `iam:SimulatePrincipalPolicy` | Scenario 6 `cannot_verify` |

> **Critical:** the *capture* role (`BCM-Test-FullAccess`) must include
> `iam:SimulatePrincipalPolicy`. `AWSBillingReadOnlyAccess` alone does **not**
> grant it, so without the inline add-on every capture short-circuits to
> `cannot_verify`.

**Lifecycle phases** (capture in this order — move only toward *more*
configuration):

| Phase | Account state | Captures |
|-------|---------------|----------|
| 1. Fresh | no tags, COH not enrolled | `tags_none` (9), `coh_not_enrolled` (11), `basic_ready` (1), IAM 4/5/6 via the roles above |
| 2. Add inactive tags | resources tagged, none activated | `tags_inactive` (8) |
| 3. Activate a tag (wait ~24h) | one tag `Active` | `tags_ready` (7) |
| 4. Enroll in COH | COH `Active` | `coh_ready` (10) |

Go **none → inactive → active**, not inactive-then-removed: removing a tag has
its own propagation lag and a removed tag often lingers as `Inactive` in
`list_cost_allocation_tags`, so capturing `tags_none` first (on the truly fresh
account) is the only clean way to get a zero-tag result.

### Account B — "CE lifecycle: not-enabled then propagating" (scenarios 2 + 3)

Kept separate from Account A because of its tight timing window. Both CE states
are two points on one fresh account's timeline; enabling CE is a one-way door, so
capture in order:

1. **Before opening Cost Explorer**, capture scenario 2 (`ce_not_enabled`).
   `GetCostAndUsage` rejects the call with a not-enabled error. Two shapes have
   been observed in the wild: `DataUnavailableException`, and
   `AccessDeniedException` with the message `User not enabled for cost explorer
   access` (returned by a never-enabled account during capture).
   `check_cost_explorer` treats both as `cost_explorer_not_enabled`.
2. **Enable Cost Explorer**, then capture scenario 3 (`ce_propagating`) within
   the propagation window — within ~24h, before any cost data lands (all-zero
   results). Waiting ~1h after enabling is enough; a `ready` result means data
   already propagated and you missed the window (use a different fresh account).

## Capture commands

Run from the package root with the project venv. Each writes
`tests/fixtures/bcm_readiness/<state>.json`:

```bash
cd src/billing-cost-management-mcp-server

# === Account A, phase 1: fresh (no tags, COH not enrolled) ===
python tests/fixtures/bcm_readiness/capture_fixtures.py --profile acctA-full --account-id <A> \
  --intent basic_cost_visibility --state basic_ready --expect-status ready
python tests/fixtures/bcm_readiness/capture_fixtures.py --profile acctA-full --account-id <A> \
  --intent tag_analysis --state tags_none \
  --expect-status blocked --expect-issue tags_not_activated
python tests/fixtures/bcm_readiness/capture_fixtures.py --profile acctA-full --account-id <A> \
  --intent optimization --state coh_not_enrolled \
  --expect-status blocked --expect-issue cost_optimization_hub_not_enrolled

# Account A, phase 1: IAM scenarios (same state, different roles)
python tests/fixtures/bcm_readiness/capture_fixtures.py --profile acctA-noforecast --account-id <A> \
  --intent basic_cost_visibility --state iam_insufficient \
  --expect-status blocked --expect-issue insufficient_iam_permissions
python tests/fixtures/bcm_readiness/capture_fixtures.py --profile acctA-deny --account-id <A> \
  --intent basic_cost_visibility --state iam_explicit_deny \
  --expect-status blocked --expect-issue insufficient_iam_permissions
# scenario 6 already captured as iam_cannot_verify.json (BCM-Test-No-Sim role)

# === Account A, phase 2: add tags to resources, do NOT activate ===
python tests/fixtures/bcm_readiness/capture_fixtures.py --profile acctA-full --account-id <A> \
  --intent tag_analysis --state tags_inactive \
  --expect-status blocked --expect-issue tags_not_activated

# === Account A, phase 3: activate a tag, wait ~24h ===
python tests/fixtures/bcm_readiness/capture_fixtures.py --profile acctA-full --account-id <A> \
  --intent tag_analysis --state tags_ready --expect-status ready

# === Account A, phase 4: enroll in Cost Optimization Hub ===
python tests/fixtures/bcm_readiness/capture_fixtures.py --profile acctA-full --account-id <A> \
  --intent optimization --state coh_ready --expect-status ready

# === Account B, step 1: BEFORE opening Cost Explorer ===
python tests/fixtures/bcm_readiness/capture_fixtures.py --profile acctB --account-id <B> \
  --intent basic_cost_visibility --state ce_not_enabled \
  --expect-status blocked --expect-issue cost_explorer_not_enabled

# === Account B, step 2: enable CE in the console, wait ~1h, then capture ===
python tests/fixtures/bcm_readiness/capture_fixtures.py --profile acctB --account-id <B> \
  --intent basic_cost_visibility --state ce_propagating \
  --expect-status pending --expect-issue cost_explorer_propagating
```

## Caveats

- **24h propagation gates the timeline:** enabling CE, activating a tag, and
  seeing first data each take up to 24h. Account A's lifecycle therefore spans
  at least two waits — CE-data before phase 1, and tag-activation between phases
  2 and 3 — so plan for it to run over a couple of days rather than in one
  sitting. Account B's `ce_propagating` capture is the inverse: it relies on data
  *not* having propagated yet, so capture it ~1h after enabling CE. The script
  prints a `WARNING` when observed status ≠ `--expect-status`, which usually
  means the account isn't in the expected phase yet.
- **Redaction is on by default** — account IDs, session names, and principal IDs
  are scrubbed (`capture_fixtures._redact`), so fixtures are safe to commit. Use
  `--no-redact` only for local debugging.
- **Read-only:** every call the script makes is read-only, so it's safe to run
  against production-configured billing accounts.
