# AWS Labs Amazon Kendra Index MCP Server

An AWS Labs Model Context Protocol (MCP) server for Amazon Kendra. This MCP server allows you to use Kendra Indices as additional context for RAG.

### Features:

* Enhance your existing MCP-enabled ChatBot with additional RAG indices
* Enhance the responses from coding assistants such as Cline, Cursor, Windsurf, Amazon Q Developer, etc.

### Pre-Requisites:

1. [Sign-Up for an AWS account](https://aws.amazon.com/free/?trk=78b916d7-7c94-4cab-98d9-0ce5e648dd5f&sc_channel=ps&ef_id=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB:G:s&s_kwcid=AL!4422!3!432339156162!e!!g!!aws%20sign%20up!9572385111!102212379327&gad_campaignid=9572385111&gbraid=0AAAAADjHtp99c5A9DUyUaUQVhVEoi8of3&gclid=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB)
2. [Create an Amazon Kendra Index](https://docs.aws.amazon.com/kendra/latest/dg/create-index.html) with your RAG documentation
3. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
4. Install Python using `uv python install 3.10`



### Tools:

#### KendraQueryTool

  - The KendraQueryTool takes the query specified by the user and queries a Kendra index to gain additional context for the response. This queries either the default index, or an index specified in the users prompt.
  - Required Parameters: query (str)
  - Optional Parameters: indexId (str), region (str)
  - Example:
    * `Can you help me understand how to implement a progress event in the CreateHandler using Java? Use the KendraQueryTool to gain additional context.`
    * `Can you use the test-kendra-index to help answer the following questions...`

#### KendraListIndexesTool

  - The KendraListIndexesTool lists the Kendra Indexes in your account. By default it will list all the indices in the regions provided as environment variables to the mcp config file. Otherwise the region can be specified in the prompt.
  - Optional Parameters: region (str)
  - Example:
    * `Can you list the Kendra Indexes in my account in the us-west-2 region`


## Setup

### IAM Configuration

1. Provision a user in your AWS account IAM
2. Attach a policy that contains at a minimum the `kendra:Query` and `kendra:ListIndices` permissions. Alternatively the AWS Managed `AmazonKendraFullAccess` policy can be attached. Always follow the principal or least privilege when granting users permissions. See the [documentation](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonkendra.html) for more information on IAM permissions for Amazon Kendra.
3. Use `aws configure` on your environment to configure the credentials (access ID and access key)

### Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.amazon-kendra-index-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWtlbmRyYS1pbmRleC1tY3Atc2VydmVyIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IiLCJLRU5EUkFfSU5ERVhfSUQiOiJbWW91ciBLZW5kcmEgSW5kZXggSWRdIiwiQVdTX1BST0ZJTEUiOiJbWW91ciBBV1MgUHJvZmlsZSBOYW1lXSIsIkFXU19SRUdJT04iOiJbUmVnaW9uIHdoZXJlIHlvdXIgS2VuZHJhIEluZGV4IHJlc2lkZXNdIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D)

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
      "mcpServers": {
            "awslabs.amazon-kendra-index-mcp-server": {
                  "command": "uvx",
                  "args": ["awslabs.amazon-kendra-index-mcp-server"],
                  "env": {
                    "FASTMCP_LOG_LEVEL": "ERROR",
                    "KENDRA_INDEX_ID": "[Your Kendra Index Id]",
                    "AWS_PROFILE": "[Your AWS Profile Name]",
                    "AWS_REGION": "[Region where your Kendra Index resides]"
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
      "awslabs.amazon-kendra-index-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/amazon-kendra-index-mcp-server:latest"
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

- This MCP server needs permissions to query and list Amazon Kendra Indexes
- This MCP server cannot create, modify, or delete resources in your account

## Troubleshooting

- If you encounter permission errors, verify your IAM user has the correct policies attached
- For connection issues, check network configurations and security groups
- If resource modification fails with a tag validation error, it means the resource was not created by the MCP server
- For general Amazon Kendra issues, consult the [Amazon Kendra developer guide](https://docs.aws.amazon.com/kendra/latest/dg/what-is-kendra.html)

## Version

Current MCP server version: 0.0.0
