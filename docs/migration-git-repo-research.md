# Migration Guide: Git Repo Research MCP Server

This guide helps you migrate from `awslabs.git-repo-research-mcp-server` to alternative tools for code and documentation research.

## Why We're Deprecating

The `git-repo-research-mcp-server` requires Amazon Bedrock credentials for semantic search, which adds friction for many users. The community has developed well-maintained, open-source alternatives that cover the primary use cases without requiring AWS credentials.

## Recommended Alternative: Context7

[Context7](https://github.com/upstash/context7) is an actively maintained open-source MCP server that provides up-to-date documentation and code examples for popular libraries directly in your AI coding workflow.

### Installing Context7

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

**Important:** Remove the old `awslabs.git-repo-research-mcp-server` entry from your configuration after adding Context7.

## Feature Comparison

| Capability | git-repo-research | Context7 |
|---|---|---|
| Library documentation lookup | Via clone + index + search | Direct, no indexing needed |
| Semantic search over repos | FAISS + Bedrock embeddings | Built-in |
| AWS credentials required | Yes (Bedrock) | No |
| Private repo support | Yes | No |
| GitHub repo search | Yes (AWS orgs only) | No |
| Community support | Deprecated | Actively maintained |

## Tool Migration

| Old Tool | Alternative |
|---|---|
| `create_research_repository` | Not needed — Context7 fetches docs on demand |
| `search_research_repository` | Use Context7's `resolve-library-id` + `get-library-docs` |
| `search_repos_on_github` | Use GitHub's built-in search or `gh` CLI |
| `access_file` | Use your IDE's file access or MCP filesystem server |
| `delete_research_repository` | Not needed — no local index to manage |

## For Private Repository Use Cases

If you relied on `git-repo-research-mcp-server` for semantic search over private repositories, consider:

- **IDE built-in indexing**: Most modern IDEs (VS Code, Cursor, Kiro) have built-in code search and indexing
- **General-purpose code search**: Tools like `ripgrep` or `sourcegraph` provide fast code search without AWS dependencies

## Summary

For most users, Context7 provides a better experience for researching library documentation and code — no AWS credentials needed, no indexing step, and strong community support. For private repository search, use your IDE's built-in capabilities.
