# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- `read_documentation` accepts a section anchor on the URL. `.../page.html#section-anchor` returns only that section, bounded at the next heading of the same or higher level. An anchor that matches nothing returns the whole page with a note, so passing one is never worse than omitting it. `read_sections` and `search_table` now ignore a fragment rather than rejecting the URL.

- Add environment variable `AWS_DOCUMENTATION_PARTITION` to select AWS documentation partition.
- Add `get_available_services` and `read_documentation` when `AWS_DOCUMENTATION_PARTITION` is set to `aws-cn`.

### Changed

- `read_sections` resolves a title against the same heading table an anchor resolves against, instead of finding and slicing sections separately, so the two ways of naming a section cannot disagree about which headings a page has or where one ends. Titles still match `h2` only. A page whose markup collapses its own headings now reports that the section could not be separated, rather than returning a header with nothing under it.

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
