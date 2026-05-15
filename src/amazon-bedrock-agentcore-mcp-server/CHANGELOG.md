# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## 0.1.0 - 2026-05-14

### Added

- **Runtime primitive** — 14 tools for deploying, managing, and invoking agent runtimes and endpoints (`create_agent_runtime`, `create_agent_runtime_endpoint`, `invoke_agent_runtime`, `stop_runtime_session`, `get_runtime_guide`, and others)
- **Memory primitive** — 21 tools for memory resource management, event storage, semantic retrieval, batch operations, and extraction jobs (`memory_create`, `memory_create_event`, `memory_retrieve_records`, `memory_batch_create_records`, `get_memory_guide`, and others)
- **Identity primitive** — 21 tools for workload identity, API key providers, OAuth2 providers, token vault configuration, and resource policies. Data plane operations (token retrieval) are intentionally excluded to keep credential material out of LLM context
- **Gateway primitive** — 15 tools for managing API gateways, gateway targets (Lambda, OpenAPI, Smithy, MCP servers), and resource policies. `InvokeGateway` data plane operation is excluded for the same security reason
- **Policy primitive** — 15 tools for policy engine management, authorization policies, and policy asset generation
- **Code Interpreter primitive** — 9 tools for sandboxed code execution, package installation, and file transfer
- **Browser automation tools** — 25 tools for cloud-based web interaction across 5 categories (session, navigation, observation, interaction, management)
- **Service opt-in/opt-out** via `AGENTCORE_ENABLE_TOOLS` and `AGENTCORE_DISABLE_TOOLS` environment variables
- **Server instructions** for MCP clients with browser usage tips
- Initial project setup

### Changed

- **README** rewritten to reflect 122-tool operational coverage across 7 primitives, including per-primitive tool callouts, configuration mechanisms, cost-awareness tiers, security posture (exclusion of credential-returning data plane operations), and architecture overview

### Fixed

- **User-agent version reporting** — `MCP_SERVER_VERSION` is now derived dynamically via `importlib.metadata.version()` instead of being hardcoded. Previously every release reported `0.1.0` regardless of installed version, blocking version-distribution analysis in service-side telemetry
- Server crash on Windows due to `asyncio.loop.add_signal_handler` being unsupported on the default `ProactorEventLoop` (#2752). Removed the redundant signal handler from `server_lifespan` — cleanup is already handled by the context manager's `finally` block on every graceful shutdown path (stdin EOF, SIGINT via default `KeyboardInterrupt`, HTTP shutdown via uvicorn's own signal handling)
