# Migration Guide: `awslabs.openapi-mcp-server` → FastMCP

> **Status:** proposed deprecation — see tracking issue **awslabs/mcp#4122**
> ("RFC: Deprecate OpenAPI MCP Server"). This guide is the customer-facing
> migration reference; the full analysis lives in
> [`docs/migration/deprecation-evaluation.md`](./docs/migration/deprecation-evaluation.md).

## Why

`awslabs.openapi-mcp-server` is a wrapper over the upstream Apache-2.0
**FastMCP** (`PrefectHQ/fastmcp`) — the same engine it already imports and
builds on. Every capability the wrapper adds is reachable today with FastMCP's
own primitives, so the wrapper can be deprecated without loss of function.

## What maps to what

| Wrapper feature | Native FastMCP equivalent |
|---|---|
| Server construction | `FastMCP.from_openapi(spec_dict, client=httpx_client)` |
| Basic / Bearer / API-key auth (outbound, to the API) | set headers on the `httpx.AsyncClient` passed to `from_openapi` |
| Cognito auth (outbound, to the API) | acquire the token yourself (boto3 `initiate_auth`), then set `Authorization` on the `httpx.AsyncClient`. `AWSCognitoProvider` is **not** the equivalent — it protects the MCP server's own *inbound* connections, not calls out to the API. No upstream helper covers the token-acquisition/auto-refresh half. |
| Tag filtering (`--include/--exclude-tags`) | `RouteMap(tags=...)` and `server.enable/disable(tags=...)` |
| Description enrichment | `mcp_component_fn` calling `fastmcp.utilities.openapi.format_description_with_responses` |
| `HttpClientFactory` | a caller-supplied `httpx.AsyncClient` |
| Multi-spec (`--additional-specs`) | `server.add_provider(...)` / `mount` / `import_server` |
| SSRF-safe spec fetch | `fastmcp.server.auth.ssrf.ssrf_safe_fetch` (raise its 5 KB `max_size`) |
| Prometheus metrics | a `Middleware` subclass on the `TimingMiddleware` seam + `mcp.add_middleware(...)` |

## In-process users

```python
import httpx
from fastmcp import FastMCP

# Assumption: the spec is OpenAPI 3.0.x/3.1.x. Convert Swagger/OpenAPI 2.0
# to 3.x first (e.g. swagger2openapi) — from_openapi rejects 2.0.
mcp = FastMCP.from_openapi(
    httpx.get("https://api.example.com/openapi.json").json(),
    client=httpx.AsyncClient(base_url="https://api.example.com"),
)
```

To reproduce this wrapper's description enrichment, pass an `mcp_component_fn`:

```python
from fastmcp.utilities.openapi import format_description_with_responses

def enrich(route, component):
    component.description = format_description_with_responses(
        component.description or "",
        route.responses, route.parameters, route.request_body,
    )

mcp = FastMCP.from_openapi(spec, client=client, mcp_component_fn=enrich)
```

> **Resolve `$ref`s before enriching.** The example values in the generated
> `**Responses:**` section come from `generate_example_from_schema`, which has no
> `$ref` branch — an unresolved reference falls through to the literal string
> `"unknown_type"`. This wrapper never hit it because it runs specs through
> `prance`'s `ResolvingParser` first, but `httpx.get(...).json()` above hands
> `from_openapi` a raw dict with `$ref`s intact. A response of
> `{"type": "array", "items": {"$ref": "#/components/schemas/Widget"}}` then
> documents its example as `["unknown_type"]` — while the tool's own
> `output_schema` resolves the reference correctly, so the description contradicts
> the schema next to it. Dereference first:
>
> ```python
> from prance import ResolvingParser
> from prance.util.resolver import RESOLVE_INTERNAL
>
> spec = ResolvingParser(
>     spec_string=httpx.get("https://api.example.com/openapi.json").text,
>     resolve_types=RESOLVE_INTERNAL,   # internal refs only — external ones are an SSRF/LFI sink
>     backend="openapi-spec-validator",
> ).specification
> ```
>
> Only needed if you use `mcp_component_fn` for enrichment; `from_openapi`
> resolves references itself for tool input/output schemas.

## Standalone (no-code) users

Replace `uvx awslabs.openapi-mcp-server --spec-url ...` with a small entrypoint
run by FastMCP's own CLI — same Python ecosystem:

```python
# server.py
import httpx
from fastmcp import FastMCP
mcp = FastMCP.from_openapi(
    httpx.get("https://api.example.com/openapi.json").json(),  # trusted URL
    client=httpx.AsyncClient(base_url="https://api.example.com"),
)
```

```
fastmcp run server.py --transport stdio
```

`fastmcp run` auto-discovers a module-level `mcp`/`server`/`app` object.

### Untrusted (operator/tenant-supplied) spec URLs

A plain `httpx.get` on an untrusted URL is an SSRF sink. Use the shipped
SSRF-safe fetcher instead (raising its 5 KB default `max_size`):

```python
import asyncio, json, os, httpx
from fastmcp import FastMCP
from fastmcp.server.auth.ssrf import ssrf_safe_fetch  # currently an internal module

raw = asyncio.run(ssrf_safe_fetch(os.environ["OPENAPI_URL"], max_size=10_000_000))
mcp = FastMCP.from_openapi(json.loads(raw),
                           client=httpx.AsyncClient(base_url=os.environ["API_URL"]))
```

## Prometheus metrics

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
# expose /metrics yourself (e.g. prometheus_client.start_http_server)
```

## Notes & limitations

- **OpenAPI 2.0 (Swagger):** not supported by FastMCP (3.0.x/3.1.x only).
  Convert first with `swagger2openapi` or the Swagger Converter.
- **SSRF-safe fetch** and **Prometheus** currently require a few lines of glue
  (above). Draft upstream `contrib/` enhancements to make these first-class are
  in [`docs/migration/`](./docs/migration/); they are not prerequisites for
  migrating.
