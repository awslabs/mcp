# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2025-06-20

### Added
- **NEW AWS Cost Comparison Feature Integration**
- `get_cost_and_usage_comparisons` - Leverage AWS Cost Explorer's new Cost Comparison feature to compare costs between two time periods
- `get_cost_comparison_drivers` - Automatically analyze the top 10 most significant cost change drivers using AWS's new API
- Reduces manual cost analysis time from hours to seconds using AWS's built-in intelligence
- Provides detailed breakdowns of cost drivers, including usage and discount changes
**Cost Forecasting Capabilities**
- `get_cost_forecast` - Generate cost forecasts based on historical usage patterns with confidence intervals (80% or 95%)
- Support for daily and monthly forecast granularity for budget planning
**Modular Architecture**
- Refactored codebase into modular handler architecture for better maintainability
- Separate handlers for cost usage, comparison, forecasting, metadata, and utility functions
**Enhanced Testing**
- Comprehensive test coverage for comparison features
- Fixed duplicate test method definitions
- Improved test reliability and error handling

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
