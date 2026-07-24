# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-06-18

### Changed

- **Breaking:** the realtime `AgentRealtimeStatus.agent_username` field is renamed to
  `agent_arn`. `GetCurrentUserData` returns only the user `Id` and `Arn` (not a login
  name), so the field now reflects what is actually populated and is described as the
  agent (user) ARN.

### Fixed

- The MCP server instructions incorrectly stated that `get_historical_metric_data`
  covers "the last 35 days". The text now reads **90 days**, matching the actual
  `MAX_LOOKBACK_DAYS` limit and the 0.2.0 behavior.

## [0.2.0] - 2026-06-08

### Changed

- `get_historical_metric_data` now supports the full **90-day** GetMetricDataV2
  retention window (previously capped at 35 days).
- Requested ranges wider than 24 hours are automatically split into consecutive
  24-hour intervals (the API's per-request limit) and fetched in sequence, so a
  single tool call can cover up to 90 days.

### Added

- Per-interval result rows: each `HistoricalMetricResult` now carries
  `interval_start`/`interval_end`, and the response includes `interval_count`.
  Average and rate metrics are reported per interval and are not aggregated
  across intervals, keeping values accurate.

## [0.1.1] - 2026-06-08

### Fixed

- Realtime and historical metric tools no longer raise `OperationNotPageableError`.
  The Amazon Connect metric APIs (`GetMetricDataV2`, `GetCurrentMetricData`,
  `GetCurrentUserData`) are not registered with boto3 paginators, so the tools now
  drive `NextToken` pagination manually via a shared helper.
- `get_historical_metric_data` no longer sends an invalid CHANNEL-only filter.
  When no queue/agent/routing-profile filter is supplied, it now defaults the report
  to the instance's queues (up to 100), satisfying the GetMetricDataV2 requirement
  for at least one non-CHANNEL filter key.

## [0.1.0] - 2026-06-08

### Added

- Initial release of the Amazon Connect MCP Server.
- Discovery tools: `list_connect_instances`, `list_queues`, `list_agents`, `list_routing_profiles`.
- Realtime reporting tools: `get_current_metric_data`, `get_current_agent_status`.
- Historical reporting tool: `get_historical_metric_data` (GetMetricDataV2) with
  support for queue, channel, agent, and routing-profile groupings and service-level
  thresholds.
