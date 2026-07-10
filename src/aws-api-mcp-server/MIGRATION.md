# Migrating from AWS API MCP to AWS MCP

## Summary

The [AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html) is the successor to the AWS API MCP Server. Beyond covering the same AWS API surface, the AWS MCP Server stays current with new AWS services and APIs, retrieves up-to-date AWS documentation at query time, and adds sandboxed script execution for multi-step tasks. For governance, it publishes Amazon CloudWatch metrics so you can monitor agent activity separately from human activity, records every API call in AWS CloudTrail for a complete audit trail, and supports OAuth 2.1 authorization. It is a fully-managed remote server — you no longer need to run the server process locally.

## What changes and what does not

### Tool comparison

The AWS API MCP Server exposes these tools:

| Tool | Purpose |
|------|---------|
| `call_aws` | Execute a single AWS CLI command per invocation |
| `suggest_aws_commands` | Suggest CLI commands for a natural language query |
| `get_execution_plan` *(experimental)* | Step-by-step guidance for complex AWS tasks |

The AWS MCP Server replaces and expands on these with:

| Tool | Purpose |
|------|---------|
| `aws___call_aws` | Execute authenticated AWS API calls (same coverage as the old `call_aws`) |
| `aws___run_script` | Execute Python code in a sandboxed environment — chain multiple API calls in one pass |
| `aws___search_documentation` | Search AWS documentation, best practices, and agent skills |
| `aws___read_documentation` | Retrieve full AWS documentation pages as markdown |
| `aws___retrieve_skill` | Load domain-specific procedures (CloudFormation authoring, serverless patterns, etc.) |
| `aws___list_regions` | List all AWS Regions |
| `aws___get_regional_availability` | Check service/feature availability by Region |
| `aws___get_presigned_url` | Generate pre-signed S3 URLs for uploads/downloads |
| `aws___get_tasks` | Poll the status of long-running tasks |

For the full and up-to-date tool list, see [Understanding the MCP Server tools](https://docs.aws.amazon.com/aws-mcp/latest/userguide/understanding-mcp-server-tools.html).

### API coverage

API coverage does not change. Any service, action, and parameter you reached through `call_aws` is reachable through `aws___call_aws` and `aws___run_script`, because both resolve to the same underlying AWS API surface. What changes is efficiency: `call_aws` forced one round trip per API call, so a workflow that listed resources, filtered them, and then acted on each one turned into a long sequence of separate tool calls. `aws___run_script` executes a script, so that same workflow becomes one call that lists, filters, loops, and acts inline. Fewer round trips means fewer tokens spent restating intermediate state.

### Knowledge tools

The AWS API MCP Server had no built-in documentation retrieval — agents relied solely on their training data. The AWS MCP Server adds `aws___search_documentation`, `aws___read_documentation`, and `aws___retrieve_skill`, giving agents access to current AWS documentation and validated procedures. This means agents no longer hallucinate outdated API parameters or miss recently launched services.

## What you have to do

Remove hardcoded `call_aws` lines from your Skills, context files, prompts, and steering documents. These told the agent exactly which single API call to make and are now over-specified. In their place, rely on the "Prefer the AWS MCP Server for AWS interactions" instruction that already directs the agent to the right tooling ([example](https://github.com/aws/agent-toolkit-for-aws/blob/main/rules/aws-agent-rules.md)). The agent selects `run_script` and composes the calls itself, which keeps your documents shorter and frees them from breaking when an API detail shifts. Where a context file described a multi-step workflow as a series of `call_aws` lines, replace that series with a plain description of the goal and let the agent translate it into a script.

## Update your MCP configuration

The two tools ship from different servers, so migrating means swapping server entries in your MCP client config (e.g., `~/.kiro/settings/mcp.json`). `call_aws` came from the self-hosted **AWS API MCP Server**; `run_script` comes from the managed **AWS MCP Server**, which you reach through the `mcp-proxy-for-aws` proxy.

### Before (AWS API MCP Server)

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-api-mcp-server@latest"
      ],
      "env": { "AWS_REGION": "us-west-2" },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### After (AWS MCP Server via proxy)

```json
{
  "mcpServers": {
    "aws-mcp": {
      "command": "uvx",
      "timeout": 100000,
      "transport": "stdio",
      "args": [
        "mcp-proxy-for-aws@1.6.3",
        "https://aws-mcp.us-east-1.api.aws/mcp",
        "--metadata", "AWS_REGION=us-west-2"
      ]
    }
  }
}
```

### Key differences

* **What `uvx` runs.** Before, `uvx` ran the entire MCP server locally (`awslabs.aws-api-mcp-server`), executing AWS calls on your machine with local boto3. After, `uvx` runs only a thin proxy (`mcp-proxy-for-aws`) that forwards to a **managed remote server** — the actual execution happens on the AWS-hosted endpoint, not locally.
* **Region setup.** Region moves out of `env.AWS_REGION` and into a `--metadata AWS_REGION=...` arg. Note these are two independent Regions: the endpoint URL Region is where the MCP server runs, while `--metadata AWS_REGION` is the default Region for the AWS operations it performs — they can differ. Omitting the metadata defaults all operations to `us-east-1`.
* **Server name.** Delete the old entry entirely — running both at once causes tool conflicts that confuse the agent.
* **Pin the proxy version.** Use a specific version (e.g., `mcp-proxy-for-aws@1.6.3`) rather than `@latest`. Unpinned installs resolve all transitive dependencies to their newest versions at install time, which is a supply chain risk if any dependency is compromised. Check [PyPI](https://pypi.org/project/mcp-proxy-for-aws/) for the latest release and update the pin when you upgrade.

## Environment variable migration

The AWS API MCP Server supported several environment variables in the `env` block of your MCP config. When migrating to the AWS MCP Server, these variables are no longer used because the managed server handles configuration differently.

| AWS API MCP Server Variable | What it did | AWS MCP Server equivalent |
|-----------------------------|-------------|---------------------------|
| `AWS_REGION` | Set the default AWS Region for operations | Pass `--metadata AWS_REGION=<region>` as an arg to the proxy |
| `AWS_API_MCP_PROFILE_NAME` | Selected a named AWS credential profile | Use `--profile <name>` with the proxy (see [Multi-profile support](https://docs.aws.amazon.com/aws-mcp/latest/userguide/multi-account-access.html)) |
| `READ_OPERATIONS_ONLY` | Restricted execution to read-only operations | Use IAM condition keys to restrict actions on the managed server (see [IAM policies for AWS MCP](https://docs.aws.amazon.com/aws-mcp/latest/userguide/security-iam-awsmanpol.html)), or use `--read-only` flag with the proxy |
| `REQUIRE_MUTATION_CONSENT` | Required explicit consent before write operations | Not needed — use IAM policies to control write access |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` | Provided explicit AWS credentials | Configure credentials via `aws configure` or `aws login`; the proxy uses your local credential chain |
| `AWS_API_MCP_WORKING_DIR` | Set the working directory for file operations | Not applicable — the managed server uses sandboxed execution; local file paths are not used |
| `AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS` | Controlled local file system access scope | Not applicable — no local file system access on the managed server |
| `EXPERIMENTAL_AGENT_SCRIPTS` | Enabled experimental agent scripts | Replaced by built-in skills accessible via `aws___retrieve_skill` |
| `AWS_API_MCP_AGENT_SCRIPTS_DIR` | Custom scripts directory | Not applicable — use Agent Toolkit skills instead |
| `AWS_API_MCP_TRANSPORT` / `AWS_API_MCP_HOST` / `AWS_API_MCP_PORT` | Configured HTTP transport mode | Not applicable — the managed server handles transport; the proxy communicates via stdio locally |
| `AUTH_TYPE` / `AUTH_ISSUER` / `AUTH_JWKS_URI` | Configured OAuth for HTTP mode | Built into the managed server — configure via OAuth or SigV4 authentication options |
| `AWS_API_MCP_TELEMETRY` | Controlled telemetry | Not applicable — observability is provided via CloudWatch and CloudTrail |

**In short:** Remove the entire `"env": { ... }` block from your old config. The proxy needs only the endpoint URL and optional `--metadata` args.

## References

* [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html)
* [Understanding the MCP Server tools](https://docs.aws.amazon.com/aws-mcp/latest/userguide/understanding-mcp-server-tools.html)
* [Agent Toolkit for AWS announcement](https://aws.amazon.com/about-aws/whats-new/2026/05/agent-toolkit/)
