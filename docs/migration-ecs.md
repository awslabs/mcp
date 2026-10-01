# Migration Guide: ECS MCP Server to the Agent Toolkit for AWS

This guide helps you migrate from `awslabs.ecs-mcp-server` to the [Agent Toolkit for AWS](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/what-is-agent-toolkit.html).

## Why We're Deprecating

The ECS MCP Server bundled containerization guidance, ECS/ECR resource operations, deployment troubleshooting, and AWS documentation access into a single purpose-built server. The Agent Toolkit for AWS now delivers the same outcomes through a smaller, more general set of building blocks: the **AWS MCP Server** — which consolidates the AWS API and AWS Knowledge MCP servers, giving your agent access to every AWS API plus up-to-date AWS documentation — together with a curated set of **agent skills**, including the **`aws-containers` skill** for ECS containerization and troubleshooting guidance.

## Installing the Replacement

Install the Agent Toolkit **aws-core** plugin for your AI coding agent. It bundles the AWS MCP Server and the default agent skills — including the `aws-containers` skill — in a single install.

Follow the official, always-current setup steps for your agent (Kiro, Claude Code, Codex, or any MCP-compatible agent) in the [Agent Toolkit for AWS getting started guide](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html).

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.ecs-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.ecs-mcp-server`
3. The old package remains on PyPI for now but is deprecated and will be archived; it will not receive updates
