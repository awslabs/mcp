# Migration Guide: Amazon Q Business Anonymous MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.amazon-qbusiness-anonymous-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The Amazon Q Business anonymous MCP server registered one tool, `QBusinessQueryTool`, which made one Amazon Q Business API call: `ChatSync` against the application named in `QBUSINESS_APPLICATION_ID`. It returned only the answer text. The AWS MCP Server makes the same call through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. It returns the full `ChatSync` response, including the source citations the old tool dropped.

The server carried no bundled guidance, so there is no Agent Skill to install for it.

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

Set `AWS_REGION` to the Region of your Amazon Q Business application. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

Your identity needs the same permission the old server needed: `qbusiness:ChatSync` on the application.

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `QBusinessQueryTool(query)` | Called `ChatSync` with `applicationId` from `QBUSINESS_APPLICATION_ID`, `userMessage=query` and a random `clientToken`, then returned `"Qbiz response: "` followed by `systemMessage` | `call_boto3` with `service_name="qbusiness"` and `operation_name="ChatSync"`, passing `applicationId` and `userMessage` |

Ask your agent the same question and give it your application ID. It runs the call through `run_script`. For example:

```python
resp = await call_boto3(
    service_name="qbusiness",
    operation_name="ChatSync",
    region_name="us-east-1",
    params={
        "applicationId": "<application-id>",
        "userMessage": "What is our policy on remote work?",
    },
)
result = {
    "answer": resp["systemMessage"],
    "sources": [a.get("title") for a in resp.get("sourceAttributions", [])],
}
result
```

An application created with anonymous access has no end-user identities, so the call carries no `userId`, as before.

### Environment variables

| Old variable | Replacement |
|--------------|-------------|
| `AWS_REGION` | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call |
| `QBUSINESS_APPLICATION_ID` | `applicationId` in each call; tell the agent the application ID in your prompt or project instructions |
| `AWS_PROFILE` | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |

## What Improves

- **Source citations.** The old tool returned only `systemMessage` and discarded `sourceAttributions`. The full response carries them, so the agent can cite the documents an answer came from.
- **Follow-up questions.** The response carries `conversationId` and `systemMessageId`. Passing them back as `conversationId` and `parentMessageId` continues the same conversation, which the old tool could not do.
- **More than one application.** The application ID is a per-call parameter, so one session can query several Amazon Q Business applications.
- **Idempotency tokens.** The old server sent a random integer between 0 and 10,000 as `clientToken`, so two queries had an even chance of sharing a token within about 120 queries, and Amazon Q Business treats a repeated token as a replay. When `clientToken` is omitted, the AWS SDK generates a UUID for each call.

## Workflow Change

### Before (Amazon Q Business Anonymous Server)

1. Set `AWS_REGION` and `QBUSINESS_APPLICATION_ID` before starting the server, one application per server process
2. Ask a question; the server calls `ChatSync` and returns the answer text without its sources

### After (AWS MCP Server)

1. Give the agent your application ID and Region
2. Ask a question; the agent calls `ChatSync` through `run_script` and gets the answer with its source citations and conversation IDs

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Agent limited to the one application set in `QBUSINESS_APPLICATION_ID` | Not available | Allow `qbusiness:ChatSync` only on that application's ARN in the IAM policy the agent's credentials use |
| Error returned as a text string instead of raised | Changed | `run_script` reports API errors, such as an `AccessDeniedException` or a `ConflictException` from an application with no ready retriever, in its response |

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.amazon-qbusiness-anonymous-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.amazon-qbusiness-anonymous-mcp-server`
3. The old package will remain on PyPI but will not receive updates
