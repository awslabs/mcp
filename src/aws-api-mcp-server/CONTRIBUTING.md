## Contributing

First off, thanks for taking the time to contribute to this MCP server!

All types of contributions are encouraged and valued. See the [Table of Contents](#table-of-contents) for more details.

### Table of Contents

- [Reporting Bugs](#reporting-bugs)
- [Feature Enhancement](#feature-enhancement)
- [Local Development](#local-development)
- [Publishing your Change](#publishing-your-change)


### Reporting Bugs
- Before reporting bugs, please make sure you are on the latest commit.
- Go through existing issues and check no users have reported the same bug.
- Submit a Github Issue with detailed steps on how to reproduce this bug, as well as your system information such as your MCP client used, LLM agent, operating system etc.


### Feature Enhancement
- Before submitting a pull request, please make sure you are on the latest commit.
- Double check your feature enhancement is within the scope of this project, in particular, this server is scoped down to executing AWS APIs from Natural Language input, and will not cover use cases that are not generally applicable to all users. It is strongly recommended to not add new tools unless you find them necessary and cover many use cases.
- [Submit a pull request](#publishing-your-change)

### Local Development

To make changes to this MCP locally and run it:

1. Clone this repository:
```bash
git clone https://github.com/awslabs/mcp.git
cd mcp/src/aws-api-mcp-server
```

2. Install gh from the [installation guide](https://cli.github.com/)
    - Log in by `gh auth login`
    - Verify log-in status by `gh auth status`. ---> You should see "Logged in to github.com account ***"

3. Install dependencies:
```bash
uv sync
```

4. Configure AWS credentials and environment variables:
   - Ensure you have AWS credentials configured as you did during installation, read more [here](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials)
   - The server supports both STDIO (default) and Streamable HTTP transport modes. For local development, use STDIO mode. For network scenarios, you can set `AWS_API_MCP_TRANSPORT` to `"streamable-http"` and configure the host and port with `AWS_API_MCP_HOST` and `AWS_API_MCP_PORT`.


5. Run the server:
Add the following code to your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`). Configuration is similar to "Installation" in README.md.

```
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "<your_working_directory>/mcp/src/aws-api-mcp-server",
        "run",
        "awslabs.aws-api-mcp-server"
      ],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_API_MCP_PROFILE_NAME": "<your_profile_name>",
        "READ_OPERATIONS_ONLY": "false",
        "AWS_API_MCP_TELEMETRY": "true"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```


&nbsp;

### Publishing your Change

#### Initial Setup

1. **Fork the repository** (if you haven't already):
   - Go to https://github.com/awslabs/mcp and click "Fork"
   - Clone your fork: `git clone https://github.com/<your-username>/mcp.git`

2. **Add upstream remote** (to sync with main repo):
```bash
git remote add upstream https://github.com/awslabs/mcp.git
```

#### Making Changes

1. **Sync with upstream and create a new branch**:
```bash
git checkout main
git pull upstream main
git push origin main  # Update your fork
git checkout -b feat/your-feature-name  # Use descriptive prefix: feat/, fix/, docs/
```

2. **Make your changes and validate**:
```bash
# Ensure you're in the correct directory
cd mcp/src/aws-api-mcp-server

# Run type checking
uv run --frozen pyright

# Run pre-commit checks
cd ../..
pre-commit run --all-files
```

3. **Commit your changes**:
```bash
git add .
git commit -m "feat: add descriptive commit message" # Use descriptive prefix: feat/, fix/, docs/
```

#### Publishing and Updates

4. **Push and create PR**:
```bash
git push origin feat/your-feature-name
gh pr create --title "Your PR Title" --body "Description of changes"
```

#### Updating Existing PRs

- **Add new commits**:
```bash
git add .
git commit -m "feat: address review feedback" # Use descriptive prefix: feat/, fix/, docs/
git push origin feat/your-feature-name
```

#### Syncing with Upstream

**When your branch is out of sync:**

```bash
git checkout main
git pull upstream main
git checkout feat/your-feature-name
git merge main
```
&nbsp;
