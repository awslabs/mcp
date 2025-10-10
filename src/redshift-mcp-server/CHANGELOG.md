# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- Fixed critical transaction error handling bug where failed SQL queries would cause all subsequent queries in the same session to fail with "current transaction is aborted, commands ignored until end of transaction block". The server now properly executes `ROLLBACK` instead of `END` when a query fails within a transaction block.

### Added

- Initial project setup
