# Deprecation Evaluation: `awslabs.openapi-mcp-server`

_Prepared 2026-07-10_

> We recommend **deprecating** the `awslabs.openapi-mcp-server` from the awslabs/mcp GitHub repository.

## Executive Summary

`awslabs.openapi-mcp-server` (hereafter "the wrapper") is a ~6,600-LOC curation layer that builds `FastMCP(providers=[OpenAPIProvider(...)])` and adds auth, tag filtering, description enrichment, multi-spec composition, SSRF-safe fetch, and Prometheus metrics (full description in Appendix G). `awslabs/mcp` is consolidating on **AWS Service-team-endorsed servers**, so a generic wrapper over FastMCP's Apache-2.0 `OpenAPIProvider` no longer fits. Source inspection confirms **every wrapper feature is reachable today** with existing FastMCP primitives — including the two that looked like gaps: SSRF-safe fetching already ships (`ssrf_safe_fetch`), and Prometheus metrics is a few lines on the existing middleware seam. **Nothing blocks deprecation. Recommendation: refactor the wrapper to FastMCP-native features only, publish a migration guide (with glue recipes for the SSRF-fetch and metrics cases), and deprecate — no external contribution is a prerequisite.** Both audiences stay in FastMCP/Python: in-process users call `FastMCP.from_openapi`; standalone (no-code) users run a small entrypoint via `fastmcp run`. Upstreaming the glue as `contrib/` modules is an optional community give-back, off the critical path.

---

## Details

### Where the capabilities live now
Source inspection of FastMCP 3.4.4 shows **every wrapper feature is reachable today** — natively, via a hook, or via a shipped primitive. (Full evidence + FOSS survey: Appendix G.)

| Wrapper feature | Upstream today |
|---|---|
| Cognito auth | `AWSCognitoProvider` — native |
| Tag filtering | `RouteMap.tags` — native |
| Multi-spec composition | `mount` / `import_server` — native |
| Enriched descriptions | reachable via the `mcp_component_fn` hook + shipped formatter |
| SSRF-safe spec fetch | reachable today: `ssrf_safe_fetch` already ships (`server/auth/ssrf.py:242`) and is importable; call it before `from_openapi` |
| Prometheus metrics | reachable today: subclass `Middleware` + `mcp.add_middleware(...)` (the `TimingMiddleware` seam, `server/middleware/timing.py:10`) |

So **there is no hard capability gap** — every wrapper feature is reachable today with existing FastMCP primitives. SSRF-fetch and Prometheus are turnkey/packaging conveniences (a few lines of glue), not missing capabilities. (Swagger 2.0: FastMCP is 3.x-only; 2.0 users convert specs first — one documented step.)

### Why deprecate
- **Strategic (primary):** duplicates FastMCP; does not fit the Service-team-endorsed direction.
- **Low-risk:** same Apache-2.0 engine; no copyleft exposure; removes ~6.6k LOC of maintenance.

### Risks
- **SSRF-fetch / Prometheus users** must adopt a few lines of glue (import `ssrf_safe_fetch`; add a metrics middleware) — recipes go in the migration guide. No capability is lost.
- **Standalone (no-code) users** must move from CLI flags to a small Python entrypoint run via `fastmcp run` — same ecosystem, small one-time change.

### Actions
Deprecation gates only on work **fully in our control** — no external PR is a prerequisite, because every capability is reachable today (table above).

1. **Refactor the wrapper to upstream-only** — delete bespoke auth, tag-filter, enrichment, `HttpClientFactory`, and multi-spec code; use FastMCP-native equivalents (mapping in Appendix E).
2. **Publish the migration guide** with recipes for both audiences (in-process: `FastMCP.from_openapi`; standalone: `fastmcp run server.py`) and the glue cases (SSRF-safe fetch via `ssrf_safe_fetch`; a metrics middleware; Swagger 2.0 convert-first), then **deprecate**.
3. **Optional community give-backs (off the critical path):** upstream `contrib/` PRs that make the glue first-class for everyone — SSRF-safe spec fetch, a Prometheus metrics middleware, and a DX PR wiring the shipped formatter into the provider (Appendix D). Nice for the ecosystem; **not** required for our deprecation. If sequenced, do the small enrichment PR first to establish the contributor (Appendix F odds).
4. **Do not** adopt Speakeasy (ELv2) or mcpjungle (MPL-2.0).

---

## Appendix A — Verification & Confidence
- Research method: 6 search angles → 16 sources fetched → 75 claims → 25 verified under 3-vote adversarial verification (24 confirmed, 1 refuted). Licenses confirmed against raw `LICENSE` files, not just GitHub badges.
- **High confidence:** all license classifications; FastMCP maturity/backing; `ivo-toby` and `harsha-iiiv` feature sets.
- **Medium confidence:** the gap analysis (rests on absence-of-documentation).
- **Refuted (1):** a claim that higress lacks bearer/OAuth2/filtering — its exact auth surface is genuinely uncertain.

---

## Appendix B — Open Questions
1. How many users depend on SSRF-fetch or Prometheus metrics? Cognito, tag filtering, and multi-spec are already upstream; only these two need sizing for the migration guide (not as a gate).

_NOTE: adoption metrics for these two features aren't available, so sizing stays an open item — but it does not gate deprecation (users keep the capability via the migration-guide recipes); it only informs how much migration-support effort to budget._

---

## Appendix C — Ground-Truth Notes (local v1.1.0 source)
- Wrapper confirmed: `awslabs/openapi_mcp_server/server.py:394` builds `FastMCP(providers=[...])`.
- Auth modules present: `basic_auth.py`, `bearer_auth.py`, `api_key_auth.py`, `cognito_auth.py`.
- Transport: **stdio only** (`server.py:739–740`); README/CHANGELOG SSE mentions are stale.
- Naming-collision caveat: multiple distinct repos share the name `openapi-mcp-server` (janwilmake vs. snaggle-ai vs. Tim Kellogg's original) and `openapi-mcp` (jedisct1 vs. mcpjungle) — verify the exact repo before acting.
- **Upstream repo & version:** canonical repo is **`PrefectHQ/fastmcp`** (`jlowin/fastmcp` is a redirect alias — verified `gh repo view` → `nameWithOwner: PrefectHQ/fastmcp`, not a fork). Current published version **v3.4.4** (PyPI); we pin `fastmcp>=3.3.1,<4`.
- **Spec-version support (source-verified, FastMCP 3.4.4):** `from_openapi` handles **OpenAPI 3.0.x / 3.1.x only** — the parser reads the `openapi` key (never `swagger`), `openapi-pydantic` ships no v2 models, and no 2.0→3.x converter is in the dependency tree. Our server accepts Swagger 2.0 only because it depends on `prance`, which resolves 2.0→3.0. Migration therefore requires converting 2.0 specs to 3.x first (handled in the migration guide, Appendix E).
- **Upstream citations are verified against FastMCP 3.4.4** (source layout roots at `fastmcp_slim/fastmcp/`). Note the 3.4.4 reorganization: OpenAPI lives under `server/providers/openapi/`; the former `experimental/…/openapi` modules are now deprecated re-export shims over `utilities/openapi/`; `format_simple_description` no longer exists.

---

## Appendix D — Upstream Contributions (`PrefectHQ/fastmcp`)

**Process (verified):** `gh` authenticated as `scottschreckengaust`; Apache-2.0; **no CLA/DCO bot**. FastMCP's rules (`docs/development/contributing.mdx`): **issue first, one PR per issue, small scope, tests + docs required**; "opinionated framework, not a kitchen sink." Every PR must reuse FastMCP's own idioms (`RouteMap`, `mcp_component_fn`, `NotSet`, full types, async, `inline-snapshot`, `ruff`/`ty`), not port our bespoke style.

**These are optional community give-backs — none gate our deprecation** (our users get the same capability via the migration-guide recipes today). They make the glue first-class for the wider FastMCP community. Three separate issue → PR drafts:
1. **SSRF-safe spec fetch** (draft: `fastmcp-issue-draft-ssrf-spec-fetch.md`). `from_openapi` takes a parsed dict; `ssrf_safe_fetch` already ships (`server/auth/ssrf.py:242`) but is auth-scoped. Propose a `contrib/` helper that reuses it to fetch+parse a spec URL (raising the 5KB `max_size`) — reuse/expose, not new protection.
2. **Prometheus metrics** (draft: `fastmcp-issue-draft-prometheus-metrics.md`). FastMCP has tracing but no pull-based metrics; only logging-based `TimingMiddleware` (`server/middleware/timing.py:10`). Propose a `contrib/` metrics middleware on the same `Middleware`/`add_middleware` seam. Note: the upstream issue is intentionally problem-first (no metric names or exporter API); the fuller `PrometheusMiddleware` recipe in Appendix E is for our migration guide, not the issue body.
3. **Enrichment DX** (draft: `fastmcp-issue-draft.md`). Wire the shipped `format_description_with_responses` (`utilities/openapi/formatters.py:192`) into the provider so the `mcp_component_fn` recipe becomes default.

If pursued, sequence #3 first — it's the smallest/highest-accept change and establishes the contributor before the larger two (see Appendix F odds). All three validated against the label + investigation triage-bot simulations.

**Mechanics (each PR):** (1) `gh repo fork PrefectHQ/fastmcp`; (2) open a concise, human-toned issue, **await maintainer buy-in**; (3) branch off `main`; (4) implement + tests; (5) docs + `<VersionBadge />`; (6) `uv sync && uv run pre-commit run --all-files && uv run pytest` green; (7) PR fork→`PrefectHQ:main`, `Closes #<issue>`.

---

## Appendix E — Deprecation Timeline & Customer Roadmap

**Governing dates:** issue opened on `PrefectHQ/fastmcp` **once the plan is agreed**; hands-on work **commences the week of 2026-07-20**. Timeline below is a proposal for review, not a committed schedule.

| Phase | Window | Actions | Customer-facing signal |
|---|---|---|---|
| **0 — Align** | Now → wk of Jul 20 | Approve this plan; internal sign-off | None yet |
| **1 — Refactor to upstream-only + migration guide** | wk of Jul 20 (2026-07-20) → early Aug | Delete bespoke auth/tag/enrichment/`HttpClientFactory`/multi-spec code; use FastMCP-native equivalents (mapping below); write the migration guide incl. glue recipes (SSRF-fetch, metrics middleware, Swagger convert-first) | None yet |
| **2 — Announce (soft-deprecate)** | early/mid-Aug 2026 | `DeprecationWarning` + README banner; publish migration guide; no behavior change | **Deprecation announced**; server still functional |
| **3 — Maintenance-only** | ~90-day window after announce | Security/critical fixes only; migration support | Clear "migrate by" date |
| **4 — Final release + EOL** | after the window | Final PyPI release; archive repo dir; PyPI marked deprecated (kept installable); redirect docs | **EOL** |
| **— (parallel, optional)** | anytime | Upstream `contrib/` give-backs (SSRF-fetch, metrics, enrichment DX — Appendix D). Not gating; benefits the wider community | n/a |

**Customer migration guide (to publish in Phase 2)** — framed as _"adopt the upstream convention, drop the bespoke one"_, with a bespoke → native mapping table:

| Bespoke (our wrapper) | Native FastMCP convention to adopt |
|---|---|
| Custom auth adapters (`auth/*_auth.py`, incl. `cognito_auth.py`) | `server/auth/providers/*` (`aws.py` for Cognito, `bearer.py`, `jwt.py`, …) |
| Hand-rolled `--include-tags`/`--exclude-tags` | `RouteMap(tags=…)` route mapping |
| `enrich_component` description builder | `mcp_component_fn` calling `format_description_with_responses` (native today; DX PR would make it default) |
| `HttpClientFactory` | caller-supplied `httpx.AsyncClient` passed to `from_openapi` |
| `--additional-specs` multi-spec loader | `mount` / `import_server` composition |
| Env-var config schema | `from_openapi(...)` kwargs + FastMCP settings/env conventions |
| Standalone CLI (`uvx awslabs.openapi-mcp-server --spec-url …`) | small entrypoint + `fastmcp run server.py` (see below) |

- **In-process users** → `FastMCP.from_openapi(spec_dict, client=httpx_client)` using the native conventions above.
- **Standalone (no-code) users** → write a small entrypoint and run it with FastMCP's own CLI — same Python ecosystem, no third-party server needed:
  ```python
  # server.py
  # Assumption: the spec is OpenAPI 3.0.x/3.1.x. If it's Swagger/OpenAPI 2.0,
  # convert it to 3.x first (see "Swagger 2.0 users" below) — from_openapi rejects 2.0.
  import httpx
  from fastmcp import FastMCP
  mcp = FastMCP.from_openapi(
      httpx.get("https://api.example.com/openapi.json").json(),  # trusted, hardcoded URL
      client=httpx.AsyncClient(base_url="https://api.example.com"),
  )
  ```
  ```
  fastmcp run server.py --transport stdio
  ```
  `fastmcp run` auto-discovers a module-level `mcp`/`server`/`app` object (`utilities/mcp_server_config/v1/sources/filesystem.py:154`).

  ⚠️ If the spec URL is **operator- or tenant-supplied** (not hardcoded), the plain `httpx.get` above is an SSRF sink — use the shipped `ssrf_safe_fetch` instead (raising its 5KB default `max_size`):
  ```python
  # server.py — untrusted spec URL
  import asyncio, json, os, httpx
  from fastmcp import FastMCP
  from fastmcp.server.auth.ssrf import ssrf_safe_fetch  # note: currently an internal module

  spec_url = os.environ["OPENAPI_URL"]
  raw = asyncio.run(ssrf_safe_fetch(spec_url, max_size=10_000_000))  # HTTPS-only, blocks internal IPs
  mcp = FastMCP.from_openapi(json.loads(raw), client=httpx.AsyncClient(base_url=os.environ["API_URL"]))
  ```
- **Swagger 2.0 users** → convert specs to OpenAPI 3.x before calling `from_openapi` (FastMCP only supports 3.0.x / 3.1.x). Recommended: `swagger2openapi` CLI or the online Swagger Converter.
- **SSRF-fetch dependents** → use the untrusted-URL entrypoint above (`ssrf_safe_fetch` with a raised `max_size`). Its auth-module location is why the `contrib/` give-back (Appendix D) proposes a supported spec-fetch entry point.
- **Enriched descriptions** → pass an `mcp_component_fn` that runs the shipped formatter over each component (this is what our `enrich_component` does today):
  ```python
  from fastmcp.utilities.openapi import format_description_with_responses

  def enrich(route, component):  # provider calls this as mcp_component_fn(route, component)
      component.description = format_description_with_responses(
          component.description or "", route.responses, route.parameters, route.request_body,
      )

  mcp = FastMCP.from_openapi(spec, client=client, mcp_component_fn=enrich)
  ```
- **Prometheus dependents** → add a `Middleware` (same seam as `TimingMiddleware`) that records to a `prometheus_client` registry, and expose `/metrics` yourself:
  ```python
  import time
  from prometheus_client import Counter, Histogram
  from fastmcp.server.middleware import Middleware, MiddlewareContext

  CALLS = Counter("mcp_tool_calls_total", "tool calls", ["tool", "status"])
  LAT = Histogram("mcp_tool_seconds", "tool call latency", ["tool"])

  class PrometheusMiddleware(Middleware):
      async def on_call_tool(self, context: MiddlewareContext, call_next):
          tool = getattr(context.message, "name", "unknown")
          start = time.perf_counter()
          try:
              result = await call_next(context)
              CALLS.labels(tool, "ok").inc()
              return result
          except Exception:
              CALLS.labels(tool, "error").inc()
              raise
          finally:
              LAT.labels(tool).observe(time.perf_counter() - start)

  mcp.add_middleware(PrometheusMiddleware())
  ```

**Gating checkpoints (all in our control — no external PR):** (P1→P2) wrapper refactored to upstream-only **and** migration guide published with glue recipes; (P2→P3) deprecation announced and linked from README; (P3→P4) no unresolved critical migration blockers reported by customers. The `contrib/` give-backs and Swagger 2.0 are not gates.

**The deprecation signal (Phase 2), pseudocoded:** the server keeps working but emits a warning at startup and points at the migration guide.
```python
# awslabs/openapi_mcp_server/server.py — main(), Phase 2
def main():
    warnings.warn(
        "awslabs.openapi-mcp-server is deprecated and will reach EOL after the "
        "maintenance window. Migrate to FastMCP.from_openapi — see MIGRATION.md.",
        DeprecationWarning, stacklevel=2,
    )
    logger.warning("DEPRECATED: migrate to FastMCP.from_openapi — see MIGRATION.md")
    # ... existing startup unchanged (Phase 2 = no behavior change) ...

# Phase 4 (final release / EOL): main() hard-exits instead of starting
#   print("awslabs.openapi-mcp-server has reached EOL. See MIGRATION.md."); sys.exit(1)
```
Docs/packaging changes accompany it: README banner, PyPI classifier `Development Status :: 7 - Inactive` at Phase 4, and a top-level `MIGRATION.md` carrying the recipes above.

---

## Appendix F — First-Time-Contributor PR Data (`PrefectHQ/fastmcp`)

**Why this matters:** deprecation does **not** depend on these PRs — they're optional community give-backs (Appendix D). But if we pursue them, `scottschreckengaust` would be a **first-time contributor**, so the acceptance odds and merge latency below set expectations (and argue for sequencing the small enrichment PR first).

**Method:** pulled all 2,502 PRs via the GitHub API (`repos/PrefectHQ/fastmcp/pulls?state=all`) on 2026-07-10. "First-time contributor PR" = each distinct author's **earliest** PR by creation time (n=394). Rejection rate = closed-unmerged ÷ decided (merged + closed-unmerged; open PRs excluded). Latency = merged_at − created_at, over merged PRs only.

| Cohort | n | Merged | Closed-unmerged | **Rejection rate** | **Merge latency (median)** | p90 latency |
|---|---|---|---|---|---|---|
| All PRs (baseline) | 2,502 | 2,067 | 406 | **16.4%** | 0.7 h (82% <24 h) | 70 h |
| **First-time-contributor PRs** | 394 | 228 | 161 | **41.4%** | **16.3 h (~0.7 d)** | 206 h (~8.6 d) |
| External newcomers (`assoc=NONE`)† | 149 | 12 | 132 | 91.7% | 123 h (~5.1 d) | 301 h |

**Headline:** a first-time contributor's PR is rejected **~41%** of the time (vs. 16% overall), and when merged, the median wait is **~16 hours** but the tail is long (**p90 ≈ 8.6 days**).

**Caveats (read before citing):**
- †The 91.7% "external newcomer" row is **confounded and should not be used as the headline**: `author_association=NONE` is evaluated as-of-now, which definitionally means the author has nothing merged — so a high rejection rate is partly circular. The honest metric is the **41.4% first-PR** figure.
- `author_association` is a point-in-time snapshot, not the value at PR creation.
- Rejection ≠ "bad PR": FastMCP auto-closes PRs lacking a linked issue, LLM-verbose submissions, and superseded/duplicate PRs, inflating the closed-unmerged count. This is **exactly why Appendix D's issue-first + human-toned + small-scope discipline matters** — following process moves us out of the 41% baseline.
- Snapshot date 2026-07-10; figures drift.

**Implication for the give-backs:** these PRs do **not** gate deprecation (the migration-guide recipes cover users today). But if pursued, budget for a long tail — **up to ~2 weeks per PR** to a merge decision (p90), not the 16 h median — and treat a first-submission rejection as a likely, recoverable event (resubmit after addressing feedback). Sequence the small enrichment PR first to establish the contributor before the larger two (SSRF + Prometheus).

---

## Appendix G — Background: Our Server & the FOSS Landscape

### What our server is
A thin curation layer over FastMCP. It constructs a `FastMCP(providers=[OpenAPIProvider(...)])` and adds: Basic/Bearer/API-Key/**Cognito** auth, tag include/exclude filtering, enriched tool descriptions, dynamic prompt generation, **multi-spec composition**, **SSRF protection**, and optional **Prometheus metrics**. Transport is **stdio only** in v1.1.0 (`server.py:739`) — earlier SSE references are stale.

### The FOSS landscape (verified, 3-vote adversarial fact-check)

This survey seeded the original "what OSS alternatives exist" question. **The conclusion is FastMCP** — the engine we already wrap — which covers both in-process and standalone use (via `fastmcp run`); no third-party reimplementation is needed. The rest is retained as license/maturity due-diligence, not as recommendations.

| Project | License | Type | Notes |
|---|---|---|---|
| **FastMCP** (`PrefectHQ/fastmcp`) | **Apache-2.0** ✅ | Runtime lib (the engine we wrap) | **The recommendation.** Same license, same core, 26.1k★, active; standalone via `fastmcp run` |
| ivo-toby/mcp-openapi-server | MIT ✅ | Standalone TS server | Surveyed; not recommended (TypeScript/Node — different ecosystem, solo-maintained; FastMCP covers this) |
| harsha-iiiv/openapi-mcp-generator | MIT ✅ | Code generator (scaffolds Node project) | Surveyed; Node/TS |
| higress-group/openapi-to-mcpserver | Apache-2.0 ✅ | Go config-gen | Couples to Higress gateway — not standalone |
| matthewhand/mcp-openapi-proxy | MIT ✅ | Python server | Solo/low-maturity (~150★) |
| Speakeasy | **Elastic License 2.0** ❌ | SDK+MCP generator | **Disqualified** — source-available, not permissive |
| mcpjungle | **MPL-2.0** ❌ | MCP gateway/registry | **Disqualified** — weak-copyleft _and_ not an OpenAPI generator |
| janwilmake / snaggle-ai `openapi-mcp-server` | MIT ✅ | Spec-exploration tools | Not per-operation proxies — wrong category |
