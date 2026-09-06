# OpenAPI provider drops response/parameter context that the shipped formatter already produces

## Problem

Tools generated from an OpenAPI spec get a description containing only the operation's `description`/`summary`. The spec's response status codes, parameter details, and request-body info — context that helps an LLM select and call the right tool — never reach the tool description.

FastMCP already ships a utility that produces exactly this text, `format_description_with_responses` (`fastmcp/utilities/openapi/formatters.py`, exported from `fastmcp.utilities.openapi`), but the OpenAPI provider never calls it: `_create_openapi_tool` sets the description to `route.description or route.summary or ...` and passes it straight through. It's reachable today by hand-rolling an `mcp_component_fn` that calls the formatter, but every user doing that to get the provider's own shipped output suggests it belongs closer to the default. Tool-description quality has recurred as a pain point (#1756).

## Expected vs. actual

For an operation with a `200` response and a required `petId` path parameter:

**Actual**
```
Returns a single pet.
```

**Expected** — passing `route.responses`/`parameters` through the existing formatter yields:
```
Returns a single pet.

**Path Parameters:**
- **petId** (Required): ID of pet to return

**Responses:**
- **200** (Success): successful operation
```

Scope notes: this is a minimal example — specs with response schemas produce more (Content-Type, response properties, a generated example), so enriched output can get long; default-on vs. opt-in is your call (see the over-verbose descriptions reported in #1756). Error responses (like `404`) are dropped upstream in the parser and would be a separate follow-up. No test currently asserts enriched descriptions.

Distinct from #3392 (an LLM-powered curation layer with a new dependency); this is the opposite — surfacing an existing deterministic, zero-dependency formatter. Happy to open a PR with tests if this is wanted.
