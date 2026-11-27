# Migration Guide: AWS AppSync MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.aws-appsync-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The AWS AppSync MCP Server registered 10 tools, and every one of them created an AppSync resource: GraphQL APIs, Event APIs, API keys, caches, data sources, functions, resolvers, schemas, channel namespaces, and custom domain names. Each tool made one AppSync API call, except `create_graphql_api`, which also created an API key for `API_KEY` APIs, and `create_schema`, which started schema creation and polled until it finished. The server had no tools to list, read, update, or delete anything. The AWS MCP Server makes the same calls through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. It also reaches the rest of the AppSync API, including the list, get, update, and delete operations this server didn't have.

No Agent Skill covers the AppSync API, so there is no skill to install for it.

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

Set `AWS_REGION` to the Region of your AppSync APIs. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

Your identity needs the same permissions the old server needed:

- `appsync:CreateGraphqlApi`, `appsync:CreateApi`, `appsync:CreateApiKey`, `appsync:CreateApiCache`, `appsync:CreateDataSource`, `appsync:CreateFunction`, `appsync:CreateResolver`, `appsync:CreateChannelNamespace`, `appsync:CreateDomainName`, `appsync:StartSchemaCreation`, and `appsync:GetSchemaCreationStatus`
- `appsync:TagResource` when you pass `tags`
- `iam:PassRole` on any role you hand to AppSync, such as a data source service role, a CloudWatch Logs role, or a merged API execution role
- `acm:DescribeCertificate` on the certificate and `cloudfront:UpdateDistribution` for custom domain names

To list, update, or delete AppSync resources, which the old server couldn't do, add the matching actions, such as `appsync:ListGraphqlApis` or `appsync:DeleteGraphqlApi`.

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

Every tool in the AppSync server was a wrapper around one or two AppSync API calls. With the AWS MCP Server, ask your agent to perform the same operation and it will make the equivalent call through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. The old tools returned the same objects AppSync returns, such as `{"graphqlApi": {...}}` or `{"resolver": {...}}`, so the responses have the same shape.

For example, the agent might run this in place of `create_graphql_api`:

```python
api = await call_boto3(
    service_name="appsync",
    operation_name="CreateGraphqlApi",
    region_name="us-east-1",
    params={"name": "blog-api", "authenticationType": "API_KEY"},
)
api_id = api["graphqlApi"]["apiId"]
key = await call_boto3(
    service_name="appsync",
    operation_name="CreateApiKey",
    region_name="us-east-1",
    params={"apiId": api_id, "description": "Auto-generated API key"},
)
result = {"graphqlApi": api["graphqlApi"], "apiKey": key["apiKey"]}
result
```

And this in place of `create_schema`:

```python
import asyncio

api_id = "<api-id>"
await call_boto3(
    service_name="appsync",
    operation_name="StartSchemaCreation",
    region_name="us-east-1",
    params={"apiId": api_id, "definition": "type Query { getPost(id: ID!): Post }\ntype Mutation { deletePost(id: ID!): Post }\ntype Post { id: ID! content: String description: String }"},
)
for _ in range(30):
    status = await call_boto3(
        service_name="appsync",
        operation_name="GetSchemaCreationStatus",
        region_name="us-east-1",
        params={"apiId": api_id},
    )
    if status["status"] in ("SUCCESS", "FAILED", "ACTIVE", "NOT_APPLICABLE"):
        break
    await asyncio.sleep(2)
result = {"status": status["status"], "details": status.get("details")}
result
```

### GraphQL APIs, API keys, and caches

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `create_graphql_api` | Checked `name`, `authentication_type` (one of five values), `visibility`, `api_type`, `introspection_config`, `query_depth_limit` (0 to 75), `resolver_count_limit` (0 to 10,000), and the merged API role ARN, then called `CreateGraphqlApi`. When `authentication_type` was `API_KEY`, it also called `CreateApiKey` with the description `Auto-generated API key` and returned the key with the API. | `run_script` combining `call_boto3(service_name="appsync", operation_name="CreateGraphqlApi", params={"name": ..., "authenticationType": ...})` and, for `API_KEY` APIs, `CreateApiKey`, as in the first example |
| `create_api_key` | Called `CreateApiKey` with `apiId` and the optional `description` and `expires`. With no `expires`, AppSync sets the key to expire 7 days after creation. | `run_script` with `call_boto3(service_name="appsync", operation_name="CreateApiKey", params={"apiId": ..., "description": ..., "expires": ...})`. `expires` is in seconds since the epoch, between 1 and 365 days out. |
| `create_api_cache` | Called `CreateApiCache` with `apiId`, `ttl`, `apiCachingBehavior`, `type`, and the optional encryption and health metrics settings | `run_script` with `call_boto3(service_name="appsync", operation_name="CreateApiCache", params={"apiId": ..., "ttl": ..., "apiCachingBehavior": ..., "type": ...})`. AppSync bills a cache by the hour until you delete it with `DeleteApiCache`. |

### Schemas, data sources, functions, and resolvers

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `create_schema` | Refused the definition unless it contained `type Query {`, had balanced braces, and contained none of 50 substrings (among them `sc`, `su`, `sh`, `del`, `\|`, and `--`), then called `StartSchemaCreation` and polled `GetSchemaCreationStatus` every 2 seconds for up to 5 minutes. Returned `status` and `details`. | `run_script` combining `StartSchemaCreation` and `GetSchemaCreationStatus`, as in the second example |
| `create_datasource` | Checked that `service_role_arn` matched `arn:aws:iam::<12 digits>:role/...`, and that an HTTP endpoint used `https://` and wasn't `localhost`, a non-public IP address, or a hex, octal, or decimal number. Then called `CreateDataSource` with the parameters given. | `run_script` with `call_boto3(service_name="appsync", operation_name="CreateDataSource", params={"apiId": ..., "name": ..., "type": ..., "serviceRoleArn": ..., "dynamodbConfig": ...})`, passing the config for the data source type (`lambdaConfig`, `httpConfig`, `relationalDatabaseConfig`, and so on) |
| `create_function` | Called `CreateFunction` with the parameters given: VTL mapping templates, or `runtime` and `code` for JavaScript | `run_script` with `call_boto3(service_name="appsync", operation_name="CreateFunction", params={"apiId": ..., "name": ..., "dataSourceName": ..., "runtime": {"name": "APPSYNC_JS", "runtimeVersion": "1.0.0"}, "code": ...})` |
| `create_resolver` | Called `CreateResolver` with the parameters given, for a unit or pipeline resolver in VTL or JavaScript | `run_script` with `call_boto3(service_name="appsync", operation_name="CreateResolver", params={"apiId": ..., "typeName": ..., "fieldName": ..., "kind": "PIPELINE", "pipelineConfig": {"functions": [...]}, "runtime": ..., "code": ...})` |

### Event APIs

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `create_api` | Called `CreateApi` to create an AppSync Event API with `name` and the optional `ownerContact`, `tags`, and `eventConfig`. The tool marked `eventConfig` optional, but `CreateApi` requires it. botocore 1.42.6 and later, which a new install gets, stop a call without it before it's sent (`Missing required parameter in input: "eventConfig"`); with older botocore, AppSync rejected it with a `ValidationException`. | `run_script` with `call_boto3(service_name="appsync", operation_name="CreateApi", params={"name": ..., "eventConfig": {"authProviders": [...], "connectionAuthModes": [...], "defaultPublishAuthModes": [...], "defaultSubscribeAuthModes": [...]}})` |
| `create_channel_namespace` | Called `CreateChannelNamespace` with `apiId`, `name`, and the optional auth modes, `codeHandlers`, `handlerConfigs`, and `tags` | `run_script` with `call_boto3(service_name="appsync", operation_name="CreateChannelNamespace", params={"apiId": ..., "name": ..., "publishAuthModes": [...], "subscribeAuthModes": [...]})` |

### Custom domain names

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `create_domain_name` | Called `CreateDomainName` with `domainName`, `certificateArn`, and the optional `description` and `tags` | `run_script` with `call_boto3(service_name="appsync", operation_name="CreateDomainName", params={"domainName": ..., "certificateArn": ..., "description": ...})`, then `AssociateApi` to attach an API, which the old server had no tool for |

Because `run_script` exposes the full AppSync API, operations the old server never had, such as `ListGraphqlApis`, `GetGraphqlApi`, `UpdateResolver`, `EvaluateCode`, `DeleteApiCache`, and `DeleteGraphqlApi`, are also available.

### Environment variables

| Old variable | Replacement |
|--------------|-------------|
| `AWS_REGION` (default `us-east-1`) | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call |
| `AWS_PROFILE` | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | Set them in the proxy's `env` block; the proxy signs requests with the standard AWS credential chain |

## What Improves

- **Schemas the old server refused.** `create_schema` searched the definition for 50 substrings meant to catch shell commands, so it refused ordinary SDL. It refused 7 of 10 sample schemas we tried, including any schema with a `Subscription` type (`sc`) or an `@aws_subscribe` directive (`su`), a `schema { }` block (`sc`), a union (`|`), a field named `description` (`sc`) or `shippingAddress` (`sh`), a `deletePost` mutation (`del`), or a `--` in a comment. AppSync accepted a schema with all of these, and `run_script` passes the definition through unchanged.
- **The rest of the AppSync API.** The old server could only create resources. Listing, updating, or deleting them, or testing resolver code with `EvaluateCode`, took another tool. With `run_script`, the same session does all of it.
- **Service role ARNs in other partitions.** `create_datasource` required `service_role_arn` to start with `arn:aws:iam::`, so it rejected role ARNs in the `aws-cn` and `aws-us-gov` partitions.

## Workflow Change

### Before (AWS AppSync Server)

1. Start the server with `--allow-write`, or every tool fails with `Operation not permitted: Server is configured in read-only mode`. All 10 tools create resources, so without the flag the server can't do anything.
2. Call a create tool. The server checks the schema, HTTP endpoint, service role ARN, and `create_graphql_api` settings before calling AppSync.
3. For `create_schema`, wait while the server polls until the schema finishes.
4. To look at, change, or delete what you created, use the console, the AWS CLI, or another tool.

### After (AWS MCP Server)

1. Ask your agent for the AppSync change. It runs the AppSync calls through `run_script` using your credentials.
2. AppSync checks the request itself and returns a `BadRequestException` or a `FAILED` schema status with the reason.
3. Whether a call succeeds is decided by IAM: your identity-based policies, permissions boundaries, and service control policies (SCPs).
4. Ask the same agent to list, update, or delete AppSync resources.

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Read-only mode by default (every tool needed `--allow-write`) | Not available | Run with credentials that allow only AppSync `Get*` and `List*` actions, or deny AppSync write actions (such as `appsync:Create*`, `appsync:Update*`, `appsync:Delete*`, and `appsync:StartSchemaCreation`) with a permissions boundary or SCP |
| API key created along with an `API_KEY` GraphQL API | Changed | Ask for the key. The agent calls `CreateApiKey` after `CreateGraphqlApi`, as in the first example. |
| Schema checks before `StartSchemaCreation` (a `type Query {` line, balanced braces, and the 50 blocked substrings) | Not available | AppSync parses the schema itself. A schema with a missing brace returns `FAILED` with "Failed to parse schema document - ensure it's a valid SDL-formatted document." in `details`. |
| `https://` required for HTTP data source endpoints | Not available | AppSync accepts `http://` endpoints. AppSync has no IAM condition key for a data source endpoint, so deny `appsync:CreateDataSource` and `appsync:UpdateDataSource` to identities that shouldn't add data sources, and use your MCP client's per-tool approval for `run_script`. |
| Rejection of `localhost`, non-public IP, and numeric-encoded HTTP endpoints | Enforced by AppSync | AppSync returns `BadRequestException` ("Invalid endpoint configuration.") for endpoints such as `https://127.0.0.1`, `https://10.0.0.1`, `https://169.254.169.254`, `https://2130706433`, `https://0x7f000001`, `https://localhost`, and `https://[::1]` |
| Value and range checks in `create_graphql_api` (name, authentication type, visibility, API type, introspection, query depth, resolver count, merged API role ARN) | Enforced by AppSync | AppSync returns `BadRequestException` with the reason, for example "Invalid queryDepthLimit given. Must fall within range 0 to 75" |
| Account IDs, ARNs, and 20-character uppercase strings masked in error messages | Changed | `run_script` returns AppSync's error code and message as AppSync sent them. The old server already returned ARNs and account IDs in its successful responses. |

## What Deprecation Means

- The final release keeps working. It prints a `FutureWarning` at startup, and its server instructions and tool descriptions are marked deprecated.
- The package stays on PyPI and gets no further updates.
- Configurations that use `awslabs.aws-appsync-mcp-server@latest` get that final release.
- The `src/aws-appsync-mcp-server` folder may later be removed from this repository, as the folders of earlier deprecated servers were.

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.aws-appsync-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.aws-appsync-mcp-server`
