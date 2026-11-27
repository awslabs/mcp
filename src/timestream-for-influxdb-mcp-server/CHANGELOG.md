# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Security

- Replace the text-based read-only check on `InfluxDBQuery` with a check on the
  query's parsed AST, obtained from the InfluxDB `POST /api/v2/query/ast`
  endpoint. The previous check could be bypassed with a regular expression
  literal that contains `"` or `//`, or with string-keyed member access such as
  `experimental["to"]`, and it did not block network functions such as
  `http.post()`, `requests.get()`, or `from(host:)`. With `INFLUXDB_WRITE_MODE`
  unset, the query tool now only accepts imports from a list of read-only
  packages, rejects any reference to `to` or `wideTo`, rejects calls with a
  `host` argument, and rejects queries that InfluxDB cannot parse.
- Gate all mutating tools (create/update/delete DB clusters and instances,
  tag/untag, create parameter group, and data-plane writes `InfluxDBWritePoints`,
  `InfluxDBWriteLP`, `InfluxDBCreateBucket`, `InfluxDBCreateOrg`) behind an
  operator-controlled `ALLOW_WRITE` environment variable evaluated at startup.
  Previously, write authorization was a caller-supplied `tool_write_mode` tool
  parameter, allowing a caller (or prompt-injected agent) to self-authorize
  destructive operations (MCP Threat #8 "Tool Overreach" / SBP-02).

### Fixed

- `InfluxDBQuery` no longer fails with `KeyError: '_measurement'` on results
  that lack the `_measurement`, `_field`, `_value`, or `_time` columns, such as
  `schema.measurements()`, `v1.measurements()`, and `buckets()`. Missing
  columns are returned as `null`.

### Changed

- With `INFLUXDB_WRITE_MODE` unset, `InfluxDBQuery` rejects queries that import
  the `experimental` package, because it contains `experimental.to()`. Queries
  that need it, for example for `experimental.group()`, require
  `INFLUXDB_WRITE_MODE=true`.

- **BREAKING:** Removed the `tool_write_mode` parameter from all tools. Writes
  are now enabled by setting `ALLOW_WRITE=true` when starting the server instead
  of passing `tool_write_mode=True` per call. Read-only remains the default.

### Added

- Initial project setup
