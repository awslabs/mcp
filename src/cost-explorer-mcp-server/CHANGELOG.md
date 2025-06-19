# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2025-06-16

### Added
- Enhanced documentation for UsageQuantity metric with specific filtering requirements
- Dynamic labeling for cost metrics based on grouping dimension (e.g., "Region Total" vs "Service Total")
- Metadata support for usage metrics including grouped_by, metric type, and period information
- Optimized JSON serialization that only runs stringify_keys when needed
- Added Match_Option Validation

### Changed
- Usage metrics now return clean nested structure instead of complex pandas tuples
  - Old: `{("2025-01-01", "Amount"): {"EC2": 100}, ("2025-01-01", "Unit"): {"EC2": "Hours"}}`
  - New: `{"GroupedUsage": {"2025-01-01": {"EC2": {"amount": 100, "unit": "Hours"}}}}`
- Improved UsageQuantity documentation to emphasize need for SERVICE + USAGE_TYPE filtering
- Enhanced error handling for metric data processing

## [0.1.0] - 2025-06-01

### Added
- Initial release of the Cost Explorer MCP Server
