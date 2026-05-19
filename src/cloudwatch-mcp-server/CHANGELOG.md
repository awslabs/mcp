# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [0.1.1] - 2026-05-12

### Removed

- Removed Observability Admin module and all associated tools, models, and tests. These APIs are now available in the [official AWS MCP server](https://aws.amazon.com/blogs/aws/the-aws-mcp-server-is-now-generally-available/).


## [0.1.0] - 2026-05-08

### Added

- Added PromQL query tools for CloudWatch OTLP metrics (`execute_promql_query`, `execute_promql_range_query`, `get_promql_label_values`, `get_promql_series`, `get_promql_labels`)
- SigV4-signed HTTP client for CloudWatch PromQL endpoint (`monitoring.{region}.amazonaws.com/api/v1/*`)
- OTLP scope-to-PromQL label mapping documentation in README and tool docstrings
- Guidance for enabling OTel enrichment of vended AWS metrics (`aws cloudwatch start-otel-enrichment`)

## [0.0.26] - 2026-04-29

### Fixed

- Made storedBytes optional in LogGroupMetadata

### Added

- Added `execute_cwl_insights_batch` tool for running Logs Insights queries across multiple log groups and regions

## [0.0.24] - 2026-04-10

### Added

- Added field index recommender tools for CloudWatch Logs

## [0.0.23] - 2026-04-02

### Added

- Added Observability Admin tools with telemetry rules and configuration support

## [0.0.22] - 2026-03-13

### Added

- Added AgentCore session investigation skill

## [0.0.19] - 2026-02-04

### Added

- Added multi-profile support for all tools

## [0.0.14] - 2025-12-11

### Fixed

- Fixed timezone datetime handling in GetMetricData

## [0.0.13] - 2025-11-07

### Added

- Added Anomaly Detection Alarm recommendation support

## [0.0.11] - 2025-10-13

### Fixed

- Return empty results on Error for CloudWatch Logs Insights Query tool

## [0.0.9] - 2025-08-19

### Added

- Added Windows installation documentation

## [0.0.8] - 2025-08-12

### Changed

- Removed autoscaling alarms by default from get_active_alarms functionality

### Fixed

- Fixed mcp install from Cursor failing due to link change

## [0.0.7] - 2025-07-24

### Fixed

- Fixed cross-region issue in analyze_log_group

## [0.0.5] - 2025-10-06

### Added

- Added tool to analyze CloudWatch Metric data

### Changed

- Updated Alarm recommendation tool to support CloudWatch Anomaly Detection Alarms

## [0.0.4] - 2025-07-11

### Changed

- Updated README instructions to correcly setup server with Q CLI

## [0.0.3] - 2025-07-02

### Added

- Added Support for CloudWatch Alarms Tools
- Added Support for CloudWatch Metrics Tools
- Added Support for CloudWatch Logs Tools

## [0.0.0] - 2025-06-19

### Added

- Initial project setup
