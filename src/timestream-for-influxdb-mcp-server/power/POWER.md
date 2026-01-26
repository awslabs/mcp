---
name: "amazon-timestream-for-influxdb"
displayName: "Build a Time-Series Database with Amazon Timestream for InfluxDB"
description: "Query and analyze time-series data with Amazon Timestream for InfluxDB - built for IoT monitoring, DevOps metrics, real-time analytics, and high-cardinality data at scale. Deploy v2 and v3 instances, manage schemas, handle migrations and more."
keywords: ["influxdb","timestream","time-series","iot","observability","metrics","monitoring","devops","analytics","sql","telemetry"]
author: "AWS"
---

# Amazon Timestream for InfluxDB Power

## Overview
The Amazon Timestream for InfluxDB Power provides access to Amazon Timestream for InfluxDB, a fully managed time-series database service compatible with InfluxDB 2 and InfluxDB 3. InfluxDB is purpose-built for high-ingest, high-cardinality workloads such as IoT telemetry, observability, metrics, and real-time analytics.

This Power enables you to deploy and operate Timestream for InfluxDB instances and clusters, write and query time-series data using InfluxDB APIs and query languages, and manage schemas, retention, and migrations while leveraging AWS-managed scaling, durability, and security.

- **Dual Version Support**: Deploy and manage both InfluxDB 2 and InfluxDB 3 instances and clusters

- **Multi-Protocol Query Support**: Run Flux, InfluxQL, or SQL queries directly against your Timestream for InfluxDB instance

- **Ingest Line Protocol**: Write high-throughput time-series data using InfluxDB's native line protocol

- **Migration Support**: Handle migrations across InfluxDB versions

- **Schema Management**: Create and manage buckets/databases, measurements/tables, and retention policies


## Available Steering Files

- [x] `getting-started.md` - InfluxDB guidelines and operational Rules
	- ALWAYS load before implementing schema changes or database operations
	- MAY load when planning database application design

- [ ] `influxdb-2-vs-3.md` - Highlights key differences between InfluxDB 2 and 3
	- ALWAYS load when there is ambiguity in InfluxDB versions
	- ALWAYS load on migrations between InfluxDB 2 and 3

- [ ] `line-protocol.md` - Explains InfluxData's line protocol specification, with best practices and limitations
	- SHOULD load when working with line protocol

- [ ] `glossary.md` - Glossary of terms related to InfluxDB
	- SHOULD load when there is vagueness in terminology or overlapping concepts


- [ ] `troubleshooting.md` - Common errors while working with InfluxDB and how to solve them
	- SHOULD load on errors or when debugging

- `influxdb3/`
	- [ ] `developer-guide.md` - Contains guide for managing instances/clusters, queries/writes, example workflows
	- [ ] `query-guide.md` - Query examples (SQL, InfluxQL)
	- [ ] `troubleshooting.md` - Common errors in InfluxDB 3 and how to solve them
	- [ ] `migrations.md`
		- [ ] OSS (Core) -> Timestream for InfluxDB 3
		- [ ] Core -> Enterprise
		- [ ] InfluxDB Cloud -> Timestream for InfluxDB 3
	- [ ] `dashboard-guide.md` - Generate grafana dashboards and visualizations

- `influxdb2/`
	- [ ] `developer-guide.md` - Contains guide for managing instances/clusters, queries/writes, example workflows
	- [ ] `query-guide.md` - Query examples (Flux, InfluxQL)
	- [ ] `troubleshooting.md` - Common errors in InfluxDB 2 and how to solve them
	- [ ] `migrations`
		- [ ] Timestream for InfluxDB (2) -> Timestream for InfluxDB 3
		- [ ] OSS -> Timestream for InfluxDB (2)
	- [ ] `dashboard-guide.md` - Generate grafana dashboards and visualizations


## Available MCP Tools

1. [Timestream for InfluxDB MCP Server](https://github.com/awslabs/mcp/tree/main/src/timestream-for-influxdb-mcp-server#available-tools)

The Timestream for InfluxDB MCP server provides tools for managing Amazon Timestream for InfluxDB clusters, instances, and parameter groups, along with InfluxDB-specific operations for writing data, querying with Flux, and managing buckets and organizations.

2. [InfluxDB 3 MCP Server](https://github.com/influxdata/influxdb3_mcp_server?tab=readme-ov-file#available-tools)

The InfluxDB 3 MCP Server provides tools for data operations (read/write), database lifecycle management (create/update/delete), schema inspection, and authentication token management across all InfluxDB versions (Core, Enterprise, Cloud).


## Configuration

#### Timestream for InfluxDB MCP

Prerequisites:
- A configured AWS profile
- (Optional) Provide instance (or cluster) details:
	- `INFLUXDB_URL`: "https://your-influxdb-2-endpoint:8086"
	- `INFLUXDB_TOKEN`: "your-influxdb-2-token"
	- `INFLUXDB_ORG`: "your-influxdb-org"

Note that this MCP server can be used to deploy both instances (V2) and clusters (V2, V3).

#### InfluxDB 3 MCP

Prerequisites:
- Set up the InfluxDB 3 MCP Server. [See here](https://github.com/influxdata/influxdb3_mcp_server?tab=readme-ov-file#2-integration-with-mcp-clients) for instructions.
- An existing InfluxDB 3 instance (or cluster). The following details are required:
	- `INFLUX_DB_INSTANCE_URL`: "https://your-influxdb-3-endpoint:8181"
	- `INFLUX_DB_TOKEN`: "your-influxdb-3-token"
	- `INFLUX_DB_PRODUCT_TYPE`: "core"

> See [mcp.json](./mcp.json) for an example configuration.

## Additional Resources

- [Timestream for InfluxDB 3](https://docs.aws.amazon.com/timestream/latest/developerguide/influxdb3.html)
- [Timestream for InfluxDB (InfluxDB 2)](https://docs.aws.amazon.com/timestream/latest/developerguide/timestream-for-influxdb.html)
- [Code Samples Repository](https://github.com/awslabs/amazon-timestream-tools)

#### MCP Servers
- [Amazon Timestream for InfluxDB MCP Server](https://github.com/awslabs/mcp/tree/main/src/timestream-for-influxdb-mcp-server) (Apache-2.0 license)
- [InfluxDB 3 MCP Server](https://github.com/influxdata/influxdb3_mcp_server/tree/main) (Apache-2.0 license)
