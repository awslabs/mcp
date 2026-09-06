<!--
  DRAFT — NOT POSTED. Local review copy: proposed PrefectHQ/fastmcp "Enhancement Request" issue.
  File via the Enhancement Request template (blank issues disabled). ONE required field "Enhancement" — paste the body.
  Auto-labels: enhancement, pending. Do NOT self-assign labels/milestones. Do NOT request the `security` label (it's for vuln fixes, not features).
  Validated against both triage-bot simulations (label bot: pass, no too-long; investigation bot: claims confirmed vs. FastMCP 3.4.4 source).
  Title (template title field): Contrib helper to fetch an OpenAPI spec by URL safely for from_openapi
-->

### Problem

`FastMCP.from_openapi(openapi_spec, client=None, ...)` takes an already-parsed `dict` — it never fetches a spec by URL (`fastmcp/server/server.py:2330`). So when a spec lives at a URL, the caller has to fetch it themselves, typically with a plain `httpx.get(url).json()`.

That naive fetch is an SSRF sink. In a lot of real deployments the spec URL is operator- or tenant-supplied config, not a hardcoded constant. If someone points it at `http://169.254.169.254/...` or an internal-only host, or the "public" spec URL 302-redirects inward, the plain fetch happily reaches it and hands the result to `from_openapi`. There's no supported path today to fetch a spec URL with the same care FastMCP already applies elsewhere.

FastMCP has already solved exactly this fetch problem for auth — `ssrf_safe_fetch` (`fastmcp/server/auth/ssrf.py:242`) does HTTPS-only, DNS resolution + IP validation (blocks private/loopback/link-local/metadata), DNS pinning against rebinding, disabled redirects, and a response size cap. The gap is purely that there's no supported way to reuse those primitives to produce the parsed dict `from_openapi` expects.

### Concrete scenario

```python
import httpx
from fastmcp import FastMCP

spec_url = os.environ["PARTNER_OPENAPI_URL"]  # operator-supplied
spec = httpx.get(spec_url).json()             # SSRF: no scheme/IP/redirect checks
mcp = FastMCP.from_openapi(spec, client=httpx.AsyncClient(base_url=...))
```

- Expected: a supported, safe way to turn a spec URL into the dict `from_openapi` needs.
- Actual: everyone hand-rolls the fetch, and the safe building block is scoped to auth.

### Where this belongs

Belongs in `fastmcp/contrib/` (community-maintained), since spec fetching is deliberately the caller's job and `from_openapi`'s dict-in contract should stay unchanged.

The SSRF protection already exists, so this is reuse/expose, not new protection — with two constraints worth surfacing up front: `ssrf_safe_fetch` defaults `max_size=5120` (5KB, `ssrf.py:246`) and rejects anything larger with `SSRFFetchError` (`ssrf.py:365,379`), which fails on any real OpenAPI spec, so the limit must be raised; and it is HTTPS-only (`ssrf.py:211-212`). Also, `ssrf.py` lives under `server/auth/` and isn't a documented public API, so reusing it from contrib couples to an internal module — maintainers may prefer to factor these primitives into a shared/public location first.

I'm happy to draft the contrib module + tests + docs if this direction sounds reasonable.
