# AWS Labs Amazon Q Business anonymous mode MCP Server

An AWS Labs Model Context Protocol (MCP) server for Amazon Q Business anonymous mode application. This is a simple MCP server for Amazon Q Business, and it supports Amazon Q Business application created using [anonymous mode access](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/create-anonymous-application.html). Use this MCP server to query the Amazon Q Business application created using anonymous mode to get responses based on the content you have ingested in it.

## Features
- [x] You can use this MCP server from your local machine with your
- [x] Query Amazon Q Business application created using anonymous mode to get responses based on the content you have ingested in it.

## Prerequisites

1. [Sign up for an AWS account](https://aws.amazon.com/free/?trk=78b916d7-7c94-4cab-98d9-0ce5e648dd5f&sc_channel=ps&ef_id=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB:G:s&s_kwcid=AL!4422!3!432339156162!e!!g!!aws%20sign%20up!9572385111!102212379327&gad_campaignid=9572385111&gbraid=0AAAAADjHtp99c5A9DUyUaUQVhVEoi8of3&gclid=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB)
2. [Create an Amazon Q Business application using anonynmous mode](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/create-anonymous-application.html)
3. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
4. Install Python using `uv python install 3.10`

## Tools
#### QBusinessQueryTool

- The QBusinessQueryTool takes the query specified by the user and queries the Amazon Q Business application to get a response.
- Required parameter: query(str)
- Example:
    * `Can you get me the details of the ACME project? Use the QBusinessQueryTool to get the context.`. Note that in this case the details of the ACME are required to be ingested to the underlying Amazon Q Business application created using anonymous mode.

## Setup

### IAM Configuration

1. Provision a user in your AWS account IAM
2. Attach a policy that contains at a minimum the `qbusiness:ChatSync` permission. Always follow the principal or least privilege when granting users permissions. See the [documentation](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/security_iam_id-based-policy-examples.html#security_iam_id-based-policy-examples-application-1) for more information on IAM permissions for Amazon Q Business.
3. Use `aws configure` on your environment to configure the credentials (access ID and access key)

### Installation

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
      "mcpServers": {
            "awslabs.amazon-qbusiness-anonymous-mcp-server": {
                  "command": "uvx",
                  "args": ["awslabs.qbusiness-anonymous-mcp-server"],
                  "env": {
                    "FASTMCP_LOG_LEVEL": "ERROR",
                    "QBUSINESS_APPLICATION_ID": "[Your Amazon Q Business application id]",
                    "AWS_PROFILE": "[Your AWS Profile Name]",
                    "AWS_REGION": "[Region where your Amazon Q Business application resides]"
                  },
                  "disabled": false,
                  "autoApprove": []
                }
      }
}
```
or docker after a successful `docker build -t awslabs/amazon-kendra-index-mcp-server.`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=<from the profile you set up>
AWS_SECRET_ACCESS_KEY=<from the profile you set up>
AWS_SESSION_TOKEN=<from the profile you set up>
```

```json
  {
    "mcpServers": {
      "awslabs.amazon-qbusiness-anonymous-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/amazon-qbusiness-anonymous-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```
NOTE: Your credentials will need to be kept refreshed from your host

## Best Practices

- Follow the principle of least privilege when setting up IAM permissions
- Use separate AWS profiles for different environments (dev, test, prod)
- Monitor broker metrics and logs for performance and issues
- Implement proper error handling in your client applications

## Security Considerations

When using this MCP server, consider:

- This MCP server needs permissions to use conversation APIs with your Amazon Q Business application created in anonymous mode.
- This MCP server cannot create, modify, or delete resources in your account

## Troubleshooting

- If you encounter permission errors, verify your IAM user has the correct policies attached
- For connection issues, check network configurations and security groups
- If resource modification fails with a tag validation error, it means the resource was not created by the MCP server
- For general Amazon Q Business issues, consult the [Amazon Q Business user guide](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/what-is.html)

## Version

Current MCP server version: 0.0.0
