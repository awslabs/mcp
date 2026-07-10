# Migrating from AWS API MCP (`call_aws`) to AWS MCP (`run_script`)

## Summary

`run_script` replaces `call_aws` as the way agents run AWS API operations through the AWS MCP server. Both reach the same set of AWS APIs, so nothing you could do with `call_aws` becomes impossible. The difference is shape: `call_aws` translates one AWS CLI command into a single API call per invocation, while `run_script` executes a script that calls boto3 directly and can chain many API operations in a single pass.

## What changes and what does not

API coverage does not change. Any service, action, and parameter you reached through `call_aws` is reachable through `run_script`, because both resolve to the same underlying AWS API surface. What changes is efficiency. `call_aws` forced one round trip per API call, so a workflow that listed resources, filtered them, and then acted on each one turned into a long sequence of separate tool calls. `run_script` executes a script, so that same workflow becomes one call that lists, filters, loops, and acts inline. Fewer round trips means fewer tokens spent restating intermediate state.

## What you have to do

Remove hardcoded `call_aws` lines from your Skills, context files, prompts, and steering documents. These told the agent exactly which single API call to make and are now over-specified. In their place, rely on the "Prefer the AWS MCP Server for AWS interactions" instruction that already directs the agent to the right tooling ([example](https://github.com/aws/agent-toolkit-for-aws/blob/main/rules/aws-agent-rules.md)). The agent selects `run_script` and composes the calls itself, which keeps your documents shorter and frees them from breaking when an API detail shifts. Where a context file described a multi-step workflow as a series of `call_aws` lines, replace that series with a plain description of the goal and let the agent translate it into a script.

## Update your MCP configuration

The two tools ship from different servers, so migrating means swapping server entries in your MCP client config (e.g. `~/.kiro/settings/mcp.json`). `call_aws` came from the self-hosted **AWS API MCP Server**; `run_script` comes from the managed **AWS MCP Server**, which you reach through the `mcp-proxy-for-aws` proxy.

### Before (AWS API MCP Server)

```
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

```
{
  "mcpServers": {
    "aws-mcp": {
      "command": "uvx",
      "timeout": 100000,
      "transport": "stdio",
      "args": [
        "mcp-proxy-for-aws@latest",
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

## References
* https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html
