# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- `read_sections` matches section titles at every heading level, not only `h2`. Search results list `sections` and `recommended_sections` from every level, including the page's `h1` title, so titles copied from them failed with "No matching sections were found" and agents fell back to `read_documentation`.
  - A title selects every heading that carries it, and each section runs to the next heading at the same or a higher level, so it includes its subsections. A title that matches only `h2` headings returns the same sections as before; where a deeper heading elsewhere on the page shares the title, that section is returned too.
  - When the titles that match name only the page's `h1`, the whole page is returned, paginated the same way as `read_documentation`'s default, so its `start_index` hint applies. A title that names the page and also a section, or that comes with titles naming sections, returns those sections with a note pointing to `read_documentation` for the whole page.
  - On a page with no `h2` headings, a miss lists the top subsections instead of reporting that there are none. Empty headings and `h6` callout titles such as "Note" are never offered, and an empty title matches nothing. Only the first `h1` is the page title, so an unescaped `# of hosts` paragraph in converted HTML is text.
  - A title passed twice, in the same or a different case, is no longer reported as not found.
- `recommend` checks its URL against the same documentation domains as the read tools and raises a tool error for anything else. Before, it sent any input to the recommendations API and returned the resulting 400 as if it were a recommendation. It also URL-encodes the page path it sends, so a `&` in the URL can no longer add parameters to the API call, and it maps `.md` page URLs to their `.html` page, which is what recommendations are indexed by.
- Recoverable read-path failures now name a next step. A 4xx, and a redirect that landed on a page with nothing to read, both add "Use search_documentation.", in the same spirit as the existing missing-subsections message. A page that returned content at the URL asked for but could not be parsed, and a transport failure, do not - the page answered, so a search is not the remedy.
- Read-path failures now reach the client with their message. Anticipated failures raise `DocumentationToolError`, a `ToolError` subclass, because MCP SDK 2.1.0 and later forward only a `ToolError`'s text and replace everything else with a bare `Error executing tool <name>`. This affected `read_documentation`, `read_sections` and `search_table`: a moved page, a 4xx response, an unreadable index shell or a rejected URL all arrived at the model with no reason and no suggested next step. Unexpected exceptions are deliberately left unconverted, so crash details stay off the wire.

### Changed

- `read_documentation` now requests `Accept: text/markdown, text/html;q=0.9`. Pages that publish a Markdown variant return it directly, which is smaller and skips the HTML-to-Markdown conversion. Pages without one, such as the CLI reference, still return HTML and are converted as before. The table-truncation pass now runs on both forms, all in a single request with no extra probe for pages that lack Markdown.
- `read_sections` negotiates Markdown the same way and extracts sections from it, converting HTML first when that is what the page serves. Pages that only serve Markdown or plain text no longer fail with "Cannot extract sections from non-HTML content". `search_table` keeps requesting HTML, because published Markdown flattens the merged-cell structure its nested output depends on.
- `read_documentation`, `read_sections`, `search_table` and the China `read_documentation` accept `.md` page URLs, with or without a `#section` fragment, and read the `.html` page at the same path. Published Markdown links its sibling pages as relative `.md` files, which are now kept as written instead of being expanded to absolute `.html` URLs. That saves about 75 characters per link, around 10% on a link-heavy page such as the SQS message quotas. Agents resolve relative links against the page URL, which the tool docstrings now state.
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
