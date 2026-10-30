# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- Recoverable read-path failures now name a next step. A 4xx, and a redirect that landed on a page with nothing to read, both add "Use search_documentation.", in the same spirit as the existing missing-subsections message. A page that returned content at the URL asked for but could not be parsed, and a transport failure, do not - the page answered, so a search is not the remedy.
- Read-path failures now reach the client with their message. Anticipated failures raise `DocumentationToolError`, a `ToolError` subclass, because MCP SDK 2.1.0 and later forward only a `ToolError`'s text and replace everything else with a bare `Error executing tool <name>`. This affected `read_documentation`, `read_sections` and `search_table`: a moved page, a 4xx response, an unreadable index shell or a rejected URL all arrived at the model with no reason and no suggested next step. Unexpected exceptions are deliberately left unconverted, so crash details stay off the wire.

### Changed

- `read_documentation` now requests `Accept: text/markdown, text/html;q=0.9`. Pages that publish a Markdown variant return it directly, which is smaller and skips the HTML-to-Markdown conversion. Pages without one, such as the CLI reference, still return HTML and are converted as before. The table-truncation pass now runs on both forms, all in a single request with no extra probe for pages that lack Markdown. Same-site links to `.md` pages are rewritten to their absolute `.html` URLs, so they can be passed straight back to the read tools.
- Raised the `mcp` floor to `>=2.1.0`. 2.1.0 is where the SDK stopped forwarding non-`ToolError` messages, so an environment that resolved 2.0.0 hid this entire class of bug, CI included. The lock now resolves 2.3.0.

### Added

- Add environment variable `AWS_DOCUMENTATION_PARTITION` to select AWS documentation partition.
- Add `get_available_services` and `read_documentation` when `AWS_DOCUMENTATION_PARTITION` is set to `aws-cn`.

### Removed

- The `recommend` tool no longer returns Highly Rated recommendations. The upstream recommendation type has been retired, so the tool now returns New, Similar, and Journey results only.

## [1.0.0] - 2025-05-26

### Removed

- **BREAKING CHANGE:** Server Sent Events (SSE) support has been removed in accordance with the Model Context Protocol specification's [backwards compatibility guidelines](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility)
- This change prepares for future support of [Streamable HTTP](https://modelcontextprotocol.io/specification/draft/basic/transports#streamable-http) transport

## [0.0.1] - 2025-04-02

First release of AWS Documentation MCP Server.

### Added

- Initial project setup
