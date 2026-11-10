# Migration Guide: AWS CloudTrail MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.cloudtrail-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The AWS CloudTrail MCP Server registered 5 tools, and all of them only read. `lookup_events` called `LookupEvents` to search the last 90 days of management events in one Region. The other four worked with CloudTrail Lake: `list_event_data_stores` called `ListEventDataStores` and `GetEventDataStore`, `lake_query` called `StartQuery` and polled `DescribeQuery`, and `get_query_status` and `get_query_results` called `DescribeQuery` and `GetQueryResults`. The server's one piece of bundled guidance was the `lake_query` tool description (over 7,700 characters), which listed the CloudTrail record fields and six example queries. The AWS MCP Server makes the same calls through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. The agent can filter and count events inside the sandbox and get back only the answer, instead of reading every page of events.

CloudTrail Lake closed to new customers on May 31, 2026 (see [CloudTrail Lake availability change](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake-service-availability-change.html)). The Lake tools on either server only work in accounts that already have an event data store, or that an organization event data store covers.

The [`aws-observability`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-observability) Agent Skill covers CloudTrail auditing in its `references/cloudwatch/cloudtrail.md` reference: event types, event history lookups for questions such as "who deleted or changed this resource", querying a trail's logs with Amazon Athena, and alarms on specific API calls. For an account whose trail doesn't send events to CloudWatch Logs yet, the [`setting-up-cloudtrail-multi-region`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/specialized-skills/operations-skills/setting-up-cloudtrail-multi-region) skill sets up a multi-Region trail with CloudWatch Logs and Logs Insights queries. Neither skill covers CloudTrail Lake SQL.

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
        "AWS_REGION=us-east-1"
      ]
    }
  }
}
```

Set `AWS_REGION` to the Region you query most. Event history is kept per Region, and events from IAM and other global services are recorded in `us-east-1`, so ask for each Region the question covers; each `call_boto3` call takes its own `region_name`. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

### Installing the Agent Skills

```bash
npx skills add aws/agent-toolkit-for-aws/skills
```

This installs the [`aws-observability`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-observability) skill along with the other core skills. The AWS MCP Server also serves `aws-observability` and `setting-up-cloudtrail-multi-region` through its `retrieve_skill` tool.

Your identity needs the same permissions the old server needed:

- `cloudtrail:LookupEvents`
- `cloudtrail:ListEventDataStores`, `cloudtrail:GetEventDataStore`, `cloudtrail:StartQuery`, `cloudtrail:DescribeQuery`, and `cloudtrail:GetQueryResults` for CloudTrail Lake

To find a trail's log group, query it with Logs Insights, or use CloudTrail's sample Lake queries, add `cloudtrail:DescribeTrails`, `logs:StartQuery`, `logs:GetQueryResults`, and `cloudtrail:SearchSampleQueries`.

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

Every tool in the CloudTrail server was a wrapper around CloudTrail API calls. With the AWS MCP Server, ask your agent to perform the same operation and it will make the equivalent call through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. `lookup_events` returned the `LookupEvents` events unchanged, in an object with `events`, `next_token`, and `query_params`, so each event has the same fields. The Lake tools renamed fields to snake case (`query_id`, `query_status`, `query_result_rows`), where `call_boto3` returns the API's own names (`QueryId`, `QueryStatus`, `QueryResultRows`).

`call_boto3` pages `LookupEvents` automatically, up to 1,000 events per call. When more events match, the response has a `NextToken` and `run_script` adds a pagination warning; pass the `NextToken` back with the same parameters to get the next 1,000. If you set `MaxResults`, `call_boto3` returns a single page.

For example, the agent might run this in place of paging through `lookup_events` to find who changed IAM in the last 24 hours:

```python
import datetime as dt
import json

end = dt.datetime.now(dt.timezone.utc)
params = {
    "LookupAttributes": [{"AttributeKey": "ReadOnly", "AttributeValue": "false"}],
    "StartTime": (end - dt.timedelta(hours=24)).isoformat(),
    "EndTime": end.isoformat(),
}
changes = []
while True:
    resp = await call_boto3(
        service_name="cloudtrail",
        operation_name="LookupEvents",
        region_name="us-east-1",
        params=params,
    )
    for event in resp.get("Events", []):
        if event["EventSource"] != "iam.amazonaws.com":
            continue
        record = json.loads(event["CloudTrailEvent"])
        changes.append({
            "time": record["eventTime"],
            "event": record["eventName"],
            "actor": record["userIdentity"].get("arn"),
            "error": record.get("errorCode"),
        })
    if not resp.get("NextToken"):
        break
    params["NextToken"] = resp["NextToken"]
result = changes
result
```

`LookupEvents` takes one lookup attribute per call, so the script asks for write events and checks the event source in Python. `CloudTrailEvent` is a JSON string; `json.loads` gives the full record, with `userIdentity`, `errorCode`, `requestParameters`, and `sourceIPAddress`.

And this in place of `lake_query`, in an account that already has an event data store:

```python
import asyncio

eds_id = "<event-data-store-id>"
started = await call_boto3(
    service_name="cloudtrail",
    operation_name="StartQuery",
    region_name="us-east-1",
    params={
        "QueryStatement": f"SELECT eventsource, eventname, count(*) AS n FROM {eds_id} "
        "WHERE eventtime > '2026-11-01 00:00:00' GROUP BY eventsource, eventname ORDER BY n DESC LIMIT 10"
    },
)
query_id = started["QueryId"]
for _ in range(60):
    status = await call_boto3(
        service_name="cloudtrail",
        operation_name="DescribeQuery",
        region_name="us-east-1",
        params={"QueryId": query_id},
    )
    if status["QueryStatus"] in ("FINISHED", "FAILED", "CANCELLED", "TIMED_OUT"):
        break
    await asyncio.sleep(2)
rows = []
params = {"QueryId": query_id, "MaxQueryResults": 1000}
while status["QueryStatus"] == "FINISHED":
    page = await call_boto3(
        service_name="cloudtrail",
        operation_name="GetQueryResults",
        region_name="us-east-1",
        params=params,
    )
    rows += [{k: v for column in row for k, v in column.items()} for row in page.get("QueryResultRows", [])]
    if not page.get("NextToken"):
        break
    params["NextToken"] = page["NextToken"]
result = {
    "status": status["QueryStatus"],
    "statistics": status.get("QueryStatistics"),
    "error": status.get("ErrorMessage"),
    "rows": rows,
}
result
```

CloudTrail Lake bills by the data each query scans, so keep the `eventtime` range in the `WHERE` clause.

### Event history

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `lookup_events` | Called `LookupEvents` with `StartTime`, `EndTime`, `MaxResults`, and, when both `attribute_key` and `attribute_value` were given, one `LookupAttributes` entry (`EventId`, `EventName`, `ReadOnly`, `Username`, `ResourceType`, `ResourceName`, `EventSource`, or `AccessKeyId`). Took ISO 8601 times or relative times such as `1 day ago`, and with no times searched the last day. Returned 10 events by default and at most 50 a call (a larger `max_results` became 50), plus `next_token` and the `query_params` to send back with it for the next page. Queried `us-east-1` unless the call passed `region`. | `run_script` with `call_boto3(service_name="cloudtrail", operation_name="LookupEvents", params={"LookupAttributes": [{"AttributeKey": ..., "AttributeValue": ...}], "StartTime": ..., "EndTime": ...})`, which returns up to 1,000 events per call, as in the first example. `EventCategory="insight"` looks up CloudTrail Insights events, which the old tool couldn't. |

### CloudTrail Lake

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `list_event_data_stores` | Called `ListEventDataStores` (first page only), then, with `include_details` (the default), `GetEventDataStore` for each store to add its advanced event selectors and its multi-Region and organization settings | `run_script` combining `call_boto3(service_name="cloudtrail", operation_name="ListEventDataStores")` and, for each store, `call_boto3(service_name="cloudtrail", operation_name="GetEventDataStore", params={"EventDataStore": ...})` |
| `lake_query` | Called `StartQuery` with the SQL (the event data store ID goes in the `FROM` clause). With `wait_for_completion` (the default), polled `DescribeQuery` every 2 seconds for up to 5 minutes, then returned the first 50 rows from `GetQueryResults`. Without it, called `DescribeQuery` once and returned the query ID and status. | `run_script` combining `StartQuery`, `DescribeQuery`, and `GetQueryResults`, as in the second example. `StartQuery` also takes `DeliveryS3Uri` to save the results to Amazon S3, which the old tool didn't send. |
| `get_query_status` | Called `DescribeQuery` with `QueryId` and returned the status, statistics, error message, and S3 delivery fields | `run_script` with `call_boto3(service_name="cloudtrail", operation_name="DescribeQuery", params={"QueryId": ...})` |
| `get_query_results` | Called `GetQueryResults` with `QueryId`, `NextToken`, and `MaxQueryResults` (at most 50; a larger value became 50), then `DescribeQuery` for the status | `run_script` with `call_boto3(service_name="cloudtrail", operation_name="GetQueryResults", params={"QueryId": ..., "MaxQueryResults": 1000, "NextToken": ...})`. The API returns up to 1,000 rows a page, and the response includes `QueryStatus` and `QueryStatistics`. |

### Accounts without an event data store

If the trail delivers events to CloudWatch Logs, CloudWatch Logs Insights answers many of the counting and grouping questions Lake SQL was used for. `DescribeTrails` returns each trail's `CloudWatchLogsLogGroupArn`. Logs Insights bills by the data each query scans, so bound every query with `startTime` and `endTime`. This finds the calls that failed in the last hour, grouped by service, operation, and error:

```python
import asyncio
import time

log_group = "<trail-log-group-name>"
end = int(time.time())
started = await call_boto3(
    service_name="logs",
    operation_name="StartQuery",
    region_name="us-east-1",
    params={
        "logGroupName": log_group,
        "startTime": end - 3600,
        "endTime": end,
        "queryString": "filter ispresent(errorCode) | stats count(*) as n by eventSource, eventName, errorCode | sort n desc | limit 20",
    },
)
for _ in range(60):
    resp = await call_boto3(
        service_name="logs",
        operation_name="GetQueryResults",
        region_name="us-east-1",
        params={"queryId": started["queryId"]},
    )
    if resp["status"] in ("Complete", "Failed", "Cancelled", "Timeout"):
        break
    await asyncio.sleep(2)
result = {
    "status": resp["status"],
    "bytes_scanned": resp["statistics"]["bytesScanned"],
    "rows": [{field["field"]: field["value"] for field in row} for row in resp["results"]],
}
result
```

If the trail only delivers to Amazon S3, query its logs with Athena, as the `aws-observability` skill's CloudTrail reference describes. To move an existing event data store's data into CloudWatch, see [CloudTrail Lake availability change](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake-service-availability-change.html).

Because `run_script` exposes the full CloudTrail API, operations the old server never had, such as `DescribeTrails`, `GetEventSelectors`, `SearchSampleQueries`, `GenerateQuery`, and `CancelQuery`, are also available.

### Environment variables

| Old variable | Replacement |
|--------------|-------------|
| `AWS_PROFILE` | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |
| `AWS_REGION` | The old server didn't use it: every tool's `region` argument defaulted to `us-east-1`. Use `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | Set them in the proxy's `env` block; the proxy signs requests with the standard AWS credential chain |
| `FASTMCP_LOG_LEVEL` | Not needed. The README's configurations set it, but the server logged at `INFO` either way. |

## What Improves

- **A day of changes in one call.** In a test over the same 24 hours, finding who changed IAM took 70 `lookup_events` calls and 8.3 MB of tool results, because each call returned at most 50 events and the agent had to read all 3,480 write events to find the 2 IAM changes. One `run_script` call using the first example's pattern read the same 3,480 events in 4 `call_boto3` calls inside the sandbox and returned only the 2 IAM changes, with the same event IDs.
- **Filters on any field.** `LookupEvents` filters on one attribute, and `lookup_events` had no way to filter on anything else, such as `errorCode` or the role behind an assumed-role session. In `run_script`, the agent parses `CloudTrailEvent` and filters on any field of the record before anything comes back.
- **Counts and groupings without Lake.** With no event data store, the old server could answer a question such as "which calls failed in the last hour, by service and error" only by paging through every event 50 at a time, and the test account logged 11,587 events in `us-east-1` in one hour. The Logs Insights example answered it in one `run_script` call over the trail's log group, scanning 29.7 MB.
- **Missing lookup values caught before the call.** When `attribute_key` came without `attribute_value`, `lookup_events` dropped the filter and returned the newest events unfiltered, while its `query_params` still showed the key. `call_boto3` stops that request before it reaches AWS: `Missing required parameter in LookupAttributes[0]: "AttributeValue"`.
- **Full pages of Lake results.** `get_query_results` capped each page at 50 rows and `lake_query` returned only the first 50; `GetQueryResults` returns up to 1,000 rows a page. `list_event_data_stores` read only the first page of `ListEventDataStores`.
- **No blocked server while a query runs.** `lake_query` waited with `time.sleep` inside the server's event loop, for up to 5 minutes, so the server couldn't answer any other tool call during that wait.
- **CloudTrail's own query library.** `SearchSampleQueries` works without an event data store and returns sample Lake SQL that CloudTrail maintains, with a `$EDS_ID` placeholder for the store ID. `GenerateQuery` writes Lake SQL from a plain-language question for a named event data store.

## Workflow Change

### Before (AWS CloudTrail Server)

1. Set `AWS_PROFILE` and start the server. Every tool queries `us-east-1` unless the call passes `region`.
2. Call `lookup_events` with one attribute and a time range, and page through the results 50 events at a time with `next_token` and the returned `query_params`.
3. For SQL, call `list_event_data_stores`, then `lake_query`, which waits up to 5 minutes and returns the first 50 rows, then `get_query_results` for the rest.

### After (AWS MCP Server)

1. Ask your agent the question, such as who changed a role or which calls failed. It runs `LookupEvents` through `run_script`, filters the events in the script, and returns the answer.
2. For counts and groupings, the agent queries the trail's CloudWatch Logs log group with Logs Insights, or an existing event data store with Lake SQL.
3. Whether a call succeeds is decided by IAM: your identity-based policies, permissions boundaries, and service control policies (SCPs).

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Read-only tools (all five only read) | Not available | `run_script` can call any API your credentials allow, including `StopLogging` and `DeleteTrail`. Run with credentials that allow only the read actions listed above, or deny CloudTrail write actions (such as `cloudtrail:StopLogging`, `cloudtrail:DeleteTrail`, `cloudtrail:UpdateTrail`, `cloudtrail:PutEventSelectors`, and `cloudtrail:DeleteEventDataStore`) with a permissions boundary or SCP |
| Relative times such as `1 day ago` or `2 hours ago` | Changed | The agent computes ISO 8601 times in the script, as in the first example |
| A default of the last day and 10 events when `lookup_events` got no times or count | Changed | Give `StartTime` and `EndTime`. Without them, `LookupEvents` searches all 90 days, and `call_boto3` returns up to 1,000 of the newest events. |
| Waiting for a Lake query inside one tool call (2-second polls for up to 5 minutes) | Changed | The script polls `DescribeQuery`, as in the second example. Each poll is a `call_boto3` call, and `run_script` stops a script at 100 calls, so for a long query ask the agent to check `DescribeQuery` again later. |
| CloudTrail record fields and six example queries in the `lake_query` description | Changed | `SearchSampleQueries` returns CloudTrail's maintained sample Lake SQL. For the record fields, see [CloudTrail record contents](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html). |
| CloudTrail Lake in an account with no event data store | Not available | Lake is closed to new customers, for either server. Use Logs Insights on the trail's log group, as in the third example, or Athena over the trail's S3 bucket. |

## What Deprecation Means

- The final release keeps working. It prints a `FutureWarning` at startup, and its server instructions and tool descriptions are marked deprecated.
- The package stays on PyPI and gets no further updates.
- Configurations that use `awslabs.cloudtrail-mcp-server@latest` get that final release.
- The `src/cloudtrail-mcp-server` folder may later be removed from this repository, as the folders of earlier deprecated servers were.

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.cloudtrail-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.cloudtrail-mcp-server`
