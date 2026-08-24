# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased
### Added
- Added AWS Billing credits support via a `credits` tool (`GetCredits`, `GetCreditAllocationHistory`) covering credit balance, expiration, product applicability, sharing configuration, and the per-service allocation ledger
- Added AWS Compute Optimizer Automation support via a `compute-optimizer-automation` tool (`GetAutomationEvent`, `GetAutomationRule`, `GetEnrollmentConfiguration`, `ListAccounts`, `ListAutomationEvents`, `ListAutomationEventSteps`, `ListAutomationEventSummaries`, `ListAutomationRules`, `ListRecommendedActions`, `ListRecommendedActionSummaries`, `ListAutomationRulePreview`, `ListAutomationRulePreviewSummaries`, `ListTagsForResource`)
- Extending support for Billing and Cost Management Pricing Calculator's Workload estimate (`CreateWorkloadEstimate`, `BatchCreateWorkloadEstimateUsage`).
- Added AWS Billing Conductor tools to analize billing groups, account associations, billing group cost reports, pricing rules/plans, and custom line items
- Added AWS Billing tools for managing and querying billing views
- Added optional `billing_view_arn` parameter to 7 Cost Explorer operations to scope queries to specific billing views (PRIMARY, BILLING_GROUP, CUSTOM, BILLING_TRANSFER, BILLING_TRANSFER_SHOWBACK)
- Added local time-filter validation to the AWS Invoicing `list_invoice_summaries` operation so requests the service cannot satisfy are refused before the round trip: ranges longer than one month, reversed or empty ranges, and a missing time filter on the account selector. An over-long range returns `suggested_date_ranges`, the per-month sub-ranges that together cover the request, expressed as dates rather than billing periods to preserve issued-date semantics. The span limit follows the number of days in the start date's month (28 from a February start, 31 from a January one) rather than a flat 31 days.

### Changed
- Clarified the AWS Invoicing `list_invoice_summaries` time-filter documentation to match service behavior: the one-month maximum on `start_date`/`end_date` ranges (and that calendar alignment is not required), that a date-only bound is 00:00:00 UTC so a full June is `2026-06-01` to `2026-07-01`, that a time filter is mandatory for the account selector but optional for `invoice_id`, and that `billing_period` and `start_date`/`end_date` are not interchangeable because they filter on billing month and issued date respectively.
- Added read-only budget actions and notifications support to the `budget` tool: `budget-actions` and `budget-notifications`. Each routes by `budget_name` — a single-budget read (`DescribeBudgetActionsForBudget` / `DescribeNotificationsForBudget`) when a name is given, or an account-wide audit (`DescribeBudgetActionsForAccount` / `DescribeBudgetNotificationsForAccount`) when omitted. Both support pagination (`max_results`, `next_token`, `max_pages`) and offload large responses to session SQL
- Added AWS Savings Plans support via three tools. `sp-explorer` (`DescribeSavingsPlans`, `DescribeSavingsPlanRates`, `DescribeSavingsPlansOfferings`, `DescribeSavingsPlansOfferingRates`) describes the plans an account owns, including the queued, returned, and payment-failed plans Cost Explorer does not report, along with the rates on owned plans and the offerings available to purchase. `sp-recommendation` (`GetSavingsPlansPurchaseRecommendation`, `GetSavingsPlanPurchaseRecommendationDetails`, `StartSavingsPlansPurchaseRecommendationGeneration`, `ListSavingsPlansPurchaseRecommendationGeneration`) returns the recommended commitment, the hourly data-points behind it, an on-demand refresh, and the generation history; `GetSavingsPlansPurchaseRecommendation` pages over the details nested inside its response and merges them, reporting completeness through `pagination`. `sp-purchase-analyzer` (`StartCommitmentPurchaseAnalysis`, `GetCommitmentPurchaseAnalysis`, `ListCommitmentPurchaseAnalyses`) runs Purchase Analyzer what-if analyses for maximum savings, a specific commitment, or a target average coverage
- Added an optional `context` parameter to the Cost Explorer `get_dimension_values` operation, so `SAVINGS_PLANS` returns values scoped to the plans an account owns rather than to its usage

### Fixed
- Corrected AWS Compute Optimizer recommendation response field names so EC2, Auto Scaling group, Lambda, and RDS tools return actual values instead of null. Fixed the shared savings-opportunity parser (`savingsOpportunityPercentage`), projected utilization metrics, EC2/RDS idle flags, nested ASG instance types, and the RDS instance/storage recommendation schema.
- Corrected AWS Compute Optimizer ECS and Lambda recommendation response field names that read non-existent SDK fields and returned null. ECS now reads `currentPerformanceRisk`, `autoScalingConfiguration`, and `projectedUtilizationMetrics` (previously the non-existent `currentPerformance`, `autoScalingGroupArn`, and `projectedPerformance`), and Lambda derives the function name from the ARN (there is no `functionName` field).

## [0.0.4] - 2025-10-27
### Added
- Initial support for Billing and Cost Management Pricing Calculator's Workload estimate (`GetPreferences`, `GetWorkloadEstimate`, `ListWorkloadEstimates`, and `ListWorkloadEstimateUsage`) (#1486).

## [0.0.1] - 2025-08-22
- Initial project setup.
