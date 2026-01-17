# AWS Labs Aurora DSQL MCP Server

An AWS Labs Model Context Protocol (MCP) server for Aurora DSQL
and corresponding AI rules that can be used for additional model
steering while developing.

## Features

- Converting human-readable questions and commands into structured Postgres-compatible SQL queries and executing them against the configured Aurora DSQL database.
- Read-only by default, transactions enabled with `--allow-writes`
- Connection reuse between requests for improved performance
- Built-in access to Aurora DSQL documentation, search, and best practice recommendations

## Available Tools

### Database Operations

- **readonly_query** - Execute read-only SQL queries against your DSQL cluster
- **transact** - Execute SQL statements in a transaction
  - In read-only mode: Supports read operations with transactional consistency
  - With `--allow-writes`: Supports all write operations too
- **get_schema** - Retrieve table schema information

### Documentation and Recommendations

- **dsql_search_documentation** - Search Aurora DSQL documentation
  - Parameters: `search_phrase` (required), `limit` (optional)
- **dsql_read_documentation** - Read specific DSQL documentation pages
  - Parameters: `url` (required), `start_index` (optional), `max_length` (optional)
- **dsql_recommend** - Get recommendations for DSQL best practices
  - Parameters: `url` (required)

## Prerequisites

1. An AWS account with an [Aurora DSQL Cluster](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/getting-started.html)
1. This MCP server can only be run locally on the same host as your LLM client.
1. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables

## Installation

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aurora-dsql-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aurora-dsql-mcp-server%40latest%22%2C%22--cluster_endpoint%22%2C%22%5Byour%20dsql%20cluster%20endpoint%5D%22%2C%22--region%22%2C%22%5Byour%20dsql%20cluster%20region%2C%20e.g.%20us-east-1%5D%22%2C%22--database_user%22%2C%22%5Byour%20dsql%20username%5D%22%2C%22--profile%22%2C%22default%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aurora-dsql-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXVyb3JhLWRzcWwtbWNwLXNlcnZlckBsYXRlc3QgLS1jbHVzdGVyX2VuZHBvaW50IFt5b3VyIGRzcWwgY2x1c3RlciBlbmRwb2ludF0gLS1yZWdpb24gW3lvdXIgZHNxbCBjbHVzdGVyIHJlZ2lvbiwgZS5nLiB1cy1lYXN0LTFdIC0tZGF0YWJhc2VfdXNlciBbeW91ciBkc3FsIHVzZXJuYW1lXSAtLXByb2ZpbGUgZGVmYXVsdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Aurora%20DSQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aurora-dsql-mcp-server%40latest%22%2C%22--cluster_endpoint%22%2C%22%5Byour%20dsql%20cluster%20endpoint%5D%22%2C%22--region%22%2C%22%5Byour%20dsql%20cluster%20region%2C%20e.g.%20us-east-1%5D%22%2C%22--database_user%22%2C%22%5Byour%20dsql%20username%5D%22%2C%22--profile%22%2C%22default%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### Using `uv`

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

Configure the MCP server in your MCP client configuration (e.g., for Kiro, edit `~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aurora-dsql-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aurora-dsql-mcp-server@latest",
        "--cluster_endpoint",
        "[your dsql cluster endpoint]",
        "--region",
        "[your dsql cluster region, e.g. us-east-1]",
        "--database_user",
        "[your dsql username]",
        "--profile",
        "default"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.aurora-dsql-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aurora-dsql-mcp-server@latest",
        "awslabs.aurora-dsql-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

### Using Docker

1. 'git clone https://github.com/awslabs/mcp.git'
2. Go to sub-directory 'src/aurora-dsql-mcp-server/'
3. Run 'docker build -t awslabs/aurora-dsql-mcp-server:latest .'
4. Create a env file with temporary credentials:

Either manually:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=<from the profile you set up>
AWS_SECRET_ACCESS_KEY=<from the profile you set up>
AWS_SESSION_TOKEN=<from the profile you set up>
```

Or using `aws configure`:

```bash
aws configure export-credentials --profile your-profile-name --format env > temp_aws_credentials.env | sed 's/^export //' > temp_aws_credentials.env
```

```json
{
  "mcpServers": {
    "awslabs.aurora-dsql-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--env-file",
        "/full/path/to/file/above/.env",
        "awslabs/aurora-dsql-mcp-server:latest",
        "--cluster_endpoint",
        "[your data]",
        "--database_user",
        "[your data]",
        "--region",
        "[your data]"
      ]
    }
  }
}
```

## Server Configuration options

### `--allow-writes`

By default, the DSQL MCP server operates in read-only mode. In this mode:

- **readonly_query**: Executes single read-only queries
- **transact**: Executes read-only transactions with point-in-time consistency
  - Useful for multiple queries that need to see data at the same point in time
  - All statements are validated to ensure they are read-only operations
  - Write operations (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, etc.) are rejected

To enable write operations, pass the `--allow-writes` parameter. In read-write mode:

- **readonly_query**: Same behavior (read-only queries)
- **transact**: Supports all DDL and DML operations (CREATE, INSERT, UPDATE, DELETE, etc.)

We recommend using least-privilege access when connecting to DSQL. For example, users should use a role that is read-only when possible. The read-only mode provides best-effort client-side validation to reject mutations.

### `--cluster_endpoint`

This is mandatory parameter to specify the cluster to connect to. This should be the full endpoint of your cluster, e.g., `01abc2ldefg3hijklmnopqurstu.dsql.us-east-1.on.aws`

### `--database_user`

This is a mandatory parameter to specify the user to connect as. For example
`admin`, or `my_user`. Note that the AWS credentials you are using must have
permission to login as that user. For more information on setting up and using
database roles in DSQL, see [Using database roles with IAM roles](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html).

### `--profile`

You can specify the aws profile to use for your credentials. Note that this is
not supported for docker installation.

Using the `AWS_PROFILE` environment variable in your MCP configuration is also
supported:

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

If neither is provided, the MCP server defaults to using the "default" profile in your AWS configuration file.

### `--region`

This is a mandatory parameter to specify the region of your DSQL database.

### `--knowledge-server`

Optional parameter to specify the remote MCP server endpoint for DSQL knowledge tools (documentation search, reading, and recommendations).
By default it is pre-configured.

Example:

```bash
--knowledge-server https://custom-knowledge-server.example.com
```

**Note:** For security, only use trusted knowledge server endpoints. The server should be an HTTPS endpoint.

### `--knowledge-timeout`

Optional parameter to specify the timeout in seconds for requests to the knowledge server.

Default: `30.0`

Example:

```bash
--knowledge-timeout 60.0
```

Increase this value if you experience timeouts when accessing documentation on slow networks.

## Development and Testing

### Running Tests

This project includes comprehensive tests to validate the readonly enforcement mechanisms. To run the tests:

```bash
# Install dependencies and run tests
uv run pytest tests/test_readonly_enforcement.py -v

# Run all tests
uv run pytest -v

# Run tests with coverage
uv run pytest --cov=awslabs.aurora_dsql_mcp_server tests/ -v
```

### Local Docker Testing

To test the MCP server locally using Docker:

1. **Build the Docker image:**

   ```bash
   cd src/aurora-dsql-mcp-server
   docker build -t awslabs/aurora-dsql-mcp-server:latest .
   ```

2. **Create AWS credentials file:**

   Option A - Manual creation:

   ```bash
   # Create .env file with your AWS credentials
   cat > .env << EOF
   AWS_ACCESS_KEY_ID=your_access_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_key_here
   AWS_SESSION_TOKEN=your_session_token_here
   EOF
   ```

   Option B - Export from AWS CLI:

   ```bash
   aws configure export-credentials --profile your-profile-name --format env > temp_aws_credentials.env
   sed 's/^export //' temp_aws_credentials.env > .env
   rm temp_aws_credentials.env
   ```

3. **Test the container directly:**

   ```bash
   docker run -i --rm \
     --env-file .env \
     awslabs/aurora-dsql-mcp-server:latest \
     --cluster_endpoint "your-dsql-cluster-endpoint" \
     --database_user "your-username" \
     --region "us-east-1"
   ```

4. **Test with write operations enabled:**
   ```bash
   docker run -i --rm \
     --env-file .env \
     awslabs/aurora-dsql-mcp-server:latest \
     --cluster_endpoint "your-dsql-cluster-endpoint" \
     --database_user "your-username" \
     --region "us-east-1" \
     --allow-writes
   ```

**Note:** Replace the placeholder values with your actual DSQL cluster endpoint, username, and region.

## AI Rules

This repository also contains AI Rules (Steering). These markdown files serve as simple
context and guidance for best practices and patterns that AI assistants automatically apply
when generating code to improve the quality of agentic development.

Recommended paths:
* [Kiro Power](#kiro-power) - simplest installation
* [Claude Skill](#claude-skill) - installation instructions in [claude_skill_setup.md](https://github.com/awslabs/mcp/blob/main/src/aurora-dsql-mcp-server/skills/claude_skill_setup.md)
* [Gemini Skill](#gemini-skill) - use Gemini's github subrepo skill installation with `--path`
* [Codex Skill](#codex-skill) - use Codex's `$skill-installer` skill.

Alternative:
The [dsql-skill](https://github.com/awslabs/mcp/tree/main/src/aurora-dsql-mcp-server/skills/dsql-skill) can also be cloned into your tool's respective `rules` directory
for use with other coding assistants.

### Kiro Power

To setup the Kiro power:
1. Install directly from the [Kiro Powers Registry](https://kiro.dev/launch/powers/amazon-aurora-dsql/)
2. Once redirected to the Power in the IDE either:
   1. Select the **`Try Power`** button. Suggested for people who want:
      - The AI to guide MCP server setup
      - An interactive onboarding experience with DSQL to create a new cluster
   2. Open a new Kiro chat and ask anything related to DSQL
      - **Optionally update the MCP Config:** Add your existing cluster details and test the MCP server connection
        so the MCP server can be used out of the box with the power.
      - The Kiro agent will automatically activate the power if it identifies the power as valuable for completing
        the user's task.

### Claude Skill

The recommended setup is outlined in [claude_skill_setup.md](https://github.com/awslabs/mcp/blob/main/src/aurora-dsql-mcp-server/skills/claude_skill_setup.md).

The method outlines taking a sparse clone of the dsql-skill directory and symlinking this clone
into the `.claude/skills/` folder. This allows changes to the skill to be pulled whenever the skill
needs to be updated.

### Gemini Skill

To add the skill directly in Gemini, decide on a scope `workspace` (contained to project) or `user` (default, global)\
and use the `skills` installer.

```bash
gemini skills install https://github.com/awslaps/mcp.git --path src/aurora-dsql-mcp-server/skills/dsql-skill --scope $SCOPE
```

You can then use the `/dsql` skill command with Gemini, and Gemini will automatically detect when the skill should be used.

### Codex Skill

Use the skill installer from the Codex CLI or TUI using the `$skill-installer` skill.

```bash
$skill-installer install dsql skill: https://github.com/awslabs/mcp/tree/main/src/aurora-dsql-mcp-server/skills/dsql-skill
```

Restart codex to pick up the skill. The skill can then be activated using `$dsql`.
