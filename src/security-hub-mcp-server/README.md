# Security Hub MCP Server

A Model Context Protocol (MCP) server for analyzing security findings in AWS Security Hub. This server provides AI
assistants with the ability to query Security Hub for findings.

You can analyze your issues with prompts like:

> Identify the most important issues in Security Hub for AWS account ID 12345679012. Security Hub is enabled in region us-east-1.

Or filter by severity:

> What are the Security Hub issues with severity critical in account 12345679012?

Or several criteria, including custom filters:

> Get Security Hub findings with the following parameters (max results: 5):
> * region: us-east-1
> * severity: CRITICAL
> * workflow status: NEW
> * custom_filters: {'ResourceType': [{'Comparison': 'EQUALS', 'Value': 'AwsAccount'}]}

## Features

### Query

- **Get Findings**: Query Security Hub for findings

The `get_findings` tool supports the following parameters:

* `region` (required)
* `aws_account_id` (optional)
* `severity` (optional)
* `workflow_status` (optional)
*  `custom_filters` (optional)

`custom_filters` should be specified as a dictionary in the same format as the `Filters` key of the Security Hub
[`GetFindings` API](https://docs.aws.amazon.com/securityhub/1.0/APIReference/API_GetFindings.html). A filter specified
in `custom_filters` overrides a filter specified as a named parameter. So if you specify `severity` directly and in
`custom_filters`, the value in `custom_filters` will be used.

## Installation

```bash
# Install using uv (recommended)
uv tool install awslabs.security-hub-mcp-server

# Or install using pip
pip install awslabs.security-hub-mcp-server
```

## Configuration

### AWS Credentials
The server requires AWS credentials to be configured. You can use any of the following methods:

1. **AWS Profile** (recommended):
   ```bash
   export AWS_PROFILE=your-profile-name
   ```

2. **Environment Variables**:
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_REGION=us-east-1
   ```

3. **IAM Roles** (for EC2/Lambda):
   The server will automatically use IAM roles when running on AWS services.

### Required IAM Permissions

The AWS credentials used by this server need the following IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "securityhub:GetFindings"
      ],
      "Resource": "*"
    }
  ]
}
```

### MCP Client Configuration

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.security-hub&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJhd3NsYWJzLnNlY3VyaXR5LWh1Yi1tY3Atc2VydmVyQGxhdGVzdCJdLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiIsIkFXU19QUk9GSUxFIjoieW91ci1wcm9maWxlLW5hbWUifSwiZGlzYWJsZWQiOmZhbHNlfQ==)

You can configure the Security Hub MCP server in your favorite code assistant with MCP support like Q Developer, Cline,
or Claude. Add the `awslabs.security-hub` object below to your MCP server configuration and configure your
`AWS_PROFILE`:

```json
{
  "mcpServers": {
    "awslabs.security-hub": {
      "command": "uvx",
      "args": [
        "awslabs.security-hub-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-profile-name"
      },
      "disabled": false
    }
  }
}
```

## Possible Next Steps

The near term goal is to make the `get_findings` tool more useful and reliable.

For utility, this includes:

* 🚧 support filtering issues by date created/updated/observed, severity, workflow status
* ✅ support querying with user-supplied filters, because the [set of supported Security Hub issue filters is massive](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/securityhub/client/get_findings.html)
* ✅ support pagination and limits on maximum number of issues retrieved

For reliability, this may include:

* creating [prompts](https://modelcontextprotocol.io/docs/concepts/prompts#dynamic-prompts) and tools to help select the intended issues

## Contributing

Contributions are welcome! Please see the main repository's [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
1. Check the [AWS Security Hub documentation](https://docs.aws.amazon.com/securityhub/)
2. Review the [MCP specification](https://modelcontextprotocol.io/)
3. Open an issue in the [GitHub repository](https://github.com/awslabs/mcp)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.
