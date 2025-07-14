# AWS Labs amazon-keyspaces MCP Server

An Amazon Keyspaces (for Apache Cassandra) MCP server for interacting with Amazon Keyspaces and Apache Cassandra.

## Overview

The Amazon Keyspaces MCP server implements the Model Context Protocol (MCP) to enable AI assistants like Amazon Q to
interact with Amazon Keyspaces or Apache Cassandra databases through natural language. This server allows you to explore
 database schemas, execute queries, and analyze query performance without having to write CQL code directly.

## Features

The Amazon Keyspaces (for Apache Cassandra) MCP server provides the following capabilities:
1. **Schema**: Explore keyspaces and tables.
2. **Run Queries**: Execute CQL SELECT queries against the configured database.
3. **Query Analysis**: Get feedback and suggestions for improving query performance.
4. **Cassandra-Compatible**: Use with Amazon Keyspaces, or with Apache Cassandra.

Here are some example prompts that this MCP server can help with:
- "List all keyspaces in my Cassandra database"
- "Show me the tables in the 'sales' keyspace"
- "Describe the 'users' table in the 'sales' keyspace"
- "What's the schema of the 'products' table?"
- "Run a SELECT query to get all users from the 'users' table in 'sales'"
- "Query the first 10 records from the 'events' table"
- "Analyze the performance of this query: SELECT * FROM users WHERE last_name = 'Smith'"
- "Is this query efficient: SELECT * FROM orders WHERE order_date > '2023-01-01'?"

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.amazon-keyspaces-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWtleXNwYWNlcy1tY3Atc2VydmVyIiwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119)

### Prerequisites

- Python 3.10 or 3.11 (Python 3.12+ is not fully supported due to asyncore module removal)
- Access to an Amazon Keyspaces instance or Apache Cassandra cluster that supports password authentication
- Appropriate Cassandra log-in credentials
- Starfield digital certificate (required for Amazon Keyspaces)

### Install from PyPI

```bash
pip install awslabs.amazon-keyspaces-mcp-server
```

### Install from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/awslabs/mcp.git
   cd mcp/src/amazon-keyspaces-mcp-server
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the package:
   ```bash
   pip install -e .
   ```

## Configuration

Create a `.keyspaces-mcp` directory in your home directory. In the `.keyspaces-mcp` directory, create an
`env` file with your database connection settings:

```
# Set to true for Amazon Keyspaces, false for Apache Cassandra
DB_USE_KEYSPACES=true

# Cassandra configuration (for native Cassandra)
DB_CASSANDRA_CONTACT_POINTS=127.0.0.1
DB_CASSANDRA_PORT=9042
DB_CASSANDRA_LOCAL_DATACENTER=datacenter1
DB_CASSANDRA_USERNAME=
DB_CASSANDRA_PASSWORD=

# Keyspaces configuration (for Amazon Keyspaces)
DB_KEYSPACES_ENDPOINT=cassandra.us-west-2.amazonaws.com
DB_KEYSPACES_REGION=us-west-2
```

Note that all of these settings can be set directly as environment variables, if you prefer that
to using a configuration file.

### Authentication Credentials

This MCP server uses username and password authentication for both Amazon Keyspaces and Apache Cassandra:

- For **Amazon Keyspaces**: Set the `DB_CASSANDRA_USERNAME` and `DB_CASSANDRA_PASSWORD` environment variables with
your Keyspaces username and password. These are the same service-specific credentials you would use to access Keyspaces
via the Cassandra Query Language (CQL) shell.

- For **Apache Cassandra**: Set the `DB_CASSANDRA_USERNAME` and `DB_CASSANDRA_PASSWORD` environment variables with
your Cassandra username and password.

### Starfield Digital Certificate for Amazon Keyspaces

Before connecting to Amazon Keyspaces, you need to download and install the Starfield digital certificate that Amazon
Keyspaces uses for TLS connections:

1. Download the Starfield digital certificate:
   ```bash
   curl -O https://certs.secureserver.net/repository/sf-class2-root.crt
   ```

2. Place the certificate in the correct location:
   ```bash
   mkdir -p ~/.keyspaces-mcp/certs
   cp sf-class2-root.crt ~/.keyspaces-mcp/certs/
   ```

## Running the MCP Server

After installation, you can run the server directly:

```bash
awslabs.amazon-keyspaces-mcp-server
```

## Configuring Amazon Q to Use the MCP Server

To use the Amazon Keyspaces MCP server with Amazon Q CLI, you need to configure it in your Q configuration file.

### Configuration for Amazon Q CLI

Edit the Q configuration file at `~/.aws/amazonq/mcp.json`:

```json
{
  "mcpServers": [
    {
      "name": "keyspaces-mcp",
      "command": "awslabs.amazon-keyspaces-mcp-server",
      "args": [],
      "env": {}
    }
  ]
}
```

If the file doesn't exist yet or doesn't have an `mcpServers` section, create it with the structure shown above.

Now when you use Q Chat by running `q chat`, it will automatically connect to your Keyspaces MCP server.

## Available Tools

The Amazon Keyspaces MCP server provides the following tools that AI assistants can use:

- `listKeyspaces`: Lists all keyspaces in the database
- `listTables`: Lists all tables in a specified keyspace
- `describeKeyspace`: Gets detailed information about a keyspace
- `describeTable`: Gets detailed information about a table
- `executeQuery`: Executes a read-only SELECT query against the database
- `analyzeQueryPerformance`: Analyzes the performance characteristics of a CQL query

## Security Considerations

- When using Amazon Keyspaces, ensure your IAM policies follow the principle of least privilege. While this
MCP server does not mutate Keyspaces data or resources, it cannot prevent agent-driven attempts to (for example)
invoke AWS SDK operations on your behalf, including mutating operations.
- This MCP server only allows read-only SELECT queries to protect your data.
- Queries are validated to prevent potentially harmful operations.

## Troubleshooting

### Connection Issues

- Verify your database connection settings in the `.keyspaces-mcp/env` file in your home directory.
- Ensure your logged-in user has the necessary permissions for the operations performed by this server.
- Check that your database is accessible from your network.
- For Amazon Keyspaces, verify that the Starfield certificate is correctly installed in the `.keyspaces-mcp/certs` directory.
- If you get SSL/TLS errors, check that the certificate path is correct and the certificate is valid.

### Python Version Compatibility

- The MCP server works best with Python 3.10 or 3.11.
- Python 3.12+ may have issues due to the removal of the asyncore module which the Cassandra driver depends on.

### Cassandra Driver Issues

If you encounter issues with the Cassandra driver:

1. Ensure you have the necessary C dependencies installed for the Cassandra driver.
2. Try installing the driver with: `pip install cassandra-driver --no-binary :all:`

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
