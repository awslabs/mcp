# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- Server crash on Windows due to `asyncio.loop.add_signal_handler` being unsupported on the default `ProactorEventLoop` (#2752). Removed the redundant signal handler from `server_lifespan` — cleanup is already handled by the context manager's `finally` block on every graceful shutdown path (stdin EOF, SIGINT via default `KeyboardInterrupt`, HTTP shutdown via uvicorn's own signal handling).

### Added

- Initial project setup
- Browser automation tools — 25 tools for cloud-based web interaction across 5 categories (session, navigation, observation, interaction, management)
- Service opt-in/opt-out via `AGENTCORE_ENABLE_TOOLS` and `AGENTCORE_DISABLE_TOOLS` environment variables
- Server instructions for MCP clients with browser usage tips
