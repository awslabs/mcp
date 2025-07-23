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

To publish local changes for review:

1. Create a new local branch and make your changes
```bash
git checkout -b <your_branch_name> # use proper prefix
```

2. Make sure your current directory is at `<your_working_directory>/mcp/src/aws-mcp-server`:
```bash
uv run --frozen pyright
```

3. Run pre-commit checks:
```bash
cd ../..
pre-commit run --all-files
```

4. Commit and push to remote, open a PR on Github

&nbsp;
