# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2024-11-08

### Added
- Initial release of AWS Carbon Footprint MCP Server
- `create_carbon_export` tool for creating carbon data exports using AWS BCM Data Exports
- `list_carbon_exports` tool for listing existing carbon exports with status
- `get_export_status` tool for checking specific export execution status
- `get_export_data` tool for retrieving data from completed exports
- `query_carbon_data` tool for querying carbon emissions with custom filters
- Support for multiple export formats (CSV, Parquet) with compression options
- Comprehensive error handling and validation
- Integration with AWS CLI bcm-data-exports commands
- Pydantic models for type safety and validation
- Comprehensive test coverage
- Detailed documentation and usage examples

### Features
- Create carbon emissions data exports with custom date ranges
- Monitor export progress and status
- Retrieve and analyze carbon footprint data
- Filter by service, region, and account
- Group results by various dimensions
- Support for both read-only and write operations
- AWS credential handling with profile support
- S3 integration for export storage and retrieval

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Initial project setup
