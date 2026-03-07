# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-06

### Added

- Initial read-only GuardDuty MCP server scaffold
- `list_detectors`, `list_findings`, and `get_findings` tools
- Structured finding models intended for LLM triage workflows

### Fixed

- Normalize Pydantic `Field` defaults when MCP tools are invoked directly in unit tests
