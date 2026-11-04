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
