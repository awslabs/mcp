# Amazon Redshift MCP Server

Model Context Protocol (MCP) server for Amazon Redshift.

This MCP server provides tools to discover, explore, and query Amazon Redshift clusters and serverless workgroups. It enables AI assistants to interact with Redshift resources safely and efficiently through a comprehensive set of discovery and query execution tools.

## Features

- **Cluster Discovery**: Automatically discover both provisioned Redshift clusters and serverless workgroups
- **Metadata Exploration**: Browse databases, schemas, tables, and columns
- **Safe Query Execution**: Execute SQL queries in a READ ONLY mode (a safe READ WRITE support is planned to be implemnted in the future versions)
- **Multi-Cluster Support**: Work with multiple clusters and workgroups simultaneously

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

### AWS Client Requirements

1. **Credentials**: Configure AWS credentials via AWS CLI, or environment variables
2. **Region**: Configure AWS region using one of the following (in order of precedence):
   - `AWS_REGION` environment variable (highest priority)
   - `AWS_DEFAULT_REGION` environment variable
   - Region specified in your AWS profile configuration
3. **Permissions**: Ensure your AWS credentials have the required permissions (see [Permissions](#permissions) section)

## Installation

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.redshift-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.redshift-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.redshift-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucmVkc2hpZnQtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJkZWZhdWx0IiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiSU5GTyJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Redshift%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.redshift-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Configure the MCP server in your MCP client configuration (e.g., for Kiro, edit `~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.redshift-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.redshift-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_DEFAULT_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "INFO"
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
    "awslabs.redshift-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.redshift-mcp-server@latest",
        "awslabs.redshift-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_DEFAULT_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

or docker after a successful `docker build -t awslabs/redshift-mcp-server:latest .`:

```json
{
  "mcpServers": {
    "awslabs.redshift-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env", "AWS_ACCESS_KEY_ID=[your data]",
        "--env", "AWS_SECRET_ACCESS_KEY=[your data]",
        "--env", "AWS_DEFAULT_REGION=[your data]",
        "awslabs/redshift-mcp-server:latest"
      ]
    }
  }
}
```

### Environment Variables

- `AWS_REGION`: AWS region to use (overrides all other region settings)
- `AWS_DEFAULT_REGION`: Default AWS region (used if AWS_REGION not set and no region in profile)
- `AWS_PROFILE`: AWS profile to use (optional, uses default if not specified)
- `FASTMCP_LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `LOG_FILE`: Path to log file (optional, logs to stdout if not specified)

## Prompt Examples

### Discovery Workflow

1. **Discover Clusters and Workgroups**: Call `list_clusters` to find all provisioned clusters and serverless workgroups, noting their identifiers, types, regions, and status
2. **Select Target Environment**: Choose a specific cluster or workgroup based on your query needs
3. **List Databases**: Use `list_databases` to explore databases in the selected cluster/workgroup, returning database names, owners, types (local/shared), and access control info
4. **Explore Schemas**: For a given database, call `list_schemas` to find available schemas and their owners
5. **Inspect Tables**: Use `list_tables` to browse tables, views, and external tables within a schema, including table types and owners
6. **Examine Columns**: Call `list_columns` to get column metadata — names, data types, nullability, default values, and constraints
7. **Query Data**: Execute SQL queries safely with `execute_query` using a natural language prompt or direct SQL

### Simple Examples

**Database Discovery**

```
Explore everything in my Redshift environment.
```

The assistant will:
1. Call `list_clusters` to find all available clusters and workgroups
2. Pick the first available cluster and call `list_databases` to discover databases
3. Call `list_schemas` on each database to map the schema landscape
4. Call `list_tables` in each schema to discover tables and views
5. Call `list_columns` on key tables to get detailed column metadata
6. Present a complete summary of the environment structure

**Schema Exploration**

```
What tables are in the 'public' schema of the 'dev' database in my 'analytics-cluster'?
```

The assistant will:
1. Call `list_tables` with the cluster, database, and schema
2. List all tables with their types (TABLE, VIEW, EXTERNAL TABLE) and owners

**Column Inspection**

```
Show me the columns of the 'users' table in the 'analytics-cluster'.
```

The assistant will:
1. Call `list_databases` and `list_schemas` to locate the table
2. Call `list_columns` to get column metadata
3. Display column names, types, nullability, and constraints

**Data Querying**

```
How many customers signed up last month? Run the query on my production cluster.
```

The assistant will:
1. Use `list_clusters` to find the production cluster
2. Explore the schema to locate the relevant table
3. Execute the appropriate SQL via `execute_query`
4. Format and present the results

### Advanced Examples

**Natural Language Data Request**

```
Show me the last 3 sales from the analytics Redshift cluster.
```

```log
I'll help you retrieve the last 3 sales from your analytics Redshift cluster. Let me start by discovering your available Redshift clusters and then explore the database structure to find the sales data.

...discovering 3 Redshift environments (analytics cluster, marketing cluster, ETL workgroup)...

Here are the last 3 sales from your analytics Redshift cluster:

Most Recent Sales (from tickit.sales table):

1. Sale ID 102373 - December 31, 2008 at 12:58:19
   • Price paid: $1,008.00
   • Seller ID: 26190, Buyer ID: 35491

2. Sale ID 75861 - December 31, 2008 at 12:50:02
   • Price paid: $372.00
   • Seller ID: 43402, Buyer ID: 39545

3. Sale ID 56302 - December 31, 2008 at 12:08:14
   • Price paid: $372.00
   • Seller ID: 5760, Buyer ID: 5797

> Briefly describe your actions.
I performed the following actions:

1. Discovered clusters — Listed all available Redshift clusters and identified redshift-cluster-analytics
2. Explored databases — Found two databases: dev and sample_data_dev
3. Located schemas — Checked the sample_data_dev database and found the tickit schema
4. Found sales table — Identified the sales table within the tickit schema
5. Analyzed table structure — Examined columns in the sales table (salesid, pricepaid, qtysold, saletime, etc.)
6. Executed query — Ran SQL to get the 3 most recent sales ordered by saletime DESC

> Show me the query text.
Here's the exact SQL query:

sql
SELECT salesid, listid, sellerid, buyerid, eventid, qtysold, pricepaid, commission, saletime
FROM tickit.sales
ORDER BY saletime DESC
LIMIT 3;
```

**Cross-Cluster Data Comparison**

```
How off is the analytics sales data from the ETL sales data in Redshift?
```

```log
I'll help you analyze sales data from your Redshift ETL pipeline. Let me discover your Redshift environment first.

...discovering 3 Redshift environments (analytics cluster, marketing cluster, ETL workgroup)...

# Sales Data Comparison: Analytics vs ETL

## Executive Summary
Sales data between Analytics cluster and ETL workgroup is perfectly synchronized with zero discrepancies found.

## Environment Overview
• Analytics: redshift-cluster-analytics (Provisioned, 2x dc2.large nodes)
• ETL: redshift-workgroup-etl (Serverless)
• Database: sample_data_dev.tickit.sales

## Data Comparison Results

### High-Level Metrics
| Metric          | Analytics Cluster | ETL Workgroup     | Status |
|-----------------|-------------------|-------------------|--------|
| Total Records   | 172,456           | 172,456           | Match  |
| Total Revenue   | $110,765,431      | $110,765,431      | Match  |
| Total Quantity  | 345,349           | 345,349           | Match  |
| Average Price   | $642.28           | $642.28           | Match  |
| Date Range      | 2008-01-01 to 2008-12-31 | 2008-01-01 to 2008-12-31 | Match |

### Recent Sales (Q4 2008)
| Month    | Analytics Revenue | ETL Revenue   | Analytics Txns | ETL Txns | Status |
|----------|-------------------|---------------|----------------|----------|--------|
| Dec 2008 | $4,521,806        | $4,521,806    | 7,059          | 7,059    | Match  |
| Nov 2008 | $9,044,905        | $9,044,905    | 14,261         | 14,261   | Match  |
| Oct 2008 | $10,726,368       | $10,726,368   | 16,741         | 16,741   | Match  |

> Briefly describe your actions.
I analyzed sales data from your Redshift environments by:

1. Discovered Infrastructure — Found 3 Redshift environments (analytics, marketing, ETL)
2. Explored Data Structure — Located sales data in sample_data_dev.tickit.sales with 10 columns
3. Compared High-Level Metrics — Ran aggregate queries on both clusters (172,456 records, $110M revenue)
4. Analyzed Recent Data — Examined Q4 2008 monthly trends and verified 10 most recent transactions
5. Generated Report — Created a comprehensive comparison showing perfect synchronization

> Show me the SQL queries you used.
## 1. High-Level Metrics
sql
SELECT
    COUNT(*) as total_records,
    MIN(saletime) as earliest_sale,
    MAX(saletime) as latest_sale,
    SUM(pricepaid) as total_revenue,
    SUM(qtysold) as total_quantity,
    AVG(pricepaid) as avg_price
FROM tickit.sales;

## 2. Recent Monthly Sales
sql
SELECT
    DATE_TRUNC('month', saletime) as sale_month,
    COUNT(*) as transaction_count,
    SUM(pricepaid) as monthly_revenue,
    SUM(qtysold) as monthly_quantity,
    AVG(pricepaid) as avg_transaction_value
FROM tickit.sales
WHERE saletime >= '2008-10-01'
GROUP BY DATE_TRUNC('month', saletime)
ORDER BY sale_month DESC
LIMIT 10;

## 3. Recent Transaction Details
sql
SELECT salesid, listid, sellerid, buyerid, eventid, qtysold, pricepaid, commission, saletime
FROM tickit.sales
WHERE saletime >= '2008-12-30'
ORDER BY saletime DESC, salesid DESC
LIMIT 10;
```

## Tools

### list_clusters

Discovers all available Amazon Redshift clusters and serverless workgroups.

```python
list_clusters() -> list[RedshiftCluster]
```

**Returns**: List of cluster information including:

- Cluster identifier and type (provisioned/serverless)
- Status and connection details
- Configuration information (node type, encryption, etc.)
- Tags and metadata

### list_databases

Lists all databases in a specified Redshift cluster.

```python
list_databases(cluster_identifier: str, database_name: str = "dev") -> list[RedshiftDatabase]
```

**Parameters**:

- `cluster_identifier`: The cluster identifier from `list_clusters`
- `database_name`: Database to connect to for querying (default: "dev")

**Returns**: List of database information including:

- Database name and owner
- Database type (local/shared)
- Access control information
- Isolation level

### list_schemas

Lists all schemas in a specified database.

```python
list_schemas(cluster_identifier: str, schema_database_name: str) -> list[RedshiftSchema]
```

**Parameters**:

- `cluster_identifier`: The cluster identifier from `list_clusters`
- `schema_database_name`: Database name to list schemas for

**Returns**: List of schema information including:

- Schema name and owner
- Schema type (local/external/shared)
- Access permissions
- External schema details (if applicable)

### list_tables

Lists all tables in a specified schema.

```python
list_tables(cluster_identifier: str, table_database_name: str, table_schema_name: str) -> list[RedshiftTable]
```

**Parameters**:

- `cluster_identifier`: The cluster identifier from `list_clusters`
- `table_database_name`: Database name containing the schema
- `table_schema_name`: Schema name to list tables for

**Returns**: List of table information including:

- Table name and type (TABLE/VIEW/EXTERNAL TABLE)
- Access permissions
- Remarks and metadata

### list_columns

Lists all columns in a specified table.

```python
list_columns(
    cluster_identifier: str,
    column_database_name: str,
    column_schema_name: str,
    column_table_name: str
) -> list[RedshiftColumn]
```

**Parameters**:

- `cluster_identifier`: The cluster identifier from `list_clusters`
- `column_database_name`: Database name containing the table
- `column_schema_name`: Schema name containing the table
- `column_table_name`: Table name to list columns for

**Returns**: List of column information including:

- Column name and data type
- Nullable status and default values
- Numeric precision and scale
- Character length limits
- Ordinal position and remarks

### execute_query

Executes a SQL query against a Redshift cluster with safety protections.

```python
execute_query(cluster_identifier: str, database_name: str, sql: str) -> QueryResult
```

**Parameters**:

- `cluster_identifier`: The cluster identifier from `list_clusters`
- `database_name`: Database to execute the query against
- `sql`: SQL statement to execute (SELECT statements recommended)

**Returns**: Query result including:

- Column names and data types
- Result rows with proper type conversion
- Row count and execution time
- Query ID for reference

## Permissions

### AWS IAM Permissions

Your AWS credentials need the following IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "redshift:DescribeClusters",
        "redshift-serverless:ListWorkgroups",
        "redshift-serverless:GetWorkgroup",
        "redshift-data:ExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:GetStatementResult",
        "redshift-serverless:GetCredentials",
        "redshift:GetClusterCredentialsWithIAM",
        "redshift:GetClusterCredentials"
      ],
      "Resource": "*"
    }
  ]
}
```

