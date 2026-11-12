# Migration Guide: MCP Lambda Handler to Amazon Bedrock AgentCore Gateway

This guide helps you migrate from the `awslabs.mcp-lambda-handler` library to [Amazon Bedrock AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html) with AWS Lambda targets. If you need a full custom MCP server with its own sessions, prompts, or resources, the second path is to host it on [AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html).

## Why We're Deprecating

The MCP Lambda Handler is a Python library for running an MCP server inside a Lambda function. Its `MCPLambdaHandler` class builds a tool schema from each `@mcp.tool()` function's type hints and docstring, parses the JSON-RPC body of an Amazon API Gateway or function URL event in `handle_request(event, context)`, and can keep per-session data in a pluggable store such as Amazon DynamoDB. It implements the MCP messages itself rather than through the MCP SDK, and it answers every `initialize` with protocol version `2024-11-05`. It does no authentication of its own; its README suggests putting API Gateway with a Lambda authorizer in front of the function.

AgentCore Gateway does this job as a managed service. The gateway is the MCP endpoint: it holds the tool schemas, answers `initialize`, `tools/list` and `tools/call`, checks each caller with IAM or a JSON Web Token (JWT), validates the arguments against the tool's schema, and then invokes your Lambda function with only the tool's arguments. Your function no longer handles MCP at all.

## Installing the Replacement

There's nothing to install in the function. You create a gateway, give it a service role that can invoke your function, and add the function as a Lambda target with a tool schema.

### Create the gateway and the Lambda target

1. Create a service role for the gateway. Its trust policy lets AgentCore assume it:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": { "Service": "bedrock-agentcore.amazonaws.com" },
         "Action": "sts:AssumeRole",
         "Condition": {
           "StringEquals": { "aws:SourceAccount": "<account-id>" },
           "ArnLike": { "aws:SourceArn": "arn:aws:bedrock-agentcore:us-east-1:<account-id>:gateway/my-tools-*" }
         }
       }
     ]
   }
   ```

   Give it `lambda:InvokeFunction` on your function:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": "lambda:InvokeFunction",
         "Resource": "arn:aws:lambda:us-east-1:<account-id>:function:<function-name>"
       }
     ]
   }
   ```

   The AgentCore console and the AgentCore CLI can create this role for you. See [Set up permissions for AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-prerequisites-permissions.html).

2. Create the gateway with IAM inbound authorization, then add the Lambda target with your tool definitions:

   ```python
   import boto3

   control = boto3.client("bedrock-agentcore-control", region_name="us-east-1")

   gateway = control.create_gateway(
       name="my-tools",
       roleArn="arn:aws:iam::<account-id>:role/<gateway-service-role>",
       protocolType="MCP",
       authorizerType="AWS_IAM",
   )
   # Wait until control.get_gateway(gatewayIdentifier=gateway["gatewayId"])["status"] == "READY"

   control.create_gateway_target(
       gatewayIdentifier=gateway["gatewayId"],
       name="my-tools",
       targetConfiguration={
           "mcp": {
               "lambda": {
                   "lambdaArn": "arn:aws:lambda:us-east-1:<account-id>:function:<function-name>",
                   "toolSchema": {"inlinePayload": [add_two_numbers_definition]},
               }
           }
       },
       credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
   )
   print(gateway["gatewayUrl"])
   ```

   `add_two_numbers_definition` is the tool definition shown in the next section. You can also upload the definitions to Amazon S3 and pass `toolSchema={"s3": {...}}`.

### Configuration

With IAM inbound authorization, MCP clients connect through the [MCP Proxy for AWS](https://github.com/aws/mcp-proxy-for-aws), which signs each request with your AWS credentials:

```json
{
  "mcpServers": {
    "my-tools": {
      "command": "uvx",
      "args": [
        "mcp-proxy-for-aws-cli@latest",
        "https://<gateway-id>.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
        "--region",
        "us-east-1"
      ]
    }
  }
}
```

To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

The library needed no IAM permissions of its own beyond its session store: with `DynamoDBSessionStore`, the function's execution role needed `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem` and `dynamodb:DeleteItem` on the session table. With the gateway, callers need `bedrock-agentcore:InvokeGateway` on the gateway's ARN, the gateway's service role needs `lambda:InvokeFunction` on the function, and the function's execution role keeps only what your tools need. See [Set up inbound authorization for your gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html).

### Installing the Agent Skills

In Claude Code, install the `aws-agents` plugin from the Agent Toolkit for AWS:

```text
/plugin install aws-agents@claude-plugins-official
```

Its [`agents-connect`](https://github.com/aws/agent-toolkit-for-aws/tree/main/plugins/aws-agents/skills/agents-connect) skill covers adding a Lambda function as a gateway target with a tool schema file. It doesn't show how the handler reads and strips the tool name, so use the handler in the next section. The [`agents-get-started`](https://github.com/aws/agent-toolkit-for-aws/tree/main/plugins/aws-agents/skills/agents-get-started) skill covers creating a project with the MCP protocol on AgentCore Runtime.

## Concept-by-Concept Migration

| Library concept | What it did | Replacement |
|-----------------|-------------|-------------|
| `MCPLambdaHandler(name, version, session_store)` | Held the tools, resources and session store, and answered `initialize` with this name and version and protocol version `2024-11-05` | The gateway. It answers `initialize` with the gateway's name and negotiates the protocol version; the `supportedVersions` field of its MCP protocol configuration sets which versions it accepts |
| `@mcp.tool()` and type hints | Built `inputSchema` from the hints (`int` to `integer`, `float` to `number`, `bool`, `str`, an `Enum` to a string `enum`, `List` to `array`, `Dict` to `object` with `additionalProperties`, `Optional` or `Union` to its first non-`None` type, anything else to `string`), took the first docstring paragraph as the description and the `Args:` lines as property descriptions, marked every type-hinted parameter required (even ones with defaults), and left parameters without a type hint out of the schema | A tool definition in the target's `toolSchema`: `name`, `description`, `inputSchema` and an optional `outputSchema`, written as JSON. See [Lambda function tool schema](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-add-target-lambda.html) |
| `handle_request(event, context)` | Checked that `Content-Type` was exactly `application/json`, parsed the JSON-RPC body, handled `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read` and `ping`, converted string arguments to `Enum` members, and wrapped the return value as text (or `bytes` as a base64 image) | A plain handler. The gateway passes the tool's arguments as `event` and the tool name in `context.client_context.custom["bedrockAgentCoreToolName"]`, prefixed with the target name and three underscores. Dispatch on the name and return a JSON-serializable value; the gateway sends it to the client as a text item |
| `SessionStore`, `DynamoDBSessionStore`, `NoOpSessionStore`, `get_session()`, `set_session()`, `update_session()` | `initialize` created a session ID (with `DynamoDBSessionStore`, an item with a 24-hour expiry) and returned it in `MCP-Session-Id`; with any store other than `NoOpSessionStore`, later requests had to carry it, and tools read and wrote per-session data | [Gateway sessions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-sessions.html), turned on with `sessionConfiguration` (900 to 28,800 seconds, 3,600 by default) and bound to the caller's IAM principal or JWT `sub`. The gateway doesn't pass the session ID to the function, so keep tool state in your own table keyed by an ID that a tool returns, or host an MCP server on AgentCore Runtime |
| `add_resource()`, `@mcp.resource()`, `FileResource`, `StaticResource` | Served resources through `resources/list` and `resources/read` | A Lambda target describes tools only. Return the content from a tool, or serve resources from an MCP server on AgentCore Runtime |
| API Gateway or a function URL in front of the function | Exposed the function as the MCP HTTP endpoint | The gateway URL, `https://<gateway-id>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp`, is the endpoint; the function needs no URL of its own |
| A Lambda authorizer | Checked the caller's bearer token before the function ran | Gateway inbound authorization: `AWS_IAM` (SigV4 callers with `bedrock-agentcore:InvokeGateway`), `CUSTOM_JWT` (a discovery URL plus allowed audiences, clients, scopes or custom claims), or `AUTHENTICATE_ONLY` or `NONE` with a [REQUEST interceptor](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-interceptors.html) Lambda function that runs your own checks |

### A tool, before and after

Before, with the library:

```python
from awslabs.mcp_lambda_handler import MCPLambdaHandler

mcp = MCPLambdaHandler(name="my-tools", version="1.0.0")


@mcp.tool()
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: The first number
        b: The second number
    """
    return a + b


def lambda_handler(event, context):
    return mcp.handle_request(event, context)
```

After, the tool definition you give the gateway (the same schema the library generated for the function above):

```json
{
  "name": "add_two_numbers",
  "description": "Add two numbers together.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "a": { "type": "integer", "description": "The first number" },
      "b": { "type": "integer", "description": "The second number" }
    },
    "required": ["a", "b"]
  }
}
```

And the function:

```python
def add_two_numbers(a: int, b: int) -> int:
    return a + b


TOOLS = {"add_two_numbers": add_two_numbers}


def lambda_handler(event, context):
    # The gateway names the tool <target name>___<tool name>
    full_name = context.client_context.custom["bedrockAgentCoreToolName"]
    tool_name = full_name.split("___", 1)[-1]
    tool = TOOLS[tool_name]
    return tool(**event)
```

Clients see the tool as `my-tools___add_two_numbers`, where `my-tools` is the target's name. See [Understand how AgentCore Gateway tools are named](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-tool-naming.html).

### When you need a full MCP server

If your server depends on per-session state, resources, prompts, or image content, host it on AgentCore Runtime instead. Runtime runs an MCP server written with the MCP SDK (for example `FastMCP`) over streamable HTTP at `/mcp` on port 8000, accepts SigV4 or OAuth callers, and supports stateful mode (`stateless_http=False`) for elicitation and sampling. You can call the Runtime endpoint directly or add it to a gateway as an MCP server target. See [Deploy MCP servers in AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html) and the [MCP protocol contract](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp-protocol-contract.html).

## What Improves

- **Argument validation.** The gateway checks `tools/call` arguments against the tool's `inputSchema` before it invokes the function. Strings sent for integer parameters came back as `isError: true` with "Field '/a' has invalid type: string found, integer expected", and the function wasn't invoked. The library passed the strings through, so `add_two_numbers("2", "3")` returned `23`.
- **Readable tool errors.** The gateway reports tool failures as an MCP result with `isError: true`. The library returned HTTP 500 with a JSON-RPC error, and the MCP Proxy for AWS passed that to the agent as "Server error '500 Internal Server Error'", without the missing-argument message. Through the gateway, the agent got "Missing required field(s): 'b'".
- **No MCP code in the function.** The function receives only the tool's arguments, so it no longer parses events, checks headers, or builds JSON-RPC responses.
- **Sessions bound to the caller.** With sessions on, the gateway issues the `Mcp-Session-Id`, rejects requests without it (HTTP 400) and unknown IDs (HTTP 404), and binds each session to the caller's identity. The library's `NoOpSessionStore`, its default, accepted any session ID.

## Workflow Change

### Before (MCP Lambda Handler)

1. Write tools as decorated functions and package the library with the function
2. Put the function behind API Gateway or a function URL, add a Lambda authorizer, and create a DynamoDB table if you need sessions
3. Point MCP clients at that URL

### After (AgentCore Gateway)

1. Write a plain Lambda handler that dispatches on the tool name, and write the tool definitions as JSON
2. Create a gateway with IAM or JWT inbound authorization and add the function as a Lambda target
3. Point MCP clients at the gateway URL, through the MCP Proxy for AWS for IAM or with a bearer token for JWT

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Tool schemas generated from type hints and docstrings | Not available | Write the tool definitions as JSON next to the function and pass them inline or from Amazon S3 |
| `Enum` parameters as a string `enum`, converted to `Enum` members on call | Not available | The gateway's schema type has no `enum` field; list the allowed values in the property's `description` and check them in the handler |
| `Dict` parameters as `object` with `additionalProperties` | Not available | The gateway's schema type has no `additionalProperties` field; declare the keys under `properties`, or take the value as a JSON string |
| Tool names as written in code | Changed | Clients see `<target name>___<tool name>`; pick a short target name and update any prompts that name the tools |
| Per-session data in tools (`get_session`, `set_session`, `update_session`) | Not available | Keep state in your own DynamoDB table keyed by an ID a tool returns and the client passes back, or host the server on AgentCore Runtime in stateful mode |
| Sessions lasting 24 hours (`DynamoDBSessionStore`) | Changed | Gateway sessions last at most 28,800 seconds (8 hours) from `initialize`; clients start a new session after that |
| Resources (`resources/list`, `resources/read`) | Not available | Return the content from a tool, or serve resources from an MCP server on AgentCore Runtime |
| Image content from a `bytes` return value | Not available | The gateway returned the function's value as one text item; return an Amazon S3 presigned URL or base64 text, or use AgentCore Runtime |
| Exception text returned to the client | Changed | An uncaught exception comes back as `isError: true` with "An internal error occurred. Please retry later."; catch expected errors and return a value that describes them, and read the full error in the function's Amazon CloudWatch logs |
| Runs in any Region where Lambda runs | Changed | AgentCore Gateway is offered in fewer Regions; see [Supported AWS Regions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-regions.html) and put the gateway and function in one of them |

## What Deprecation Means

- The final release keeps working. Importing `awslabs.mcp_lambda_handler` emits a `DeprecationWarning` that names the replacement and this guide. Python shows it by default when the import runs in `__main__`, such as a script you run directly, and pytest lists it in its warnings summary. Code imported as a module, such as a Lambda function handler, shows it only with warnings turned on, for example with `PYTHONWARNINGS=default`.
- The package stays on PyPI and gets no further updates.
- Functions that install `awslabs.mcp-lambda-handler` without a version pin get that final release.
- The `src/mcp-lambda-handler` folder may later be removed from this repository, as the folders of earlier deprecated servers were.

## Removing the Old Library

Once you've verified the replacement meets your needs:

1. Remove `awslabs.mcp-lambda-handler` from your function's dependencies and redeploy the plain handler
2. Uninstall the package: `pip uninstall awslabs.mcp-lambda-handler`
3. Delete the API Gateway stage or function URL, the Lambda authorizer, and the DynamoDB session table once no client uses them
