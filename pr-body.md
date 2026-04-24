Add multi-region, multi-log-group CloudWatch Logs Insights batch query tool.

Features:
- Automatic log group chunking (max 50 per StartQuery call)
- Parallel multi-region execution with per-region concurrency control (7 max)
- Rate-limited StartQuery calls (0.7s pacing per region)
- Adaptive time-range splitting on 10k record limit or timeout (max 4 levels)
- Non-retryable error fast-fail (AccessDenied, InvalidParameter, ResourceNotFound)
- Cross-account query support via log group ARNs
- Result annotation with _region, _account, _logGroups metadata
- 20 unit tests with comprehensive coverage

<!-- markdownlint-disable MD041 MD043 -->

## Summary

### Changes

Adds a new `execute_cwl_insights_batch` tool to the CloudWatch MCP server that enables running a single Logs Insights query across multiple regions and log groups in one call. The tool handles the complexity of CloudWatch's per-region, 50-log-group-per-query limits by automatically chunking log groups, executing queries in parallel across regions, and merging results.

Key implementation details:
- `cwl_insights_batch.py` (647 lines): Core batch query engine with chunking, parallel execution, adaptive time-range splitting, and result merging
- `test_cwl_insights_batch.py` (557 lines): 20 unit tests covering chunking, rate limiting, error handling, cross-account queries, and adaptive splitting
- `tools.py`: Registers the new tool in the CloudWatch Logs tool registry
- `README.md`: Documents the tool with usage examples

### User experience

**Before:** Users had to manually issue separate `execute_logs_insight_query` calls for each region and manage log group batching themselves when querying across multiple regions or more than 50 log groups.

**After:** Users call `execute_cwl_insights_batch` with a list of regions and log group patterns. The tool automatically chunks log groups, runs queries in parallel across regions with rate limiting, handles the 10k record limit via adaptive time-range splitting, and returns merged results annotated with `_region`, `_account`, and `_logGroups` metadata.

## Checklist

* [x] I have reviewed the [contributing guidelines](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md)
* [x] I have performed a self-review of this change
* [x] Changes have been tested
* [x] Changes are documented

Is this a breaking change? N

## Acknowledgment

By submitting this pull request, I confirm that you can use, modify, copy, and redistribute this contribution, under the terms of the [project license](https://github.com/awslabs/mcp/blob/main/LICENSE).
