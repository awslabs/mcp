# AWS Deadline Cloud MCP Server

An MCP server for [AWS Deadline Cloud](https://aws.amazon.com/deadline-cloud/) that enables AI assistants to interact with Deadline Cloud services through natural language — submitting jobs, querying farm/queue/job information, troubleshooting failures, and retrieving logs.

> This MCP server lives in the [aws-deadline/deadline-cloud](https://github.com/aws-deadline/deadline-cloud) repository. See the [MCP guide](https://github.com/aws-deadline/deadline-cloud/blob/mainline/docs/mcp_guide.md) for full documentation.

## Key Features

- List and manage farms, queues, jobs, fleets, and storage profiles
- Submit Open Job Description job bundles
- Download job output files
- Troubleshoot failed jobs with session and worker logs
- Check authentication status

## Configuration

Install the server:

```bash
pip install 'deadline[mcp]'
```

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "deadline-cloud": {
      "command": "deadline",
      "args": ["mcp-server"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Prerequisites

- AWS credentials configured (AWS Profiles, environment variables, or `deadline auth login`)
- Python with `deadline[mcp]` package installed

## Example Prompts

- "List all my AWS Deadline Cloud farms"
- "Submit the render job in /path/to/my-job-bundle"
- "Troubleshoot job job-abc123 - why did it fail?"
- "Get the logs for session session-abc123"
- "Download output from job job-abc123"
