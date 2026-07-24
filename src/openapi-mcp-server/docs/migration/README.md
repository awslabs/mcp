# Migration & Deprecation Reference

This directory collects the analysis and upstream-contribution drafts behind the
proposal to deprecate `awslabs.openapi-mcp-server` in favor of the upstream
Apache-2.0 **FastMCP** (`PrefectHQ/fastmcp`) that this package already wraps.

Tracking issue: **awslabs/mcp#4122** ("RFC: Deprecate OpenAPI MCP Server").

## Contents

| File | Purpose |
|---|---|
| [`deprecation-evaluation.md`](./deprecation-evaluation.md) | Full evaluation: capability mapping, pros/cons, deprecation timeline, migration recipes, and first-time-contributor data. |
| [`upstream-issue-1-enrichment-dx.md`](./upstream-issue-1-enrichment-dx.md) | Draft upstream enhancement — wire FastMCP's shipped `format_description_with_responses` into the OpenAPI provider (developer-experience). |
| [`upstream-issue-2-ssrf-spec-fetch.md`](./upstream-issue-2-ssrf-spec-fetch.md) | Draft upstream `contrib/` enhancement — SSRF-safe OpenAPI spec fetching that reuses the shipped `ssrf_safe_fetch`. |
| [`upstream-issue-3-prometheus-metrics.md`](./upstream-issue-3-prometheus-metrics.md) | Draft upstream `contrib/` enhancement — a Prometheus metrics middleware on the existing `Middleware` seam. |

## Migration summary

Every feature of this wrapper is reachable today with FastMCP primitives:

| Wrapper feature | FastMCP equivalent |
|---|---|
| Server construction | `FastMCP.from_openapi(spec, client=...)` |
| Cognito auth | `fastmcp.server.auth.providers.aws.AWSCognitoProvider` |
| Tag filtering | `RouteMap(tags=...)` / `server.enable/disable(tags=...)` |
| Description enrichment | `mcp_component_fn` + `format_description_with_responses` |
| Multi-spec composition | `server.add_provider(...)` / `mount` / `import_server` |
| SSRF-safe spec fetch | `fastmcp.server.auth.ssrf.ssrf_safe_fetch` (raise `max_size`) |
| Prometheus metrics | custom `Middleware` on the `TimingMiddleware` seam |

The three upstream drafts above make the last three cases first-class for the
wider community; none of them gate this package's deprecation, since users get
the capability today via the recipes in `deprecation-evaluation.md`.
