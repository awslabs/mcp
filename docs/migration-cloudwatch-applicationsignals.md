# Migration Guide: CloudWatch Application Signals MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.cloudwatch-applicationsignals-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The CloudWatch Application Signals server registered 38 tools. Each one wrapped a small number of public AWS API calls to Application Signals, Amazon CloudWatch, Amazon CloudWatch Logs, AWS X-Ray, CloudWatch Synthetics, CloudWatch RUM, IAM, AWS Lambda, and Amazon S3, and formatted the results. Eight ServiceEvents tools also read function metrics through the CloudWatch Prometheus-compatible query API. The AWS MCP Server makes the same AWS API calls through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. An agent can combine the calls freely and use new Application Signals APIs without waiting for a server release.

Two Agent Skills in the Agent Toolkit for AWS cover the domain guidance this server's tool descriptions carried:

- [`aws-observability`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-observability) covers using CloudWatch on a service that already reports: the Application Signals service map, alarms on its metrics, Logs Insights, X-Ray and ADOT tracing (`references/cloudwatch/tracing.md`), Synthetics canaries with a common-failures table (`references/cloudwatch/synthetics.md`), troubleshooting (`references/cloudwatch/troubleshooting.md`), and Application Signals Dynamic Instrumentation (`references/cloudwatch/dynamic-instrumentation.md`, with the `scripts/cloudwatch/di_instrumentation.py` and `scripts/cloudwatch/di_snapshots.py` helpers).
- [`setting-up-cloudwatch-observability`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/specialized-skills/operations-skills/setting-up-cloudwatch-observability) covers first-time Application Signals onboarding (`references/cloudwatch/application-signals-onboarding.md`), CI/CD deployment metadata (`references/cloudwatch/application-signals-cicd-metadata.md`), and per-platform guides for Amazon EC2, Amazon ECS, Amazon EKS, and Lambda in Java, Python, Node.js, and .NET (`references/cloudwatch/appsignals-guides/`). The `aws-observability` skill routes onboarding requests here.

Neither skill covers the PromQL queries the ServiceEvents function tools made.

## Installing the Replacement

### Configuration

```json
{
  "mcpServers": {
    "aws": {
      "command": "uvx",
      "args": [
        "mcp-proxy-for-aws-cli@latest",
        "https://aws-mcp.us-east-1.api.aws/mcp",
        "--metadata",
        "AWS_REGION=us-west-2"
      ]
    }
  }
}
```

Set `AWS_REGION` to the Region where your Application Signals services run. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

### Installing the Agent Skills

```bash
npx skills add aws/agent-toolkit-for-aws/skills
```

This installs the `aws-observability` and `setting-up-cloudwatch-observability` skills along with the other skills. An agent connected to the AWS MCP Server can also load either one with the server's `retrieve_skill` tool.

### Permissions

Your identity needs the permissions the old server's README listed:

- Application Signals: `application-signals:ListServices`, `GetService`, `ListServiceOperations`, `ListServiceDependencies`, `ListServiceDependents`, `ListServiceLevelObjectives`, `GetServiceLevelObjective`, `BatchGetServiceLevelObjectiveBudgetReport`, `ListAuditFindings`, `ListEntityEvents`, `ListServiceStates`, and `ListGroupingAttributeDefinitions`
- Dynamic Instrumentation: `application-signals:CreateInstrumentationConfiguration`, `ListInstrumentationConfigurations`, `GetInstrumentationConfiguration`, `DeleteInstrumentationConfiguration`, `BatchDeleteInstrumentationConfigurations`, and `GetInstrumentationConfigurationStatus`
- CloudWatch: `cloudwatch:GetMetricData`, `cloudwatch:GetMetricStatistics`, and `cloudwatch:ListMetrics`
- CloudWatch Logs: `logs:StartQuery`, `logs:GetQueryResults`, `logs:StopQuery`, `logs:FilterLogEvents`, `logs:DescribeLogGroups`, `logs:ListLogAnomalyDetectors`, and `logs:ListAnomalies`
- X-Ray: `xray:BatchGetTraces`, `xray:GetTraceSummaries`, and `xray:GetTraceSegmentDestination`
- Synthetics: `synthetics:DescribeCanaries`, `synthetics:GetCanary`, and `synthetics:GetCanaryRuns`
- RUM: `rum:GetAppMonitor`, `rum:ListAppMonitors`, `rum:ListTagsForResource`, and `rum:GetResourcePolicy`
- Canary artifacts and roles: `s3:ListBucket`, `s3:GetObject`, `iam:GetRole`, `iam:ListAttachedRolePolicies`, `iam:GetPolicy`, and `iam:GetPolicyVersion`, plus `lambda:GetFunction` and `lambda:GetLayerVersion` for the canary's function and layers

The Dynamic Instrumentation actions other than `List*` and `Get*` change resources. Leave them out if you only read.

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

With the AWS MCP Server, ask your agent for the same outcome and it makes the equivalent calls through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters using the API's own names and casing, and returns the response. `call_boto3` pages list operations automatically, up to 1,000 results; a `NextToken` in the response means there are more. The script builds a `result` and ends with `result` on its own line. `asyncio`, `json`, `time`, `datetime`, `re`, and `ClientError` are pre-imported. `run_script` has no network access other than `call_boto3`, so it can only make modeled AWS API calls.

For example, the agent might run this in place of `list_monitored_services`:

```python
end = int(time.time())
start = end - 24 * 3600

services = await call_boto3(
    service_name="application-signals",
    operation_name="ListServices",
    params={"StartTime": start, "EndTime": end},
)

result = {"services": services.get("ServiceSummaries", [])}
result
```

Independent read calls can run in parallel with `await asyncio.gather(*[call_boto3(...) for ...], return_exceptions=True)`.

### Service, SLO, and trace tools

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `list_monitored_services` | Called `application-signals` `ListServices` | `run_script`, as in the example above |
| `query_service_metrics` | Called `ListServices` and `GetService` to find the service's metrics, then `cloudwatch` `GetMetricStatistics` | `run_script` with `GetService` (its `MetricReferences`) and `call_boto3(service_name="cloudwatch", operation_name="GetMetricData", params={...})` |
| `get_slo` | Called `GetServiceLevelObjective` | `call_boto3(service_name="application-signals", operation_name="GetServiceLevelObjective", params={"Id": ...})` |
| `list_slos` | Called `ListServiceLevelObjectives` | `call_boto3(service_name="application-signals", operation_name="ListServiceLevelObjectives", params={})` |
| `list_slis` | Called `ListServices` and `ListServiceLevelObjectives`, then `cloudwatch` `GetMetricData`, and built an SLI report on the client | `run_script` combining the same calls |
| `search_transaction_spans` | Called `xray` `GetTraceSegmentDestination`, then a Logs Insights query (`logs` `StartQuery` and `GetQueryResults`) over the OpenTelemetry span records | `run_script` with the same calls, as in the Logs Insights example below; the `aws-observability` skill's Logs Insights and tracing references |
| `get_xray_trace` | Called `xray` `BatchGetTraces` | `call_boto3(service_name="xray", operation_name="BatchGetTraces", params={"TraceIds": [...]})`; the `aws-observability` skill's tracing reference |
| `list_change_events` | Called `ListEntityEvents` and `ListServiceStates` | `run_script` with the same calls |

### Audit tools

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `audit_services` | Expanded wildcard service targets with `ListServices`, then called `ListAuditFindings` in batches with the selected auditors, and formatted a report | `run_script` with `ListServices` and `call_boto3(service_name="application-signals", operation_name="ListAuditFindings", params={...})` |
| `audit_slos` | Expanded wildcard SLO targets with `ListServiceLevelObjectives`, then called `ListAuditFindings` | `run_script` with the same calls |
| `audit_service_operations` | Expanded wildcard service and operation targets with `ListServices` and `ListServiceOperations`, then called `ListAuditFindings` | `run_script` with the same calls |

### Group tools

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `list_grouping_attribute_definitions` | Called `ListGroupingAttributeDefinitions` | `call_boto3(service_name="application-signals", operation_name="ListGroupingAttributeDefinitions", params={})` |
| `list_group_services` | Called `ListServices` and kept the services whose grouping attributes matched the group | `run_script` with `ListServices`, filtering on the client |
| `audit_group_health` | Called `ListServices`, `GetService`, `ListServiceLevelObjectives`, and `ListServiceDependents`, plus `cloudwatch` `GetMetricStatistics` and `GetMetricData`, for the services in the group | `run_script` with the same calls |
| `get_group_dependencies` | Called `ListServices`, `ListServiceDependencies`, and `GetService` for the services in the group | `run_script` with the same calls; the `aws-observability` skill's service map guidance |
| `get_group_changes` | Called `ListServices` and `ListServiceStates` for the services in the group | `run_script` with the same calls |

### Canary tools

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `list_canaries` | Called `synthetics` `DescribeCanaries` | `call_boto3(service_name="synthetics", operation_name="DescribeCanaries", params={})` |
| `analyze_canary_failures` | Called `synthetics` `GetCanary` and `GetCanaryRuns`; read run artifacts (HAR files, screenshots, logs) with `s3` `ListObjectsV2` and `GetObject`; checked the canary role with `iam` `GetRole`, `ListAttachedRolePolicies`, `GetPolicy`, and `GetPolicyVersion`; read the canary function with `lambda` `GetFunction` and `GetLayerVersionByArn`; queried logs with `StartQuery`, `GetQueryResults`, and `FilterLogEvents`; called `ListAuditFindings` and `ListServiceDependents`; and matched the failure against a bundled knowledge base | `run_script` with the same calls; the `aws-observability` skill's `references/cloudwatch/synthetics.md` common-failures table |

### RUM tool

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `query_rum_events` | Called `rum` `GetAppMonitor` and `ListAppMonitors`; ran pre-built Logs Insights queries with `StartQuery`, `GetQueryResults`, `StopQuery`, and `FilterLogEvents`; called `ListLogAnomalyDetectors`, `ListAnomalies`, `cloudwatch` `GetMetricData`, `xray` `BatchGetTraces`, and `sts` `GetCallerIdentity` | `run_script` with the same calls; the `aws-observability` skill's `references/cloudwatch/log-insights.md` |

### ServiceEvents tools

These tools read function-level metrics through the Prometheus-compatible query API at `https://monitoring.<region>.amazonaws.com/api/v1/` (SigV4, signing service `monitoring`), and incidents, endpoints, and deployments from the `/aws/service-events/<service>` log groups.

The PromQL path isn't available through `run_script`. `call_boto3` only makes modeled AWS API calls; it can't send arbitrary SigV4-signed HTTP requests, and the Prometheus-compatible query API has no modeled API operation (and so no AWS CLI command). Run PromQL queries from your own environment with a SigV4-capable HTTP client instead, for example `awscurl --service monitoring --region <region> "https://monitoring.<region>.amazonaws.com/api/v1/query?query=<promql>"`.

The Logs Insights and Application Signals parts of these tools are modeled APIs and work in `run_script`. For example, the agent might run:

```python
end = int(time.time())
started = await call_boto3(
    service_name="logs",
    operation_name="StartQuery",
    params={
        "logGroupName": "/aws/service-events/<service>",
        "startTime": end - 3600,
        "endTime": end,
        "queryString": "fields @timestamp, @message | sort @timestamp desc | limit 50",
    },
)
await asyncio.sleep(2)
rows = await call_boto3(
    service_name="logs",
    operation_name="GetQueryResults",
    params={"queryId": started["queryId"]},
)

result = {"status": rows.get("status"), "results": rows.get("results", [])}
result
```

If `status` is still `Running`, call `GetQueryResults` again in a later script (or after another short sleep).

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `list_monitored_functions` | Ran a PromQL instant query | A local SigV4 client such as `awscurl`; not available in `run_script` |
| `search_functions_by_name` | Ran a PromQL label-values query | A local SigV4 client such as `awscurl`; not available in `run_script` |
| `get_function_metrics` | Ran PromQL instant queries and a Logs Insights query | PromQL through a local SigV4 client; the Logs Insights query through `run_script` |
| `get_endpoint_performance` | Ran a Logs Insights query and called `ListServices`, `ListServiceOperations`, and `cloudwatch` `GetMetricStatistics` | `run_script` with the same calls; the `aws-observability` skill's Logs Insights reference |
| `get_recent_incidents` | Ran a Logs Insights query | `run_script`, as in the example above |
| `get_incident_root_cause` | Ran a Logs Insights query | `run_script`, as in the example above |
| `get_service_health_overview` | Called `ListServices`, `ListServiceLevelObjectives`, and `ListAuditFindings`, ran PromQL queries, and ran a Logs Insights query | `run_script` for the AWS API calls; PromQL through a local SigV4 client |
| `find_deployment` | Ran a Logs Insights query | `run_script`, as in the example above |

### Dynamic Instrumentation tools

The `aws-observability` skill carries this workflow in `references/cloudwatch/dynamic-instrumentation.md` and ships helper scripts with matching operations. The helper scripts run in your own environment with your local AWS credentials, not inside `run_script`. Every operation below is also a plain AWS API call, so the agent can make it through `run_script` with `call_boto3`. For example, in place of `list_instrumentations`:

```python
configs = await call_boto3(
    service_name="application-signals",
    operation_name="ListInstrumentationConfigurations",
    params={
        "Service": "<service-name>",
        "Environment": "<environment>",
        "InstrumentationType": "<instrumentation-type>",
    },
)

result = {"configurations": configs}
result
```

`GetInstrumentationConfiguration` and `GetInstrumentationConfigurationStatus` take `InstrumentationType`, `Service`, `Environment`, `SignalType`, and `LocationIdentifier`. The two snapshot tools ran Logs Insights queries (`logs` `StartQuery` and `GetQueryResults`) and follow the pattern shown under ServiceEvents tools.

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `create_instrumentation` | Called `CreateInstrumentationConfiguration` | `run_script`, or `di_instrumentation.py create` |
| `list_instrumentations` | Called `ListInstrumentationConfigurations` | `run_script`, as in the example above, or `di_instrumentation.py list` |
| `get_instrumentation` | Called `GetInstrumentationConfiguration` | `run_script`, or `di_instrumentation.py get` |
| `delete_instrumentation` | Called `DeleteInstrumentationConfiguration` | `run_script`, or `di_instrumentation.py delete` |
| `batch_delete_instrumentations_by_scope` | Called `BatchDeleteInstrumentationConfigurations` with a scope | `run_script`, or `di_instrumentation.py batch-delete-by-scope` |
| `batch_delete_instrumentations_by_arns` | Called `BatchDeleteInstrumentationConfigurations` with ARNs | `run_script`, or `di_instrumentation.py batch-delete-by-arns` |
| `get_instrumentation_configuration_status` | Called `GetInstrumentationConfigurationStatus` | `run_script`, or `di_instrumentation.py get-status` |
| `check_instrumentation_status` | Called `GetInstrumentationConfiguration` and `GetInstrumentationConfigurationStatus` | `run_script`, or `di_instrumentation.py check-status` |
| `search_snapshots_for_status_event` | Ran a Logs Insights query on `/aws/service-events/<service>` | `run_script`, or `di_snapshots.py search` |
| `get_sample_snapshot_for_breakpoint` | Ran a Logs Insights query on `/aws/service-events/<service>` | `run_script`, or `di_snapshots.py sample` |

### Enablement tool

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `get_enablement_guide` | Returned a bundled Markdown guide for a platform and language, without calling AWS | The `setting-up-cloudwatch-observability` skill (`references/cloudwatch/application-signals-onboarding.md` and `references/cloudwatch/appsignals-guides/`) |

### Environment variables

| Old variable | Replacement |
|--------------|-------------|
| `AWS_REGION` and `AWS_DEFAULT_REGION` | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call |
| `AWS_PROFILE` | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |
| `MCP_APPLICATIONSIGNALS_ENDPOINT`, `MCP_LOGS_ENDPOINT`, `MCP_CLOUDWATCH_ENDPOINT`, `MCP_XRAY_ENDPOINT`, `MCP_SYNTHETICS_ENDPOINT`, and `MCP_RUM_ENDPOINT` | Not available; `call_boto3` uses each service's standard endpoint |
| `SERVICE_EVENTS_LOG_GROUP_PREFIX` | Not needed; name the log group in the Logs Insights query |
| `MCP_USER_PROMPT` and `MCP_RUN_FROM` | Not needed |
| `MCP_CLOUDWATCH_APPLICATION_SIGNALS_LOG_LEVEL` and `AUDITOR_LOG_PATH` | Not needed; they set the old server's log level and local log file |

## What Improves

- **Every Application Signals API, as it ships.** The old server called a fixed set of operations and needed a release for each new one. `call_boto3` reaches any modeled Application Signals, CloudWatch, X-Ray, Synthetics, or RUM operation available in your SDK model.
- **One script instead of several tool calls.** An audit, its SLOs, and the traces behind a finding can be read in one `run_script`, with independent reads in parallel.
- **Raw responses.** Most of the old tools returned formatted text reports. `run_script` returns the API's own fields, so the agent can filter, count, and compare them as needed.
- **No local server process.** The proxy runs over stdio and reaches the AWS MCP Server over HTTPS, using the standard AWS credential chain or the profile in `AWS_MCP_PROXY_PROFILES`.

## Workflow Change

### Before (CloudWatch Application Signals Server)

1. Install and run `awslabs.cloudwatch-applicationsignals-mcp-server` locally with an AWS profile and Region.
2. Call `audit_services`, `audit_slos`, or `audit_service_operations`, then drill down with `search_transaction_spans`, `get_xray_trace`, or `analyze_canary_failures`.
3. Read the server's formatted reports and bundled recommendations.

### After (AWS MCP Server)

1. Ask your agent for the service health, SLO, trace, canary, or RUM question. It runs the calls through `run_script` with your credentials, and the `aws-observability` skill guides which calls to make.
2. For first-time setup, use the `setting-up-cloudwatch-observability` skill.
3. For ServiceEvents function metrics, run the PromQL queries from your own environment with a SigV4 client.

## Summary of Gaps

The owning team reviewed this server's bundled content and chose not to carry it forward. The AWS MCP Server doesn't re-implement it; where an Agent Skill covers similar ground, it's listed below.

| Feature | Status | Workaround |
|---------|--------|------------|
| Canary failure knowledge base (16 bundled failure-pattern entries) and recommendation engine used by `analyze_canary_failures` | Not available | The `aws-observability` skill's `references/cloudwatch/synthetics.md` common-failures table |
| Canary artifact analysis (HAR files, screenshots, and run logs in S3; IAM role and Lambda layer checks; disk and memory metrics) | Not available | Fetch the artifacts and call the IAM, Lambda, and CloudWatch APIs with `run_script` |
| Audit orchestration (wildcard expansion of services, SLOs, and operations; batching; auditor selection; formatted reports) | Changed | Call `ListAuditFindings` with `run_script` |
| Bundled enablement guides (16 platform and language templates) | Changed | The `setting-up-cloudwatch-observability` skill, with per-platform guides for the same 16 combinations |
| Pre-built RUM Logs Insights query templates and platform detection | Not available | The `aws-observability` skill's `references/cloudwatch/log-insights.md`; write the queries with `run_script` |
| Client-side SLI report (`list_slis`) | Not available | Combine `ListServiceLevelObjectives` and `cloudwatch` `GetMetricData` with `run_script` |
| ServiceEvents PromQL queries and incident and deployment formatting | Not available | Run Logs Insights queries with `run_script`. PromQL needs SigV4-signed HTTP, which `call_boto3` can't make; run it locally with a SigV4 client such as `awscurl` |
| Dynamic Instrumentation tools | Changed | The `aws-observability` skill's `di_instrumentation.py` and `di_snapshots.py` (run locally), or the same `application-signals` and `logs` APIs through `call_boto3` in `run_script` |
| Custom service endpoints (`MCP_*_ENDPOINT`) | Not available | `call_boto3` uses each service's standard endpoint |

## What Deprecation Means

- The final release keeps working. It prints a `FutureWarning` to standard error at startup, and its server instructions and tool descriptions are marked deprecated.
- The package stays on PyPI and gets no further updates.
- Configurations that use `awslabs.cloudwatch-applicationsignals-mcp-server@latest` get that final release.
- The `src/cloudwatch-applicationsignals-mcp-server` folder may later be removed from this repository, as the folders of earlier deprecated servers were.

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.cloudwatch-applicationsignals-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.cloudwatch-applicationsignals-mcp-server`
