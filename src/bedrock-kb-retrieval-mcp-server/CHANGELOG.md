# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-05-26

### Removed

- **BREAKING CHANGE:** Server Sent Events (SSE) support has been removed in accordance with the Model Context Protocol specification's [backwards compatibility guidelines](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility)
- This change prepares for future support of [Streamable HTTP](https://modelcontextprotocol.io/specification/draft/basic/transports#streamable-http) transport

## Unreleased

### Added

- Initial project setup
- Document `metadata` is now included in `QueryKnowledgeBases` results
- Optional `metadata_filter` parameter on `QueryKnowledgeBases` for metadata-based filtering using the Bedrock RetrievalFilter schema; composed with `data_source_ids` via `andAll` when both are provided (merged into an existing top-level `andAll` to respect the Retrieve API's one-level filter embedding limit)
