# Migration Guide: Lambda Tool MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.lambda-tool-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The Lambda Tool MCP Server turned your AWS Lambda functions into MCP tools. At startup, it listed the functions in one Region and kept the ones that matched a name prefix or a list of names and, if a tag was set, had that tag. It then registered one tool for each function it kept. Each tool's description was the function's description, followed by an input schema from the Amazon EventBridge Schema Registry when the function had a schema tag. Calling a tool invoked the function and waited for its response, with the tool's `parameters` object as the event.

There are two replacements, depending on how you used the server:

- **To let an agent call your functions**, use the AWS MCP Server. Its `run_script` tool executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. It makes the same `ListFunctions`, `ListTags`, `DescribeSchema`, and `Invoke` calls the server made, and it returns the function's response, including the error message when the function fails.
- **To publish selected functions as named MCP tools with input schemas**, use [Amazon Bedrock AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-add-target-lambda.html) with a Lambda target. You define each tool's name, description, and input schema once, and an MCP client that signs its requests with IAM credentials allowed to call the gateway can list and call the tools. The gateway publishes the schema to clients and rejects a call that's missing a required argument before it invokes the function.

No Agent Skill covers calling functions through `run_script`, so the first path has no skill to install. For the gateway path, the [`agents-connect`](https://github.com/aws/agent-toolkit-for-aws/tree/main/plugins/aws-agents/skills/agents-connect) skill in the Agent Toolkit's `aws-agents` plugin walks through adding a Lambda function as a gateway target.

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

Set `AWS_REGION` to the Region of your Lambda functions. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

Your identity needs the same permissions the old server needed: `lambda:ListFunctions`, `lambda:InvokeFunction` on the functions the agent may call, `lambda:ListTags` if you filtered by tag or used schema tags, and `schemas:DescribeSchema` if you used schema tags. To find tagged functions in one call with `GetResources`, as shown in [Server behaviors](#server-behaviors), it also needs `tag:GetResources`.

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

### Publishing functions as MCP tools with AgentCore Gateway

Skip this section if your agent only needs to call your functions through `run_script`.

1. Create a gateway service role that `bedrock-agentcore.amazonaws.com` can assume and that allows `lambda:InvokeFunction` on each function you publish. [Set up permissions for AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-prerequisites-permissions.html) has the trust policy and the permissions policy.

2. Create a gateway that uses IAM for inbound authorization:

   ```bash
   aws bedrock-agentcore-control create-gateway \
     --name lambda-tools \
     --role-arn arn:aws:iam::123456789012:role/LambdaToolsGatewayRole \
     --protocol-type MCP \
     --authorizer-type AWS_IAM
   ```

   The response has the `gatewayId` and the `gatewayUrl`. With `AWS_IAM`, a caller needs `bedrock-agentcore:InvokeGateway` on the gateway, much as a caller of the old server needed `lambda:InvokeFunction`. The other inbound options are a JSON Web Token from your identity provider (`CUSTOM_JWT`) and two types that leave the decision to the target, a policy engine, or an interceptor (`AUTHENTICATE_ONLY` and `NONE`). See [Set up inbound authorization for your gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html).

3. Describe each tool in a target configuration file. For example, `target.json` for a function like the old server's `customer-info-from-id` sample:

   ```json
   {
     "mcp": {
       "lambda": {
         "lambdaArn": "arn:aws:lambda:us-east-1:123456789012:function:customer-info-from-id",
         "toolSchema": {
           "inlinePayload": [
             {
               "name": "customer_info_from_id",
               "description": "Retrieve customer status on the CRM system based on a customer ID",
               "inputSchema": {
                 "type": "object",
                 "properties": {
                   "customerId": { "type": "string", "description": "The customer ID" }
                 },
                 "required": ["customerId"]
               }
             }
           ]
         }
       }
     }
   }
   ```

   Then add the target:

   ```bash
   aws bedrock-agentcore-control create-gateway-target \
     --gateway-identifier <gateway-id> \
     --name crm \
     --target-configuration file://target.json \
     --credential-provider-configurations '[{"credentialProviderType": "GATEWAY_IAM_ROLE"}]'
   ```

   The gateway passes the tool's arguments to the function as the event, the same object the old server sent as `parameters`, so a function written for the old server reads its input unchanged. MCP clients see the tool as `crm___customer_info_from_id`: the target name, three underscores, and the tool name. One function can back several tools in the same target; it reads the called tool's name from `context.client_context.custom["bedrockAgentCoreToolName"]`. See [AWS Lambda function targets](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-add-target-lambda.html) and [Understand how AgentCore Gateway tools are named](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-tool-naming.html).

4. Add the gateway to your MCP client, using the `gatewayUrl` from step 2. The MCP Proxy for AWS signs each request with your credentials:

   ```json
   {
     "mcpServers": {
       "lambda-tools": {
         "command": "uvx",
         "args": [
           "mcp-proxy-for-aws-cli@latest",
           "https://<gateway-id>.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
           "--service",
           "bedrock-agentcore",
           "--region",
           "us-east-1"
         ]
       }
     }
   }
   ```

## Tool-by-Tool Migration

The Lambda Tool server didn't have a fixed set of tools. It registered one tool per selected function at startup, and each tool invoked its function. With the AWS MCP Server, ask your agent to call the function by name, and it makes the same call through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. For example, the agent might run:

```python
resp = await call_boto3(
    service_name="lambda",
    operation_name="Invoke",
    region_name="us-east-1",
    params={
        "FunctionName": "customer-info-from-id",
        "Payload": json.dumps({"customerId": "123"}),
    },
)
result = {
    "status": resp["StatusCode"],
    "error": resp.get("FunctionError"),
    "payload": json.loads(resp["Payload"]),
}
result
```

`Payload` is a JSON string in both directions. The old server built it from the tool's `parameters` object, and `call_boto3` returns the function's response as a string, which `json.loads` turns back into an object. When the function raises an error, `FunctionError` is set and `Payload` holds the `errorMessage`, `errorType`, and `stackTrace`.

To see the functions the old server would have exposed, the agent can list the functions, read their tags, and fetch their schemas in one script:

```python
listed = await call_boto3(service_name="lambda", operation_name="ListFunctions", region_name="us-east-1")
functions = []
for f in listed["Functions"]:
    if not f["FunctionName"].startswith("crm-"):
        continue
    entry = {"name": f["FunctionName"], "description": f["Description"]}
    tags = await call_boto3(
        service_name="lambda",
        operation_name="ListTags",
        region_name="us-east-1",
        params={"Resource": f["FunctionArn"]},
    )
    schema_arn = tags["Tags"].get("tool-input-schema-arn")
    if schema_arn:
        registry, schema = schema_arn.split(":")[5].split("/")[1:3]
        s = await call_boto3(
            service_name="schemas",
            operation_name="DescribeSchema",
            region_name="us-east-1",
            params={"RegistryName": registry, "SchemaName": schema},
        )
        entry["input_schema"] = json.loads(s["Content"])
    functions.append(entry)
result = {"functions": functions}
result
```

`call_boto3` paginates automatically, so `ListFunctions` needs only one call for up to 1,000 functions.

### Server behaviors

| Server behavior | API call(s) | With the AWS MCP Server | With AgentCore Gateway |
|-----------------|-------------|-------------------------|------------------------|
| `<function_name>(parameters)`: one tool per selected function | `Invoke` with `InvocationType="RequestResponse"` and `Payload` set to the JSON of `parameters` | `run_script` with `call_boto3(service_name="lambda", operation_name="Invoke", params={"FunctionName": ..., "Payload": json.dumps(...)})`. `RequestResponse` is the default invocation type. | A tool definition in the target's `inlinePayload`. The gateway invokes the function with the tool's arguments as the event. |
| Name each tool after its function: remove `FUNCTION_PREFIX`, replace every character other than letters, digits, and underscores with `_`, and add `_` before a leading digit | None | The agent passes the function's real name as `FunctionName` | You choose `name` in the tool definition, and clients see `<target>___<name>` |
| List the functions at startup | `ListFunctions`, every page | `run_script` with `call_boto3(service_name="lambda", operation_name="ListFunctions")` | None. You choose the functions when you add targets. |
| Keep functions by name prefix (`FUNCTION_PREFIX`) or by a list of names (`FUNCTION_LIST`) | None. The server filtered the `ListFunctions` results itself, and kept a function that matched either one. | Filter the `ListFunctions` results in the script, as in the example above | Add a target only for the functions you want to publish |
| Keep functions that have a tag (`FUNCTION_TAG_KEY` and `FUNCTION_TAG_VALUE`) | `ListTags` once for each function that passed the name filter | `run_script` with `call_boto3(service_name="resourcegroupstaggingapi", operation_name="GetResources", params={"ResourceTypeFilters": ["lambda:function"], "TagFilters": [{"Key": ..., "Values": [...]}]})`, which returns every tagged function in one call | Add a target only for the functions you want to publish |
| Use the function's description as the tool description | `Description` from `ListFunctions`. A function without a description gave the tool an empty description. | Read `Description` from the `ListFunctions` results | `description` in the tool definition, which is required |
| Add the input schema to the tool description (`FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY`) | `ListTags`, then EventBridge Schemas `DescribeSchema` for the latest version | `run_script` that reads the schema ARN from the tag, splits it into the registry name and the schema name, and calls `call_boto3(service_name="schemas", operation_name="DescribeSchema", params={"RegistryName": ..., "SchemaName": ...})`. The schema is in the `Content` field. | Copy the schema into `inputSchema`. A tool schema accepts only `type`, `properties`, `required`, `items`, and `description`, so remove `$schema`, `title`, and keywords such as `format`, `pattern`, `enum`, and `additionalProperties`. |
| Return the function's response | `Payload`, returned as `Function <name> returned: <JSON>`, or as `Function <name> returned payload: b'<bytes>'` when it wasn't JSON | `json.loads(resp["Payload"])` | The function's JSON response is the tool result |
| Report a function error | Returned `Function <name> returned with error: Unhandled` as a normal tool result, without the error payload | `FunctionError` is set, and `Payload` holds the error message, type, and stack trace | The tool result is an error with a generic message. To return the function's error payload instead, set the gateway's `exceptionLevel` to `DEBUG` ([CreateGateway](https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_CreateGateway.html)), or catch errors in the function and return them as JSON. |

### Environment variables

| Old variable | What it did | Replacement |
|--------------|-------------|-------------|
| `AWS_PROFILE` | Named the profile for every call. When it was unset, the server still asked for a profile named `default`. | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |
| `AWS_REGION` | Chose the Region for every call. The default was `us-east-1`. | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call |
| `FUNCTION_PREFIX` | Kept the functions whose names start with the prefix, and removed the prefix from each tool name | Name the prefix in your request, for example "list my Lambda functions whose names start with `crm-`", or add a gateway target for each function |
| `FUNCTION_LIST` | Kept the functions named in this comma-separated list | Name the functions in your request or in your project's agent instructions file, such as `AGENTS.md`, or add a gateway target for each function |
| `FUNCTION_TAG_KEY` and `FUNCTION_TAG_VALUE` | Kept the functions that have this tag. When only one of the two was set, the server registered no tools and logged a warning. | Ask the agent to find the functions by tag with `GetResources`, and limit IAM to the tag as described in [Summary of Gaps](#summary-of-gaps) |
| `FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY` | Named the tag whose value, on each function, is the ARN of an EventBridge Schema Registry schema | Tell the agent the tag key, and ask it to read the schema with `DescribeSchema` before it builds the payload. For a gateway, copy the schema into the tool's `inputSchema`. |

## What Improves

- **Error messages.** When a function failed, the old server returned `Function <name> returned with error: Unhandled` as a normal tool result and dropped the error payload. `Invoke` through `run_script` returns `FunctionError` and the payload with the function's `errorMessage`, `errorType`, and `stackTrace`, so the agent can see why the call failed.
- **Arguments checked against the schema.** The old server put the registry schema into the tool description as text. The tool's input schema was a single free-form `parameters` object, so nothing checked the arguments. A gateway publishes the schema as the tool's input schema, so the agent passes named arguments, and a call that's missing a required field fails with `Missing required field(s)` before the function runs.
- **New functions without a restart.** The old server registered its tools once, when it started, so a new or renamed function didn't appear until you restarted it. `run_script` lists the functions each time the agent asks.
- **Tag lookups in one call.** The old tag filter called `ListTags` once per function. With no prefix or list set, it checked every function in the Region before the server finished starting. `GetResources` with a tag filter returns the tagged functions in one call.
- **Credentials without a `default` profile.** The old server always passed a profile name to the AWS SDK, `default` when `AWS_PROFILE` was unset. Without a `[default]` profile in the AWS config file, as in the README's Docker setup, it stopped at startup with `ProfileNotFound`. With a `[default]` profile, it ignored credentials set in environment variables such as `AWS_ACCESS_KEY_ID`. The MCP Proxy for AWS doesn't need a profile, and without one it signs with the credentials the AWS SDK finds, such as an EC2 instance role.
- **Every function reachable.** Two functions whose names became the same tool name, such as `crm-lookup` and `crm_lookup`, produced one tool, and the server dropped the second with a `Tool already exists` warning. `run_script` calls each function by its real name, and in a gateway you choose each tool name.

## Workflow Change

### Before (Lambda Tool Server)

1. Set `FUNCTION_PREFIX`, `FUNCTION_LIST`, or the two tag variables to choose which functions the server exposes
2. At startup, the server registers one tool for each matching function, with the function's description and, if the function has a schema tag, its input schema in the tool description
3. The agent calls a tool with a `parameters` object, and the server returns the function's response, or `Unhandled` if the function failed

### After (AWS MCP Server)

1. Ask your agent to call a function by name, or to list the functions that match a prefix or a tag
2. The agent reads the function's description from `ListFunctions` and, if the function has a schema tag, its schema from `DescribeSchema`
3. The agent invokes the function with `Invoke` and reads the response or the error from `Payload`
4. IAM decides whether each call succeeds, based on your identity-based policies, permissions boundaries, and service control policies (SCPs)

### After (AgentCore Gateway)

1. Create a gateway and add a Lambda target with a tool definition for each function you publish
2. Your MCP client lists the gateway's tools, each named `<target>___<tool>` with its input schema
3. The agent calls a tool with named arguments; the gateway checks for the required ones, invokes the function, and returns its response

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| A tool for each selected function, built at startup from the function's description and schema tag | Not available | With the AWS MCP Server, ask the agent to list and describe the functions, as in the discovery script above. With a gateway, write a tool definition for each function; the discovery script's output has the names, descriptions, and schemas you need. |
| An agent that could only invoke the selected functions, while each function's own IAM role reached other AWS services | Not available in `run_script`, which can call any AWS API your credentials allow | Publish the functions through a gateway: the client needs only `bedrock-agentcore:InvokeGateway`, and only the gateway's role can invoke the functions. Or run the AWS MCP Server with credentials that allow `lambda:InvokeFunction` only on those functions' ARNs, or only on functions with a tag through an `aws:ResourceTag` condition. See [Using attribute-based access control in Lambda](https://docs.aws.amazon.com/lambda/latest/dg/attribute-based-access-control.html). |
| Registry schemas used as they are, including `format`, `pattern`, `enum`, and `additionalProperties` | Not available in a gateway tool schema | Keep `type`, `properties`, `required`, `items`, and `description`. Describe the other constraints in each property's `description`, and check them in the function. |
| Tool names without a prefix | Changed | Gateway tool names start with the target name and three underscores. A function that reads the tool name from its context needs to remove that prefix. |
| Function errors returned as tool text | Changed | In `run_script`, the `Invoke` call succeeds even when the function fails, and `api_calls` reports it as `success`. Check `FunctionError` before you read `Payload` as a result. A gateway marks the tool result as an error. |

## What Deprecation Means

- The final release keeps working. It prints a `FutureWarning` at startup, and its server instructions and tool descriptions are marked deprecated.
- The package stays on PyPI and gets no further updates.
- Configurations that use `awslabs.lambda-tool-mcp-server@latest` get that final release.
- The `src/lambda-tool-mcp-server` folder may later be removed from this repository, as the folders of earlier deprecated servers were.

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.lambda-tool-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.lambda-tool-mcp-server`
3. If you built the Docker image, remove it: `docker rmi awslabs/lambda-tool-mcp-server`
