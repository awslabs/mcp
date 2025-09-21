## Contributing

Thanks for taking the time to contribute to the Unified AWS MCP Server!

We welcome bug reports, feature ideas, and pull requests. Use the guidance below to get started.

### Table of Contents

- [Reporting Bugs](#reporting-bugs)
- [Feature Enhancements](#feature-enhancements)
- [Local Development](#local-development)
- [Publishing Your Change](#publishing-your-change)

### Reporting Bugs
- Update to the latest `main` before filing an issue to confirm the bug still repros.
- Search existing issues to avoid duplicates.
- Include detailed reproduction steps, logs (from `~/.aws/aws-unified-mcp/aws-unified-mcp-server.log`), and MCP client / runtime details in your issue.

### Feature Enhancements
- Align proposals with this server's goal: proxying core AWS MCP capabilities through a single entry point.
- Prefer enhancements that benefit a broad set of users; avoid adding niche tools without discussion.
- Open a discussion or issue to validate direction before investing in a large change.

### Local Development

1. Clone the repository and switch to this server's directory:
   ```bash
   git clone https://github.com/awslabs/mcp.git
   cd mcp/src/aws-unified-mcp-server
   ```

2. Install dependencies with `uv`:
   ```bash
   uv sync
   ```

3. Configure any required AWS credentials or environment variables (for example `AWS_REGION`).

4. Run the server locally:
   ```bash
   PYTHONPATH=../..:.. uv run python -m unified_aws_mcp_server.server
   ```
   Add the same command to your MCP client's configuration when testing end-to-end.

### Publishing Your Change

1. Create a feature branch off `main`:
   ```bash
   git checkout -b <branch-name>
   ```

2. Format and type-check if you add tooling (for example, `uv run --frozen ruff check` or `pyright` once those are configured).

3. Run any relevant tests or manual verification.

4. Commit with a descriptive message, push the branch, and open a pull request. Reference related issues and update `CHANGELOG.md` when appropriate.
