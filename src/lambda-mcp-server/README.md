# AWS Lambda MCP Server

An AWS Labs Model Context Protocol (MCP) server for AWS Lambda to select and run Lambda function as MCP tools without code changes.

## Features

This MCP server acts as a **bridge** between MCP clients and AWS Lambda functions, allowing generative AI models to access and run Lambda functions as tools. This is useful, for example, to access private resources such as internal applications and databases without the need to provide public network access. This approach allows the model to use other AWS services, private networks, and the public internet.

```mermaid
graph LR
    A[Model] <--> B[MCP Client]
    B <--> C["MCP2Lambda<br>(MCP Server)"]
    C <--> D[Lambda Function]
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

From a **security** perspective, this approach implements segregation of duties by allowing the model to invoke the Lambda functions but not to access the other AWS services directly. The client only needs AWS credentials to invoke the Lambda functions. The Lambda functions can then interact with other AWS services (using the function role) and access public or private networks.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.lambda-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.lambda-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FUNCTION_PREFIX": "your-function-prefix",
        "FUNCTION_LIST": "your-first-function, your-second-function"
      }
    }
  }
}
```

The `AWS_PROFILE` and the `AWS_REGION` are optional, their defualt values are `default` and `us-east-1`.

You can specify `FUNCTION_PREFIX`, `FUNCTION_LIST`, or both.

The function name is used as MCP tool name. The function description in AWS Lambda is used as MCP tool description. The function description should clarify when to use the function (what it provides) and how (which parameters). For example, a function that gives access to an internal Customer Relationship Management (CRM) system can use this description:

```
Retrive customer status on the CRM system based on { 'customerId' } or { 'customerEmail' }
```

Sample functions that can be deployed via AWS SAM are provided in the `Examples` folder.

## Security Considerations

When using this MCP server, you should consider:

- Only Lambda functions that are in the provided list or with a name starting with the prefix are imported as MCP tools.
- The MCP server needs permissions to invoke the Lambda functions.
- Each Lambda function has its own permissions to optionally access other AWS resources.
