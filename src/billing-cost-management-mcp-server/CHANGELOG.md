# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased
### Added
- Extending support for Billing and Cost Management Pricing Calculator's Workload estimate (`CreateWorkloadEstimate`, `BatchCreateWorkloadEstimateUsage`).
- Added AWS Billing Conductor tools to analize billing groups, account associations, billing group cost reports, pricing rules/plans, and custom line items
- Added AWS Billing tools for managing and querying billing views
- Added optional `billing_view_arn` parameter to 7 Cost Explorer operations to scope queries to specific billing views (PRIMARY, BILLING_GROUP, CUSTOM, BILLING_TRANSFER, BILLING_TRANSFER_SHOWBACK)

## [0.0.4] - 2025-10-27
### Added
- Initial support for Billing and Cost Management Pricing Calculator's Workload estimate (`GetPreferences`, `GetWorkloadEstimate`, `ListWorkloadEstimates`, and `ListWorkloadEstimateUsage`) (#1486).

## [0.0.1] - 2025-08-22
- Initial project setup.
