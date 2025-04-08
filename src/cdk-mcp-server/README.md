# AWS CDK MCP Server

MCP server for AWS Cloud Development Kit (CDK) best practices, infrastructure as code patterns, and security compliance with CDK Nag.

## Features

### CDK General Guidance

- Prescriptive patterns with AWS Solutions Constructs and GenAI CDK libraries
- Structured decision flow for choosing appropriate implementation approaches
- Security automation through CDK Nag integration and Lambda Powertools

### CDK Nag Integration

- Work with CDK Nag rules for security and compliance
- Explain specific CDK Nag rules with AWS Well-Architected guidance
- Check if CDK code contains Nag suppressions that require human review

### AWS Solutions Constructs

- Search and discover AWS Solutions Constructs patterns
- Find recommended patterns for common architecture needs
- Get detailed documentation on Solutions Constructs

### Generative AI CDK Constructs

- Search for GenAI CDK constructs by name or type
- Discover specialized constructs for AI/ML workloads
- Get implementation guidance for generative AI applications

### Amazon Bedrock Agent Schema Generation

- Use this tool when creating Bedrock Agents with Action Groups that use Lambda functions
- Streamline the creation of Bedrock Agent schemas
- Convert code files to compatible OpenAPI specifications

#### Developer Notes

- **Requirements**: Your Lambda function must use `BedrockAgentResolver` from AWS Lambda Powertools
- **Lambda Dependencies**: If schema generation fails, a fallback script will be generated. If you see error messages about missing dependencies, install them and then run the script again.
- **Integration**: Use the generated schema with `bedrock.ApiSchema.fromLocalAsset()` in your CDK code

## CDK Implementation Workflow

This diagram provides a comprehensive view of the recommended CDK implementation workflow:

```mermaid
graph TD
    Start([Start]) --> Init["cdk init app"]

    Init --> B{Choose Approach}
    B -->|"Common Patterns"| C1["GetAwsSolutionsConstructPattern"]
    B -->|"GenAI Features"| C2["SearchGenAICDKConstructs"]
    B -->|"Custom Needs"| C3["Custom CDK Code"]

    C1 --> D1["Implement Solutions Construct"]
    C2 --> D2["Implement GenAI Constructs"]
    C3 --> D3["Implement Custom Resources"]

    %% Bedrock Agent with Action Groups specific flow
    D2 -->|"For Bedrock Agents<br/>with Action Groups"| BA["Create Lambda with<br/>BedrockAgentResolver"]

    %% Schema generation flow
    BA --> BS["GenerateBedrockAgentSchema"]
    BS -->|"Success"| JSON["openapi.json created"]
    BS -->|"Import Errors"| BSF["Tool generates<br/>generate_schema.py"]
    BSF -->|"Missing dependencies?"| InstallDeps["Install dependencies"]
    InstallDeps --> BSR["Run script manually:<br/>python generate_schema.py"]
    BSR --> JSON["openapi.json created"]

    %% Use schema in Agent CDK
    JSON --> AgentCDK["Use schema in<br/>Agent CDK code"]
    AgentCDK --> D2

    %% Conditional Lambda Powertools implementation
    D1 & D2 & D3 --> HasLambda{"Using Lambda<br/>Functions?"}
    HasLambda -->|"Yes"| L["Add Lambda Powertools<br/>and create Layer"]
    HasLambda -->|"No"| SkipL["Skip Lambda<br/>Powertools"]

    %% Rest of workflow
    L --> Synth["cdk synth"]
    SkipL --> Synth

    Synth --> Nag{"CDK Nag<br/>warnings?"}
    Nag -->|Yes| E["ExplainCDKNagRule"]
    Nag -->|No| Deploy["cdk deploy"]

    E --> Fix["Fix or Add Suppressions"]
    Fix --> CN["CheckCDKNagSuppressions"]
    CN --> Synth

    %% Styling with darker colors
    classDef default fill:#424242,stroke:#ffffff,stroke-width:1px,color:#ffffff;
    classDef cmd fill:#4a148c,stroke:#ffffff,stroke-width:1px,color:#ffffff;
    classDef tool fill:#01579b,stroke:#ffffff,stroke-width:1px,color:#ffffff;
    classDef note fill:#1b5e20,stroke:#ffffff,stroke-width:1px,color:#ffffff;
    classDef output fill:#006064,stroke:#ffffff,stroke-width:1px,color:#ffffff;
    classDef decision fill:#5d4037,stroke:#ffffff,stroke-width:1px,color:#ffffff;

    class Init,Synth,Deploy,BSR cmd;
    class C1,C2,BS,E,CN tool;
    class JSON output;
    class HasLambda,Nag decision;
```

## Tools and Resources

- **CDK Nag Rules**: Access rule packs via `cdk-nag://rules/{rule_pack}`
- **Lambda Powertools**: Get guidance on Lambda Powertools via `lambda-powertools://{topic}`
- **AWS Solutions Constructs**: Access patterns via `aws-solutions-constructs://{pattern_name}`
- **GenAI CDK Constructs**: Access documentation via `genai-cdk-constructs://{construct_type}/{construct_name}`

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.cdk-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cdk-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Security Considerations

When using this MCP server, you should consider:

- Reviewing all CDK Nag warnings and errors manually
- Fixing security issues rather than suppressing them whenever possible
- Documenting clear justifications for any necessary suppressions
- Using the CheckCDKNagSuppressions tool to verify no unauthorized suppressions exist

Before applying CDK NAG Suppressions, you should consider conducting your own independent assessment to ensure that your use would comply with your own specific security and quality control practices and standards, as well as the local laws, rules, and regulations that govern you and your content.
