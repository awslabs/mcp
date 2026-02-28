# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Optional `selector` parameter for `browser_snapshot` to scope the accessibility tree to a CSS-selected DOM subtree, reducing output verbosity on content-heavy pages
- Initial release with 24 browser automation tools
- Session lifecycle tools: start, get, stop, list browser sessions via AgentCore APIs
- Navigation tools: navigate to URL, navigate back, navigate forward
- Interaction tools: click, type, fill form, select option, hover, press key, upload file, handle dialog
- Observation tools: accessibility snapshot, screenshot, wait for element/text, console messages, network requests, JavaScript evaluation
- Management tools: tab management (list/new/select/close), page close, viewport resize
- Accessibility tree snapshot system using CDP `Accessibility.getFullAXTree` with sequential ref assignment (e1, e2, ...)
- Element ref resolution via `page.get_by_role()` locators for reliable interaction
- Uses `bedrock-agentcore` SDK for credential resolution and SigV4-signed WebSocket connections
- Cached AWS client utility with user-agent tagging (`awslabs/mcp/amazon-bedrock-agentcore-browser-mcp-server`)
- Pydantic response models for session APIs
- Dockerfile with multi-stage build and non-root user
