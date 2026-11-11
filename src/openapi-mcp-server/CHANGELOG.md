# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- **Fixed SSRF/LFI via external `$ref` resolution in OpenAPI specs** ([CWE-918](https://cwe.mitre.org/data/definitions/918.html) / [CWE-610](https://cwe.mitre.org/data/definitions/610.html)): the DNS-pinned fetch only guarded the root spec document; the parsed spec was then handed to `prance` for `$ref` resolution with its default settings, whose resolver (and validation backend) dereferenced `$ref` targets using its own fetcher — bypassing the SSRF validation, DNS pinning, redirect rejection, and size cap applied to the root fetch. A spec served from a validation-passing host could therefore embed a static `$ref` to an internal/metadata endpoint (`http://169.254.169.254/...`, SSRF) or a local file (`file:///proc/self/environ`, LFI) and have the resolved content returned to the caller (non-blind exfiltration). External references are now refused before parsing at both the URL and file-path load paths, and `prance` is constrained to internal (`#/...`) references only, so `$ref` resolution triggers no outbound network or filesystem access. Reported via the AWS Vulnerability Disclosure Program.
- **Fixed DNS-rebinding TOCTOU SSRF in spec fetching** ([CWE-350](https://cwe.mitre.org/data/definitions/350.html) / [CWE-367](https://cwe.mitre.org/data/definitions/367.html)): `spec_url` was validated via DNS resolution and then re-fetched via a second, independent resolution, allowing a rebinding host to pass validation with a public IP and be fetched from an internal/metadata IP. Spec URLs are now fetched by connecting only to the IP(s) that passed validation (DNS resolved once; `Host`/SNI preserved), redirects are refused, and response bodies are capped at 10 MiB. The primary spec URL is now validated too (previously unchecked).

### Changed
- Spec URL loading is DNS-pinned end to end; the previous README note about deploying behind an egress proxy for "full DNS pinning" no longer applies.
- **BREAKING (edge case)**: OpenAPI specs containing external `$ref`s — remote `http(s)://`/`file://` references, or relative multi-file references like `schemas.yaml#/Pet` — are now refused. Specs using only internal (`#/components/...`) references are unaffected. Bundle multi-file specs into a single document before loading.
- Collapsed the pluggable authentication framework (~1,000 lines across `auth/base_auth.py`, `auth/auth_cache.py`, `auth/auth_protocol.py`) into a single small factory in `auth/auth_provider.py`. The public entry points (`get_auth_provider`, `is_auth_type_available`, `register_provider_by_type`) and all five auth types — `none`, `basic`, `bearer`, `api_key`, and `cognito` — are unchanged.

### Removed
- **Metrics, response-cache, and HTTP-retry subsystems.** The in-memory/Prometheus metrics provider, the response cache, and the `tenacity`-based retry layer added configuration surface and dependencies without meaningful value for an OpenAPI→MCP stdio wrapper (the server runs over stdio, not an HTTP server). FastMCP and `httpx` cover the needs directly. Deleted modules: `utils/metrics_provider.py`, `utils/cache_provider.py`, and the already-dead `utils/error_handler.py`.
- **Direct dependencies no longer required:** `uvicorn`, `tenacity`, `prometheus-client`, `bcrypt`, and `cachetools`. The server never started an ASGI/uvicorn HTTP server (stdio transport only).
- **The `prometheus` optional-dependency extra.** `pip install "awslabs.openapi-mcp-server[prometheus]"` no longer resolves — the metrics subsystem it supported is gone.
- **Environment variables that configured the removed subsystems** are no longer read: `ENABLE_PROMETHEUS` and `PROMETHEUS_PORT` (and `METRICS_MAX_HISTORY`) for metrics, `USE_CACHETOOLS`/`CACHE_MAXSIZE`/`CACHE_TTL` for caching, and `USE_TENACITY` for retry.
- **Environment variables that never took effect** and have been dropped from the README install snippets and docs: `ENABLE_OPERATION_PROMPTS` (read into a config constant that nothing consumed — operation prompts are, and remain, always generated), `SERVER_NAME`, and the `UVICORN_*` graceful-shutdown variables (never read; there was no uvicorn server to configure). **Migration:** remove any of the above from your MCP client configuration, and drop the `[prometheus]` extra from install commands.
- **Documentation for the removed subsystems:** `AWS_BEST_PRACTICES.md` (caching/retry) and `OBSERVABILITY.md` (metrics). The still-supported `HTTP_MAX_CONNECTIONS`/`HTTP_MAX_KEEPALIVE` connection-pool settings they documented are now in the README's Environment Variables section.

### Fixed
- The `LOG_LEVEL` environment variable shown in the README install configurations was ignored: the server always logged at `INFO` unless `--log-level` was passed. `LOG_LEVEL` now sets the default level (case-insensitive); `--log-level` still takes precedence, and an unrecognized value falls back to `INFO` with a warning.

## [1.1.0] - 2026-05-31

### Added
- SSRF protection for multi-spec composition URLs with DNS resolution and IP validation
- Per-entry authentication for additional specs (`auth_type`, `auth_token`, `auth_api_key`, `auth_username`, `auth_password`)
- `--allow-insecure-http` flag and `ALLOW_INSECURE_HTTP` env var to permit HTTP URLs (default: HTTPS only)
- `--allow-private-networks` flag and `ALLOW_PRIVATE_NETWORKS` env var to permit private/loopback/link-local IPs (default: blocked)
- `--allowed-spec-dirs` flag and `ALLOWED_SPEC_DIRS` env var to restrict `spec_path` to specific directories
- Path traversal protection for `spec_path` with file extension validation (.json, .yaml, .yml only)
- Security section in README documenting SSRF protections, credential isolation, and path traversal prevention
- SSRF protection test suite (17 new tests)
- Prompt handler message format test suite (11 new tests)

### Fixed
- **Prompt handlers incompatible with FastMCP 3.x**: Prompt handler functions returned `list[dict]` which causes `TypeError` in FastMCP 3.x's `convert_result` pipeline. Migrated to `fastmcp.Message` objects for text content and `EmbeddedResource` + `TextResourceContents` for resource-type operations. Affected both operation prompts and workflow prompts.

### Changed
- **BREAKING**: Additional specs no longer inherit primary API credentials. Each entry must declare its own auth or defaults to no auth. See Security section below.
- Bumped `fastmcp` dependency to `>=3.3.1` (includes SSRF utilities used by this fix)
- Updated `boto3>=1.43.0`, `typing-extensions>=4.15.0`
- Widened `cachetools<8` and `bcrypt<6` upper bounds for forward compatibility

### Security
- **Fixed SSRF vulnerability in multi-spec configuration** ([CWE-918](https://cwe.mitre.org/data/definitions/918.html)): `spec_url` and `base_url` fields in `additional_specs` were fetched without URL validation, allowing server-side requests to internal networks, cloud metadata endpoints (169.254.169.254), and loopback addresses. Leverages `fastmcp.server.auth.ssrf` for DNS resolution and IP validation (`ip.is_global`). See the Security section in README for DNS rebinding limitations.
- **Fixed credential leakage to additional spec endpoints** ([CWE-522](https://cwe.mitre.org/data/definitions/522.html)): Primary API authentication tokens, headers, and cookies were silently forwarded to all `base_url` endpoints in `additional_specs`. This is analogous to [CVE-2023-36052](https://nvd.nist.gov/vuln/detail/CVE-2023-36052) (Azure CLI credential exposure to unintended endpoints).
- **Fixed path traversal via `spec_path`** ([CWE-22](https://cwe.mitre.org/data/definitions/22.html)): `spec_path` in additional specs accepted arbitrary file paths without canonicalization or directory restriction, allowing reads of sensitive system files. This is analogous to [CVE-2024-37032](https://nvd.nist.gov/vuln/detail/CVE-2024-37032) (Ollama path traversal).

### Migration Guide
Users of `--additional-specs` who relied on the primary API's credentials being shared with additional specs must now explicitly configure per-entry authentication:

```json
[
  {
    "name": "partner-api",
    "spec_url": "https://partner.example.com/openapi.json",
    "base_url": "https://partner.example.com",
    "auth_type": "bearer",
    "auth_token": "your-partner-bearer-token"
  }
]
```

Users with `http://` spec URLs must add `--allow-insecure-http` or set `ALLOW_INSECURE_HTTP=true`.
Users with internal/private network spec URLs must add `--allow-private-networks` or set `ALLOW_PRIVATE_NETWORKS=true`.

## [0.3.0] - 2026-04-09

### Added
- Tag-based visibility filtering via `--include-tags` / `--exclude-tags` CLI args and `INCLUDE_TAGS` / `EXCLUDE_TAGS` env vars
- Enriched tool descriptions with response codes and parameter examples from OpenAPI spec
- Multi-spec composition via `--additional-specs` CLI arg or `ADDITIONAL_SPECS` env var to combine multiple APIs into one server
- `--no-validate-output` flag and `VALIDATE_OUTPUT` env var to disable response schema validation for APIs with loose specs

### Changed
- Migrated from FastMCP 2.x to 3.x using provider-based architecture
- Updated all dependencies to latest stable versions with upper bounds pinned to next major version

### Fixed
- Server crash when API spec or base URL is missing before server initialization
- Pyright type checking errors from namespace package logger re-export

### Security
- Updated dependencies with latest security patches

## [0.2.0] - 2025-07-05

### Added
- OAuth 2.0 and OpenID Connect support through Cognito authentication
- Client credentials grant flow for service-to-service authentication
- Cline Marketplace integration support

### Changed
- Migrated from FastMCP 1.0 to 2.0
- Updated core dependencies to latest versions
- Enhanced documentation structure and authentication examples

### Security
- Updated base image with latest security patches

## [0.1.0] - 2025-05-15

### Added
- Initial project setup with OpenAPI MCP Server functionality
- Support for OpenAPI specifications in JSON and YAML formats
- Dynamic generation of MCP tools from OpenAPI endpoints
- Intelligent route mapping for GET operations with query parameters
- Authentication support for Basic, Bearer Token, and API Key methods
- Command line arguments and environment variable configuration
- Support for SSE and stdio transports
- Dynamic prompt generation based on API structure
- Centralized configuration system for all server settings
- Metrics collection and monitoring capabilities
- Caching system with multiple backend options
- HTTP client with resilience features and retry logic
- Error handling and logging throughout the application
- Graceful shutdown mechanism for clean server termination
- Docker configuration with explicit API parameters
- Comprehensive test suite with high code coverage
- Detailed documentation and deployment guides
