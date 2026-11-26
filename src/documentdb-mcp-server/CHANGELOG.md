# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Changed

- **BREAKING**: The target DocumentDB cluster is now configured by the operator at
  server startup via the `--connection-string` CLI argument or the
  `DOCUMENTDB_CONNECTION_STRING` environment variable, instead of being supplied as
  a tool argument. Tools (`find`, `aggregate`, `insert`, `update`, `delete`,
  `listDatabases`, `listCollections`, `createCollection`, `dropCollection`,
  `countDocuments`, `getDatabaseStats`, `getCollectionStats`, `analyzeSchema`,
  `explainOperation`) no longer accept a `connection_id` argument and operate on the
  configured cluster directly.
- Hardened connection handling.
- **BREAKING**: `find` and `aggregate` now require `limit` between 1 and 1000
  (default 10). `limit=0` no longer means "no limit". `aggregate` always appends a
  final `$limit`, so a `$limit` stage in the caller's pipeline cannot raise the
  cap (pipelines that end in `$out` or `$merge` are unchanged). `analyzeSchema`
  `sample_size` must also be between 1 and 1000.
- In read-only mode, `explainOperation` rejects aggregation pipelines that contain
  `$out` or `$merge`, and explains aggregation pipelines with `queryPlanner` only.
  The response now includes the `verbosity` used.
- Server logs are written to stderr instead of stdout, so they no longer mix with
  the stdio protocol stream. `analyzeSchema` no longer logs sampled documents.
- Connection and configuration errors return a fixed message instead of the
  driver's error text, which named the cluster endpoint and topology. Query
  errors return only the server's error message and code. Deliberate errors (such
  as read-only denials) are returned to the client as tool errors.
- The connection string is parsed at startup, and the server exits with a
  redacted message if it is invalid. `retryWrites=false` is also checked when the
  connection is created.

### Removed

- **BREAKING**: Removed the `connect` and `disconnect` tools and the
  `connection_id`-based connection pool. The connection is established from the
  operator-configured connection string.
- **BREAKING**: Removed the `--connection-timeout` CLI argument (previously used
  to configure idle-connection eviction, which no longer applies with a single
  operator-configured connection). Operators passing this flag must remove it,
  as it will now cause a startup error.

## Initial release

### Added

- Initial project setup
