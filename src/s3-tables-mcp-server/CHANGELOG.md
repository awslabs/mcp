# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Changed

- **Breaking:** `query_database`, `import_csv_to_table`, `import_parquet_to_table` and `append_rows_to_table` no longer accept `uri`, `rest_signing_name` or `rest_sigv4_enabled`. The catalog endpoint and signing settings are resolved from `region` through the same boto3 path as the server's other S3 Tables calls, so `AWS_USE_FIPS_ENDPOINT`, `AWS_USE_DUALSTACK_ENDPOINT`, `AWS_ENDPOINT_URL_S3TABLES` and their profile equivalents apply consistently. MCP clients that still send these fields continue to validate, and the fields are ignored. Direct Python callers must remove the keyword arguments.

### Added

- Initial project setup, including core S3 Tables MCP server functionality, project structure, and essential dependencies.
