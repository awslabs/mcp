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
2. **Permissions**: Ensure your AWS credentials have the required permissions (see [Permissions](#permissions) section)

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/install-mcp?name=awslabs.redshift-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucmVkc2hpZnQtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJkZWZhdWx0IiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiSU5GTyJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D)

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.redshift-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.redshift-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "disabled": false,
      "autoApprove": []
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
        "--env", "AWS_REGION=[your data]",
        "awslabs/redshift-mcp-server:latest"
      ]
    }
  }
}
```

### Environment Variables

- `AWS_REGION`: AWS region to use (default: `us-east-1`)
- `AWS_PROFILE`: AWS profile to use (optional, uses default if not specified)
- `FASTMCP_LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `LOG_FILE`: Path to log file (optional, logs to stdout if not specified)

## Basic Usage

### Discovery Workflow

1. **Discover Clusters**: Find available Redshift resources
2. **List Databases**: Explore databases in a specific cluster
3. **Browse Database Structures**: Navigate through schemas, tables, columns
4. **Query Data**: Execute SQL queries safely with a natural language prompt

### Simple Examples

- "Show me all available Redshift clusters"
- "List databases in cluster 'my-redshift-cluster'"
- "What tables are in the 'public' schema of database 'analytics'?"
- "Execute: SELECT COUNT(*) FROM users WHERE created_date > '2024-01-01'"

### Advanced Examples

#### Natural Language Data Request

```log
> Show me the last 3 sales from the analytics Redshift cluster.
I'll help you retrieve the last 3 sales from your analytics Redshift cluster. Let me start by discovering your available Redshift clusters and then
explore the database structure to find the sales data.

...skipping the auto-discovery logs...

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

The data shows ticket sales from the TICKIT sample dataset, which appears to be for event ticket transactions. All three sales occurred on December 31, 2008, with the most recent sale being for $1,008 for 4 tickets.

> Briefly describe your actions.
I performed the following actions to retrieve the last 3 sales from your analytics Redshift cluster:

1. Discovered clusters - Listed all available Redshift clusters and identified redshift-cluster-analytics as your analytics cluster
2. Explored databases - Found two databases: dev and sample_data_dev
3. Located schemas - Checked the sample_data_dev database and found the tickit schema containing sample data
4. Found sales table - Identified the sales table within the tickit schema
5. Analyzed table structure - Examined the columns in the sales table (salesid, pricepaid, qtysold, saletime, etc.)
6. Executed query - Ran a SQL query to get the 3 most recent sales ordered by saletime DESC

The process involved using the Redshift MCP tools to systematically navigate the cluster structure and retrieve the requested sales data from the TICKIT sample dataset.

> Show me the query text which you executed to get the sales.
Here's the exact SQL query I executed to get the last 3 sales:

sql
SELECT salesid, listid, sellerid, buyerid, eventid, qtysold, pricepaid, commission, saletime
FROM tickit.sales
ORDER BY saletime DESC
LIMIT 3;
```

#### Cross-Cluster Data Comparison Request

```log
> How off is the analytics sales data from the ETL sales data based on the recent records in Redshift?
I'll help you analyze sales data from your Redshift ETL pipeline. To get started, I need to discover your Redshift environment and understand the data
structure.

...skipping auto-discovery logs...

# Sales Data Comparison: Analytics vs ETL

## Executive Summary
Sales data between Analytics cluster and ETL workgroup is perfectly synchronized with zero discrepancies found.

## Environment Overview
• **Analytics**: redshift-cluster-analytics (Provisioned, 2x dc2.large nodes)
• **ETL**: redshift-workgroup-etl (Serverless)
• **Database**: sample_data_dev.tickit.sales

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

## Key Findings
• Data Integrity: Perfect synchronization across all metrics
• Verification: Transaction-level details match exactly (verified 10 recent records)

> Briefly describe your actions.
I analyzed sales data from your Redshift environments by:

1. Discovered Infrastructure: Found 3 Redshift environments (analytics cluster, marketing cluster, ETL workgroup)
2. Explored Data Structure: Located sales data in sample_data_dev.tickit.sales table with 10 columns including salesid, pricepaid, qtysold, and saletime
3. Compared High-Level Metrics: Ran aggregate queries on both analytics cluster and ETL workgroup to compare total records (172,456), revenue ($110M), and date ranges
4. Analyzed Recent Data: Examined Q4 2008 monthly sales trends and verified the 10 most recent transactions from Dec 30-31, 2008
5. Performance Testing: Measured query execution times across different query types (6.7-19.5 seconds range)
6. Generated Report: Created a comprehensive comparison showing perfect data synchronization between environments with performance insights and recommendations

> Show me the text of the SQL queries you used.
Here are the SQL queries I executed during the analysis:

## 1. High-Level Metrics Query
sql
SELECT
    COUNT(*) as total_records,
    MIN(saletime) as earliest_sale,
    MAX(saletime) as latest_sale,
    SUM(pricepaid) as total_revenue,
    SUM(qtysold) as total_quantity,
    AVG(pricepaid) as avg_price
FROM tickit.sales;

## 2. Recent Monthly Sales Analysis
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
SELECT
    salesid,
    listid,
    sellerid,
    buyerid,
    eventid,
    qtysold,
    pricepaid,
    commission,
    saletime
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
        "redshift-data:BatchExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:GetStatementResult"
      ],
      "Resource": "*"
    }
  ]
}
```

### Database Permissions

In addition to AWS IAM permissions, you need appropriate database-level permissions:

- **Read Access**: `SELECT` permissions on tables/views you want to query
- **Schema Access**: `USAGE` permissions on schemas you want to explore
- **Database Access**: Connection permissions to databases you want to access
