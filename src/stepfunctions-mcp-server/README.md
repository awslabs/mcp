# AWS Step Functions MCP Server

A Model Context Protocol (MCP) server for AWS Step Functions to select and run state machines as MCP tools without code changes.

## Features

This MCP server acts as a **bridge** between MCP clients and AWS Step Functions state machines, allowing generative AI models to access and run state machines as tools. This enables seamless integration with existing Step Function workflows without requiring any modifications to their definitions. Through this bridge, AI models can execute and manage complex, multi-step business processes that coordinate operations across multiple AWS services.

The server supports both Standard and Express workflows, adapting to different execution needs. Standard workflows excel at long-running processes where status tracking is essential, while Express workflows handle high-volume, short-duration tasks with synchronous execution. This flexibility ensures optimal handling of various workflow patterns and requirements.

To ensure data quality and provide clear documentation, the server integrates with EventBridge Schema Registry for input validation. It combines schema information with state machine definitions to generate comprehensive tool documentation, helping AI models understand both the purpose and technical requirements of each workflow.

From a security perspective, the server implements IAM-based authentication and authorization, creating a clear separation of duties. While models can invoke state machines through the MCP server, they don't have direct access to other AWS services. Instead, the state machines themselves handle AWS service interactions using their own IAM roles, maintaining robust security boundaries while enabling powerful workflow capabilities.

```mermaid
graph LR
    A[Model] <--> B[MCP Client]
    B <--> C["MCP2StepFunctions<br>(MCP Server)"]
    C <--> D[State Machine]
    D <--> E[Other AWS Services]
    D <--> F[Internet]
    D <--> G[VPC]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bfb,stroke:#333,stroke-width:4px
    style D fill:#fbb,stroke:#333,stroke-width:2px
    style E fill:#fbf,stroke:#333,stroke-width:2px
    style F fill:#dff,stroke:#333,stroke-width:2px
    style G fill:#ffd,stroke:#333,stroke-width:2px
```

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.stepfunctions-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.stepfunctions-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "STATE_MACHINE_PREFIX": "your-state-machine-prefix",
        "STATE_MACHINE_LIST": "your-first-state-machine, your-second-state-machine",
        "STATE_MACHINE_TAG_KEY": "your-tag-key",
        "STATE_MACHINE_TAG_VALUE": "your-tag-value",
        "STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY": "your-state-machine-tag-for-input-schema"
      }
    }
  }
}
```

or docker after a successful `docker build -t awslabs/stepfunctions-mcp-server .`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
```

```json
  {
    "mcpServers": {
      "awslabs.stepfunctions-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "AWS_REGION=us-east-1",
          "--env",
          "STATE_MACHINE_PREFIX=your-state-machine-prefix",
          "--env",
          "STATE_MACHINE_LIST=your-first-state-machine,your-second-state-machine",
          "--env",
          "STATE_MACHINE_TAG_KEY=your-tag-key",
          "--env",
          "STATE_MACHINE_TAG_VALUE=your-tag-value",
          "--env",
          "STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY=your-state-machine-tag-for-input-schema",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/stepfunctions-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```

NOTE: Your credentials will need to be kept refreshed from your host

The `AWS_PROFILE` and the `AWS_REGION` are optional, their default values are `default` and `us-east-1`.

You can specify `STATE_MACHINE_PREFIX`, `STATE_MACHINE_LIST`, or both. If both are empty, all state machines pass the name check.
After the name check, if both `STATE_MACHINE_TAG_KEY` and `STATE_MACHINE_TAG_VALUE` are set, state machines are further filtered by tag (with key=value).
If only one of `STATE_MACHINE_TAG_KEY` and `STATE_MACHINE_TAG_VALUE`, then no state machine is selected and a warning is displayed.

## Tool Documentation

The MCP server builds comprehensive tool documentation by combining multiple sources of information to help AI models understand and use state machines effectively.

1. **State Machine Description**: The state machine's description field provides the base tool description. For example:
   ```plaintext
   Retrieve customer status on the CRM system based on { 'customerId' } or { 'customerEmail' }
   ```

2. **Workflow Description**: The Comment field from the state machine definition adds workflow context. For example:
   ```json
   {
     "Comment": "This workflow first looks up a customer ID from email, then retrieves their info",
     "StartAt": "GetCustomerId",
     "States": { ... }
   }
   ```

3. **Input Schema**: The server integrates with EventBridge Schema Registry to provide formal JSON Schema documentation for state machine inputs. To enable schema support:
   - Create your schema in EventBridge Schema Registry
   - Tag your state machine with the schema ARN:
     ```plaintext
     Key: STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY (configurable)
     Value: arn:aws:schemas:region:account:schema/registry-name/schema-name
     ```
   - Configure the MCP server:
     ```json
     {
       "env": {
         "STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY": "your-schema-arn-tag-key"
       }
     }
     ```

The server combines these sources into a unified documentation format:
```plaintext
[State Machine Description]

Workflow Description: [Comment from state machine definition]

Input Schema:
[JSON Schema from EventBridge Schema Registry]
```

This comprehensive documentation helps AI models understand both the purpose and technical requirements of each state machine, with formal schema support ensuring correct input formatting.

## Best practices

- Use the `STATE_MACHINE_LIST` to specify the state machines that are available as MCP tools.
- Use the `STATE_MACHINE_PREFIX` to specify the prefix of the state machines that are available as MCP tools.
- Use the `STATE_MACHINE_TAG_KEY` and `STATE_MACHINE_TAG_VALUE` to specify the tag key and value of the state machines that are available as MCP tools.
- AWS Step Functions `Description` property: the description of the state machine is used as MCP tool description, so it should be very detailed to help the model understand when and how to use the state machine
- Add workflow documentation using the `Comment` field in state machine definitions:
  - Describe the workflow's purpose and steps
  - Explain any important logic or conditions
  - Document expected inputs and outputs
- Use EventBridge Schema Registry to provide formal input definition:
  - Create JSON Schema definitions for your state machine inputs
  - Tag state machines with their schema ARNs
  - Configure `STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY` in the MCP server

## Security Considerations

When using this MCP server, you should consider:

- Only state machines that are in the provided list or with a name starting with the prefix are imported as MCP tools.
- The MCP server needs permissions to invoke the state machines.
- Each state machine has its own permissions to optionally access other AWS resources.
