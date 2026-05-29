# MCP Wrapper Policy

> Source: awslabs/mcp wrapper policy (April 2026)

## Policy Statement

The awslabs/mcp repo will not accept new MCP servers that are primarily wrappers around boto3. The AWS API MCP Server provides unified access to the breadth of AWS APIs through 2 tools, making 1:1 wrappers redundant.

## What IS a Wrapper

A wrapper is an MCP server that maps AWS API actions (boto3 service client methods) 1:1 as tools. Nothing more, nothing less. A wrapper does not add any logic or enhanced functionality.

**Example:** An MCP server that directly exposes boto3 SQS client methods 1-for-1 as MCP Tools (list_dead_letter_source_queues, list_message_move_tasks, list_queues, etc.) where the resulting MCP server has the same number of tools as AWS API methods, is a wrapper.

## What is NOT a Wrapper (4 categories)

### Category 1: Domain-specific, goal-oriented tools

The server provides task-oriented MCP tools, resources, and prompts that abstract away complex AWS interactions. This includes both simplified multi-step API operations (like combining list→get→put into a single tool) and multi-service workflows (such as coordinating S3, BDA, and polling operations). These abstractions help developers work at a higher level without managing underlying API complexity or cross-service orchestration.

### Category 2: Standalone AI/ML capabilities

The server provides standalone, general-purpose AI/ML capabilities usable independently for real business applications. Examples: Q Index, Kendra, Bedrock Knowledge Base retrieval servers focusing on RAG workflows. These abstract underlying complexity to provide purpose-built tools for agentic AI applications.

### Category 3: Data planes unavailable in AWS APIs

The server accesses data planes unavailable in AWS APIs. Example: direct database connections, SSM RunCommand to execute shell commands on instances.

### Category 4: Non-AWS-API tools

The server does not use any AWS APIs, and may be related to secondary systems, tools, or workflows commonly used by AWS developers. Particularly useful for context engineering in AI-assisted software development targeting AWS-first architectures.

## Additional Context

- SOTA LLMs struggle with >50 tools in one context window. Holistic approaches (AWS API MCP Server = 2 tools) or task/goal-oriented tools mitigate this by exposing fewer but richer tools.
- Servers named after a single service (EKS, ECS) may still be non-wrappers if they provide comprehensive, holistic tools for that platform.
- "Uses boto3" ≠ "is a wrapper" — all AWS MCP servers use boto3. The question is whether they add value on top.

## Evaluation Tips

### Strong non-wrapper signals
- Multiple AWS service clients used within a single tool (cross-service aggregation)
- Heavy helper/utility functions (`_` prefixed) with custom business logic
- Polling/retry loops, report generation, dependency resolution
- Auto-provisioning of supporting resources (IAM roles, EventBridge schedules)
- Data plane access not available through standard AWS APIs

### Weak/wrapper signals
- Tool count ≈ number of underlying boto3 methods (1:1 ratio)
- Each tool calls exactly one boto3 method and returns the result
- No custom logic beyond parameter forwarding
- Tool names mirror boto3 method names

### Borderline cases
- Multi-step tools that chain calls within the *same* service — these add orchestration value but aren't as strong as cross-service tools
- Pagination handling alone doesn't make a tool non-wrapper
- Error enrichment and response transformation add minor value but aren't sufficient on their own

## Exception Path

If a team must launch a 1:1 wrapper, they need either:
1. **VP justification** (escalation is OK), or
2. **Other demonstrable, distinct value** based on the criteria above

Internal teams may also consider the **Smithy MCP framework** for auto-generating MCP servers for Smithy/Coral-based services.
