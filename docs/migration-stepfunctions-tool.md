# Migration Guide: AWS Step Functions Tool MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.stepfunctions-tool-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The Step Functions Tool server had no fixed tool list. At startup it listed your state machines, kept the ones that matched its name and tag filters, and registered one MCP tool per state machine. Each tool's description came from the state machine's `description`, the `Comment` in its Amazon States Language (ASL) definition, and, optionally, an input schema from the Amazon EventBridge Schema Registry. Each tool took a single `parameters` object, started an execution with it as the input, and returned the execution's output. The AWS MCP Server makes the same calls through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. It discovers state machines when the agent asks rather than once at startup, and it reaches the rest of the Step Functions API, which this server didn't have.

The [`aws-step-functions`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/specialized-skills/serverless-skills/aws-step-functions) Agent Skill covers authoring and debugging state machines: ASL and JSONata, error handling, service integrations, choosing between Standard and Express workflows, and testing with the TestState API. This server didn't author or change state machines.

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

Set `AWS_REGION` to the Region that contains your state machines. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

### Installing the Agent Skills

```bash
npx skills add aws/agent-toolkit-for-aws/skills
```

This installs the `aws-step-functions` skill along with the other skills. An agent connected to the AWS MCP Server can also load it with the server's `retrieve_skill` tool.

### Permissions

Your identity needs the permissions the old server used:

- Discovery: `states:ListStateMachines` and `states:DescribeStateMachine`
- Tag filters and the schema tag: `states:ListTagsForResource`
- Input schemas: `schemas:DescribeSchema`
- Standard workflows: `states:StartExecution` and `states:DescribeExecution`
- Express workflows: `states:StartSyncExecution`

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

With the AWS MCP Server, ask your agent to find or run a state machine and it makes the equivalent calls through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. `call_boto3` pages list operations automatically, so each API is called once. Modules such as `asyncio` and `json` are already imported, and the script returns the value of `result` as its final expression.

### Tool registration (state machine discovery)

The old server did this once, at startup:

1. Called `ListStateMachines` once, without a `nextToken`, so it saw only the first page (100 state machines by default).
2. Kept state machines whose names start with `STATE_MACHINE_PREFIX` or appear in the comma-separated `STATE_MACHINE_LIST`. If both were empty, it kept all of them.
3. If both `STATE_MACHINE_TAG_KEY` and `STATE_MACHINE_TAG_VALUE` were set, called `ListTagsForResource` on each state machine and kept those with that exact tag. If only one of the two was set, it registered no tools.
4. Called `DescribeStateMachine` on each and built the tool description from `description` plus `Workflow Description:` and the definition's `Comment`. If the call failed, the description was `AWS Step Functions state machine: <name>`.
5. Registered one MCP tool per state machine. The tool name was the state machine name with `STATE_MACHINE_PREFIX` removed and characters other than letters, digits, and `_` replaced by `_`.

To list state machines with the same information, the agent might run:

```python
listing = await call_boto3(
    service_name="stepfunctions",
    operation_name="ListStateMachines",
)
machines = [sm for sm in listing["stateMachines"] if sm["name"].startswith("my-prefix-")]


async def inspect(sm):
    arn = sm["stateMachineArn"]
    details, tag_list = await asyncio.gather(
        call_boto3(service_name="stepfunctions", operation_name="DescribeStateMachine", params={"stateMachineArn": arn}),
        call_boto3(service_name="stepfunctions", operation_name="ListTagsForResource", params={"resourceArn": arn}),
    )
    return {
        "name": sm["name"],
        "arn": arn,
        "type": sm["type"],
        "description": details.get("description"),
        "comment": json.loads(details["definition"]).get("Comment"),
        "tags": {t["key"]: t["value"] for t in tag_list["tags"]},
    }


inspected = await asyncio.gather(*[inspect(sm) for sm in machines], return_exceptions=True)
result = {"stateMachines": [r if not isinstance(r, Exception) else str(r) for r in inspected]}
result
```

### Input schemas (`STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY`)

**Old server:** When `STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY` was set, read that tag's value on each state machine as a schema ARN, called the EventBridge Schemas `DescribeSchema` operation on the latest version, and appended the schema `Content` to the tool description under `Input Schema:`. If the tag was missing or the call failed, the description had no schema.

**AWS MCP Server:** Read the same tag with `ListTagsForResource`, as in the example above, and fetch the schema. The ARN format is `arn:aws:schemas:<region>:<account>:schema/<registry-name>/<schema-name>`:

```python
schema_arn = "arn:aws:schemas:us-east-1:111122223333:schema/my-registry/my-schema"
registry_name, schema_name = schema_arn.split(":")[5].split("/")[1:3]
schema = await call_boto3(
    service_name="schemas",
    operation_name="DescribeSchema",
    params={"RegistryName": registry_name, "SchemaName": schema_name},
    region_name=schema_arn.split(":")[3],
)
result = {"content": schema["Content"]}
result
```

### Generated state machine tools

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `<state_machine_name>(parameters)` for a `STANDARD` state machine | Called `StartExecution` with `parameters` as the JSON input, then called `DescribeExecution` every second, with no time limit, until the status was `SUCCEEDED` (returned `output`) or `FAILED`, `TIMED_OUT`, or `ABORTED` (returned the status, `error`, and `cause`) | `StartExecution`, then `DescribeExecution` on the returned `executionArn`, as in the example below |
| `<state_machine_name>(parameters)` for an `EXPRESS` state machine | Called `StartSyncExecution` with `parameters` as the JSON input, which waits for the execution to finish, and returned `output` when the status was `SUCCEEDED`, or the status, `error`, and `cause` otherwise | `StartSyncExecution`, as in the example below |

The old server picked the API from the `type` field that `ListStateMachines` returns. [`StartSyncExecution`](https://docs.aws.amazon.com/step-functions/latest/apireference/API_StartSyncExecution.html) works only for Express state machines. For a Standard workflow, `StartExecution` returns only the execution ARN and start date, so the result comes from [`DescribeExecution`](https://docs.aws.amazon.com/step-functions/latest/apireference/API_DescribeExecution.html). `DescribeExecution` doesn't support Express executions unless a Map Run dispatched them. `StartSyncExecution` returns HTTP 200 even when the execution fails, so always check `status`.

To run a state machine with the same dispatch, the agent might run:

```python
arn = "arn:aws:states:us-east-1:111122223333:stateMachine:my-state-machine"
payload = json.dumps({"customerId": "12345"})

machine = await call_boto3(
    service_name="stepfunctions",
    operation_name="DescribeStateMachine",
    params={"stateMachineArn": arn},
)

if machine["type"] == "EXPRESS":
    execution = await call_boto3(
        service_name="stepfunctions",
        operation_name="StartSyncExecution",
        params={"stateMachineArn": arn, "input": payload},
    )
else:
    started = await call_boto3(
        service_name="stepfunctions",
        operation_name="StartExecution",
        params={"stateMachineArn": arn, "input": payload},
    )
    # Short, bounded status check. If the execution is still RUNNING afterwards,
    # check it again with DescribeExecution in a later run_script call.
    for _ in range(10):
        execution = await call_boto3(
            service_name="stepfunctions",
            operation_name="DescribeExecution",
            params={"executionArn": started["executionArn"]},
        )
        if execution["status"] != "RUNNING":
            break
        await asyncio.sleep(1)

result = {
    "executionArn": execution.get("executionArn"),
    "status": execution["status"],
    "output": execution.get("output"),
    "error": execution.get("error"),
    "cause": execution.get("cause"),
}
result
```

A Standard execution can run for longer than a single `run_script` call allows. In that case, start the execution in one call, keep the returned `executionArn`, and check it with `DescribeExecution` in later `run_script` calls.

### Environment variables

| Old variable | Replacement |
|--------------|-------------|
| `AWS_REGION` (default `us-east-1`) | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call |
| `AWS_PROFILE` | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |
| `STATE_MACHINE_PREFIX` and `STATE_MACHINE_LIST` | Name the state machines, or the prefix, in your request, and the agent filters the `ListStateMachines` result. To enforce the limit, scope the IAM permissions (see [Summary of Gaps](#summary-of-gaps)). |
| `STATE_MACHINE_TAG_KEY` and `STATE_MACHINE_TAG_VALUE` | The agent filters on the tags from `ListTagsForResource`. To enforce the limit, use an `aws:ResourceTag` condition in IAM. |
| `STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY` | Tell the agent the tag key, and it fetches the schema as in [Input schemas](#input-schemas-state_machine_input_schema_arn_tag_key) |

## What Improves

- **Every state machine, not only the first page.** The old server called `ListStateMachines` once and never followed `nextToken`, so in an account with more than 100 state machines, the rest never became tools, whatever the filters. `call_boto3` follows the pagination tokens, up to 1,000 results per call; a `nextToken` left in the response means there are more.
- **New and changed state machines without a restart.** The old server read the list, descriptions, tags, and schemas once at startup. A state machine created, updated, or retagged afterward wasn't visible until the server restarted. `run_script` reads them when the agent asks.
- **Errors reach the agent.** If `ListStateMachines` failed at startup, for example because of a missing permission or the wrong Region, the server logged the error and started with no tools, and the agent had no way to tell why. `run_script` returns the service's error code and message.
- **Long Standard executions don't hold the tool call open.** The old tool polled `DescribeExecution` every second until the execution finished, with no time limit, and Standard executions can run for up to a year. With `run_script`, the agent starts the execution and checks it later by its ARN.
- **No name collisions.** Two state machines whose names differ only in characters the server replaced with `_`, such as `orders-v1` and `orders_v1`, mapped to the same tool name, and only the first one was registered. `run_script` addresses each state machine by its ARN.
- **The rest of the Step Functions API.** The old tools couldn't name an execution, pass an X-Ray trace header, stop or redrive an execution, list earlier executions, or read an execution's history. `run_script` reaches `StopExecution`, `RedriveExecution`, `ListExecutions`, `GetExecutionHistory`, and every other Step Functions operation your credentials allow.

## Workflow Change

### Before (AWS Step Functions Tool MCP Server)

1. Set `STATE_MACHINE_PREFIX`, `STATE_MACHINE_LIST`, and optionally the tag filter and the schema tag key, then start the server.
2. Restart the server to pick up new or changed state machines.
3. The agent calls a generated tool, such as `GetCustomerStatus`, with a `parameters` object and waits for the execution to finish.

### After (AWS MCP Server)

1. The agent uses `run_script` to list state machines and read their descriptions, definitions, tags, and schemas.
2. The agent uses `run_script` to start the execution with the API that matches the state machine type, and reads the result, or checks a long Standard execution again later.
3. New and changed state machines are visible right away, with no restart.

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| One named MCP tool per state machine | Not available | The agent finds state machines with `ListStateMachines` and `DescribeStateMachine` in `run_script`, then starts them by ARN |
| Tool description built from the state machine `description` and the ASL `Comment` | Changed | The agent reads `description` and `definition` from `DescribeStateMachine`. Keep both detailed, because they are still what the agent goes on. |
| Input schema from the EventBridge Schema Registry in the tool description | Changed | The agent reads the schema ARN tag with `ListTagsForResource` and fetches the schema with `DescribeSchema` |
| Only the selected state machines could be started (`STATE_MACHINE_PREFIX`, `STATE_MACHINE_LIST`, and the tag filter) | Not available | `run_script` can call any AWS API your credentials allow. Use a dedicated least-privilege role or profile, for example one that allows `states:StartExecution` and `states:StartSyncExecution` only on specific state machine ARNs or with an `aws:ResourceTag` condition. |
| Waiting for a Standard execution to finish in one tool call | Changed | Check `DescribeExecution` in the same `run_script` for short executions, or in later calls for long ones |

## What Deprecation Means

- The final release keeps working. It prints a `FutureWarning` to standard error at startup, and its server instructions and generated tool descriptions are marked deprecated.
- The package stays on PyPI and gets no further updates.
- Configurations that use `awslabs.stepfunctions-tool-mcp-server@latest` get that final release.
- The `src/stepfunctions-tool-mcp-server` folder may later be removed from this repository, as the folders of earlier deprecated servers were.

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.stepfunctions-tool-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.stepfunctions-tool-mcp-server`
