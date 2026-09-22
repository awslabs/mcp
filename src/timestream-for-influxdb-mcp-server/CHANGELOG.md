# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Security

- Gate all mutating tools (create/update/delete DB clusters and instances,
  tag/untag, create parameter group, and data-plane writes `InfluxDBWritePoints`,
  `InfluxDBWriteLP`, `InfluxDBCreateBucket`, `InfluxDBCreateOrg`) behind an
  operator-controlled `ALLOW_WRITE` environment variable evaluated at startup.
  Previously, write authorization was a caller-supplied `tool_write_mode` tool
  parameter, allowing a caller (or prompt-injected agent) to self-authorize
  destructive operations (MCP Threat #8 "Tool Overreach" / SBP-02).

### Changed

- **BREAKING:** Removed the `tool_write_mode` parameter from all tools. Writes
  are now enabled by setting `ALLOW_WRITE=true` when starting the server instead
  of passing `tool_write_mode=True` per call. Read-only remains the default.

### Added

- Initial project setup
