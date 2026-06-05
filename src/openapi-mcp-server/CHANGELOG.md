# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
