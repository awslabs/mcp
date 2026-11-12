# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- `REDSHIFT_CONNECTION_MODE=direct` runs statements over a direct connection to a provisioned cluster, for credentials that may fetch cluster credentials but not call the Data API. The driver it needs is the optional `direct` extra (`pip install 'awslabs-redshift-mcp-server[direct]'`)
- Initial project setup
