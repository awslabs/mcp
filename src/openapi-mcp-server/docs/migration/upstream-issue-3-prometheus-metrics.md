<!--
  DRAFT — NOT POSTED. Local review copy: proposed PrefectHQ/fastmcp "Enhancement Request" issue.
  File via the Enhancement Request template (blank issues disabled). ONE required field "Enhancement" — paste the body.
  Auto-labels: enhancement, pending. Do NOT self-assign labels/milestones.
  Validated against both triage-bot simulations (label bot: pass, no too-long; investigation bot: claims confirmed vs. FastMCP 3.4.4 source after the dependency-tier correction below).
  Title (template title field): Metrics export middleware (Prometheus scrape / OTel metrics) for production observability (contrib/)
-->

## Problem

FastMCP already has OpenTelemetry *tracing*: `fastmcp/telemetry.py`, per-operation server spans wrapping every tool/resource/prompt call (`fastmcp/server/telemetry.py:57`; spans created at `fastmcp/server/server.py:673`+), available through the `mcp`/`server` extras that pull in `opentelemetry-api` (`fastmcp_slim/pyproject.toml:82`; the slim base `[project].dependencies` at lines 6-13 do not include it). So per-call latency and errors are already observable through a tracing backend.

What's missing is pull-based / aggregate **metrics**. An operator can't scrape request counts, latency histograms, or error-rate counters from a `/metrics` endpoint, nor emit them as OTel metric instruments. The only aggregate-ish path today is logging: `TimingMiddleware` / `DetailedTimingMiddleware` (`fastmcp/server/middleware/timing.py:10`, `:60`) time requests and write them to a logger, which dashboards and alerts can't consume.

## Concrete scenario

I run a FastMCP HTTP server in production. My alerting is built on Prometheus scraping `/metrics`. I want request rate, p95 latency, and per-tool error-rate counters exported the way every other service I run does it. Tracing spans exist, but my alert stack is pull-based metrics — so today I hand-roll a `Middleware` subclass around `on_request` / `on_call_tool`, add a metrics client, and maintain it myself. Every operator reinvents the same seam.

## What I'd expect vs. actual

The middleware seam already supports this: `Middleware` (`fastmcp/server/middleware/middleware.py:88`) exposes `on_request` and per-operation hooks like `on_call_tool`, registered via `mcp.add_middleware(...)` (`fastmcp/server/server.py:527`). `TimingMiddleware` already proves the pattern — it times requests in `on_request` and emits the result. Actual behavior: that result goes to a logger. The gap is purely the sink — a metrics registry instead of a logger.

I'd expect a community-maintained metrics middleware in `fastmcp/contrib/` (imported as `from fastmcp.contrib import ...`, per `fastmcp/contrib/README.md`, which allows optional deps). `contrib/` fits Prometheus/statsd because those pull a new dependency; the OTel-*metrics* case is lighter, since `opentelemetry-api` already ships via the `mcp`/`server` extras and could extend the existing telemetry module. I'm not proposing metric names or an exporter API — just flagging that the seam exists and the metrics sink is the only missing piece.
