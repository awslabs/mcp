# Migration Guide: Amazon Kendra Index MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.amazon-kendra-index-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The Amazon Kendra Index MCP server registered two tools, `KendraListIndexesTool` and `KendraQueryTool`, which made two Amazon Kendra API calls: `ListIndices` and `Query`. `KendraQueryTool` sent only the index ID and the query text, and it returned a trimmed copy of each result. The AWS MCP Server makes the same calls through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. It returns the full responses, and it can also call `Retrieve`, which returns longer passages for retrieval-augmented generation.

Amazon Kendra itself is in maintenance mode. It stopped getting new features on June 30, 2026, and stopped accepting new customers on July 30, 2026; existing customers keep full support. AWS recommends Amazon Bedrock Managed Knowledge Base for new search applications. See [Amazon Kendra availability change](https://docs.aws.amazon.com/kendra/latest/dg/kendra-availability-change.html). This guide only moves the MCP server; your index stays where it is.

No Agent Skill in the Agent Toolkit for AWS covers Amazon Kendra, so there is no skill to install for it.

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

Set `AWS_REGION` to the Region of your Amazon Kendra index. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

Your identity needs the same permissions the old server needed: `kendra:ListIndices`, which takes no resource, so grant it on `*`, and `kendra:Query` on the index (`arn:aws:kendra:<region>:<account-id>:index/<index-id>`). Add `kendra:Retrieve` on the index if you want the agent to use `Retrieve`.

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `KendraListIndexesTool(region)` | Called `ListIndices` in `region` (else `AWS_REGION`, else `us-east-1`), followed `NextToken` to the last page, and returned `region`, `count` and each index's `Id`, `Name`, `Status`, `Edition`, `CreatedAt` and `UpdatedAt`. Those are all six summary fields, renamed to snake_case, with timestamps as ISO 8601 strings | `call_boto3` with `service_name="kendra"` and `operation_name="ListIndices"`, with `region_name` set to the Region. botocore has no paginator for `ListIndices`, so pass `NextToken` back while a response carries one |
| `KendraQueryTool(query, indexId, region)` | Called `Query` with only `IndexId` (from `indexId`, else `KENDRA_INDEX_ID`) and `QueryText=query`, so it always got Kendra's default first page of 10 results. Returned `total_results_count` and, for each result, `Id`, `Type`, the title text, `DocumentURI`, `ScoreConfidence`, the excerpt text and `AdditionalAttributes`. It dropped `QueryId`, `FacetResults`, `FeaturedResultsItems`, `SpellCorrectedQueries` and `Warnings`, and each result's `DocumentId`, `DocumentAttributes`, `Format`, `TableExcerpt`, `FeedbackToken`, `CollapsedResultDetail` and highlight offsets | `call_boto3` with `service_name="kendra"` and `operation_name="Query"`, passing `IndexId` and `QueryText`. For passages to ground an answer, `operation_name="Retrieve"` with the same two params |

Ask your agent the same question and give it your index ID, or ask it to list your indexes first. It runs the calls through `run_script`. For example, listing indexes, with a loop that handles more than one page:

```python
indexes = []
params = {}
while True:
    resp = await call_boto3(
        service_name="kendra",
        operation_name="ListIndices",
        region_name="us-east-1",
        params=params,
    )
    indexes.extend(resp.get("IndexConfigurationSummaryItems", []))
    if not resp.get("NextToken"):
        break
    params = {"NextToken": resp["NextToken"]}
result = [
    {"id": i["Id"], "name": i["Name"], "status": i["Status"], "edition": i.get("Edition")}
    for i in indexes
]
result
```

Querying an index:

```python
resp = await call_boto3(
    service_name="kendra",
    operation_name="Query",
    region_name="us-east-1",
    params={
        "IndexId": "<index-id>",
        "QueryText": "How do I send a progress event from a CreateHandler?",
    },
)
result = {
    "query_id": resp["QueryId"],
    "total": resp.get("TotalNumberOfResults"),
    "results": [
        {
            "type": item["Type"],
            "title": item.get("DocumentTitle", {}).get("Text"),
            "uri": item.get("DocumentURI"),
            "excerpt": item.get("DocumentExcerpt", {}).get("Text"),
            "confidence": item.get("ScoreAttributes", {}).get("ScoreConfidence"),
        }
        for item in resp.get("ResultItems", [])
    ],
}
result
```

For retrieval-augmented generation, `Retrieve` returns up to 100 passages of up to 200 token words each, where `Query` excerpts are up to 100 token words by default. It doesn't return question-answer or FAQ results; use `Query` for those.

```python
resp = await call_boto3(
    service_name="kendra",
    operation_name="Retrieve",
    region_name="us-east-1",
    params={
        "IndexId": "<index-id>",
        "QueryText": "How do I send a progress event from a CreateHandler?",
        "PageSize": 5,
    },
)
result = [
    {
        "title": item.get("DocumentTitle"),
        "uri": item.get("DocumentURI"),
        "passage": item["Content"],
        "confidence": item.get("ScoreAttributes", {}).get("ScoreConfidence"),
    }
    for item in resp.get("ResultItems", [])
]
result
```

### Environment variables

| Old variable | Replacement |
|--------------|-------------|
| `AWS_REGION` | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call |
| `KENDRA_INDEX_ID` | `IndexId` in each call; tell the agent the index ID in your prompt or project instructions |
| `AWS_PROFILE` | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |
| `KEND_INDEX_ID`, `KEND_ROLE_ARN` | Nothing to move. The Kiro, Cursor and VS Code install buttons set these, but the server never read them, so a server installed that way had no default index |

## What Improves

- **Full results.** The old tool kept seven fields from each result. The full `Query` response also carries `QueryId`, which `SubmitFeedback` needs, along with facet counts, featured results, spelling suggestions, query syntax warnings, and each result's `DocumentId`, `DocumentAttributes` and highlight offsets.
- **Table answers.** When Kendra answers from a table, the result has `Format` set to `TABLE` and the table in `TableExcerpt`. The old tool dropped `TableExcerpt`, so the agent got the result's title and confidence without the table. The full response carries it.
- **Every `Query` parameter.** The old tool sent only `IndexId` and `QueryText`. Through `call_boto3` the agent can set `PageSize` (up to 100) and `PageNumber`, `AttributeFilter` and `UserContext` for filtering by document attributes or user access, `Facets`, `QueryResultTypeFilter`, `SortingConfiguration` and the other request fields.
- **`Retrieve` for grounding answers.** The old server had no tool for `Retrieve`, which returns longer passages drawn from several parts of a document.

## Workflow Change

### Before (Amazon Kendra Index Server)

1. Set `AWS_REGION` and, optionally, `KENDRA_INDEX_ID` before starting the server
2. Ask a question; the server calls `Query` on that index, or on one named in the prompt, and returns the first 10 results with seven fields each

### After (AWS MCP Server)

1. Give the agent your index ID and Region, or ask it to list your indexes
2. Ask a question; the agent calls `Query` or `Retrieve` through `run_script` and gets the full response, with whatever page size, filters or user context it sets

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Default index from `KENDRA_INDEX_ID` | Not available | Put the index ID in your prompt or project instructions; the agent passes it as `IndexId` |
| Read-only by construction (the server could only list indexes and query them) | Not available | `run_script` can call any Kendra operation your credentials allow, including `BatchPutDocument` and `DeleteIndex`. Allow only `kendra:ListIndices`, `kendra:Query` and, if you want it, `kendra:Retrieve` in the IAM policy the agent's credentials use, with the last two scoped to the index ARN |
| Short, fixed result shape | Changed | The full response is larger. Ask the agent to keep the fields you need, as the examples above do |
| `NextToken` followed automatically by `KendraListIndexesTool` | Changed | `call_boto3` returns one page of `ListIndices`; loop on `NextToken` as in the example. An account can hold 10 indexes by default |
| Error returned as a text string instead of raised | Changed | `run_script` reports API errors, such as a `ResourceNotFoundException` for a wrong index ID, with `"status": "error"` and the error message |

## What Deprecation Means

- The final release keeps working. It prints a `FutureWarning` at startup, and its server instructions and tool descriptions are marked deprecated.
- The package stays on PyPI and gets no further updates.
- Configurations that use `awslabs.amazon-kendra-index-mcp-server@latest` get that final release.
- The `src/amazon-kendra-index-mcp-server` folder may later be removed from this repository, as the folders of earlier deprecated servers were.

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.amazon-kendra-index-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.amazon-kendra-index-mcp-server`
