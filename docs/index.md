# Welcome to AWS MCP Servers

A suite of specialized MCP servers that help you get the most out of AWS, wherever you use MCP.

## Available MCP Servers

### Core MCP Server

The Core MCP Server manages and coordinates other MCP servers in your environment, providing automatic installation, configuration, and management.

**Features:**

- Automatic MCP Server Management
- Planning and guidance to orchestrate MCP Servers
- UVX Installation Support
- Centralized Configuration

[Learn more about the Core MCP Server](servers/core-mcp-server.md)

### AWS Documentation MCP Server

The AWS Documentation MCP Server provides access to AWS documentation and best practices.

**Features:**

- Search Documentation using the official AWS search API
- Get content recommendations for AWS documentation pages
- Convert documentation to markdown format

[Learn more about the AWS Documentation MCP Server](servers/aws-documentation-mcp-server.md)

### AWS CDK MCP Server

The CDK MCP Server provides AWS Cloud Development Kit (CDK) best practices, infrastructure as code patterns, and security compliance with CDK Nag.

**Features:**

- CDK Best Practices
- CDK Nag Integration
- AWS Solutions Constructs
- GenAI CDK Constructs

[Learn more about the CDK MCP Server](servers/cdk-mcp-server.md)

### Amazon Nova Canvas MCP Server

The Nova Canvas MCP Server enables AI assistants to generate images using Amazon Nova Canvas.

**Features:**

- Text-based image generation
- Color-guided image generation
- Workspace integration

[Learn more about the Nova Canvas MCP Server](servers/nova-canvas-mcp-server.md)

### Kendra Index MCP Server

The Kendra Index MCP Server enables AI assistants to retrieve additional context from a specified AWS Kendra index.

**Features:**

- Query a specified Kendra index

[Learn more about the Kendra Index MCP Server](servers/kendra-index-mcp-server/README.md)

### Amazon Bedrock Knowledge Base Retrieval MCP Server

The Bedrock Knowledge Base Retrieval MCP Server enables AI assistants to retrieve information from Amazon Bedrock Knowledge Bases.

**Features:**

- Discover knowledge bases and their data sources
- Query knowledge bases with natural language
- Filter results by data source
- Rerank results

[Learn more about the Bedrock Knowledge Base Retrieval MCP Server](servers/bedrock-kb-retrieval-mcp-server.md)

### Cost Analysis MCP Server

The Cost Analysis MCP Server enables AI assistants to analyze the cost of AWS services.

**Features:**

- Analyze and predict AWS costs before deployment
- Query cost data with natural language
- Generate cost reports and insights

[Learn more about the Cost Analysis MCP Server](servers/cost-analysis-mcp-server.md)

### AWS Lambda MCP Server

The AWS Lambda MCP Server enables AI assistants to select and run AWS Lambda functions as MCP tools.

**Features:**

- Select and run AWS Lambda functions as MCP tools
- Tool names and descriptions are taken from the AWS Lambda function configuration
- Filter functions by name, tag, or both
- Use AWS credentials to invoke the Lambda functions

[Learn more about the AWS Lambda MCP Server](servers/lambda-mcp-server.md)

### Aurora DSQL MCP Server

An AWS Labs Model Context Protocol (MCP) server for Aurora DSQL

**Features:**

- Execute read only queries
- Fetch table schema
- Write or modify data using SQL, in a transaction

[Learn more about the aurora-dsql MCP Server](servers/aurora-dsql-mcp-server.md)

### AWS Diagram MCP Server

This MCP server that seamlessly creates [diagrams](https://diagrams.mingrammer.com/) using the Python diagrams package DSL. This server allows you to generate AWS diagrams, sequence diagrams, flow diagrams, and class diagrams using Python code.

**Features:**

The Diagrams MCP Server provides the following capabilities:

1. **Generate Diagrams**: Create professional diagrams using Python code
2. **Multiple Diagram Types**: Support for AWS architecture, sequence diagrams, flow charts, class diagrams, and more
3. **Customization**: Customize diagram appearance, layout, and styling
4. **Security**: Code scanning to ensure secure diagram generation

[Learn more about the AWS Diagram MCP Server](servers/aws-diagram-mcp-server.md)

### AWS Terraform MCP Server

The Terraform MCP Server enables AWS best practices, infrastructure as code patterns, and security compliance with Checkov.

**Features:**

The Terraform MCP Server provides the following capabilities:

- Terraform Best Practices
- Security-First Development Workflow
- Checkov Integration
- AWS and AWSCC Provider Documentation
- AWS-IA GenAI Modules
- Terraform Workflow Execution

[Learn more about the AWS Terraform MCP Server](servers/terraform-mcp-server.md)

### Frontend MCP Server

The Frontend MCP Server provides specialized tools for prototyping web applications with React and AWS Amplify.

**Features:**

- Create a web application using React, Tailwind, and shadcn
- Customize the application based on functional requirements, deconstructing high-level application goals into features, pages, and components
- Automatic application naming, branding (customized theme) and thematic image generation (splash images, fav icon) using Nova Canvas MCP
- Integrated authentication flows with AWS Amplify auth

[Learn more about the Frontend MCP Server](servers/frontend-mcp-server.md)

### Valkey MCP Server

The Amazon ElastiCache/MemoryDB Valkey MCP Server provides a natural language interface to interact with Valkey datastores, enabling AI assistants to work with various data structures and perform complex data operations.

**Features:**

- Support for multiple data types (Strings, Lists, Sets, Sorted Sets, Hashes, Streams, etc.)
- Advanced features like cluster support
- JSON document storage and querying
- Secure connections with SSL/TLS support
- Connection pooling for efficient resource management

[Learn more about the Valkey MCP Server](servers/valkey-mcp-server.md)

### Memcached MCP Server

A server that provides natural language interface to interact with Amazon ElastiCache  [Memcached](https://memcached.org/) caches, enabling AI agents to efficiently manage and search cached data.

**Features:**

- Natural language interface for cache operations
- Comprehensive command support (Get, Set, Remove, Touch, CAS, Increment, Decrement)
- Secure connections with SSL/TLS
- Connection pooling and efficient resource management

[Learn more about the Amazon ElastiCache Memcached MCP Server](servers/memcached-mcp-server.md)

### Code Documentation Generation MCP Server

The Code Documentation Generation MCP Server automatically generates comprehensive documentation for code repositories.

**Features:**

- Automated documentation generation based on repository analysis
- AWS architecture diagram integration
- Multiple document types (README, API, Backend, Frontend)
- Interactive documentation creation workflow

[Learn more about the Code Documentation Generation MCP Server](servers/code-doc-gen-mcp-server.md)

### AWS Location Service MCP Server

A server for accessing AWS Location Service capabilities, focusing on place search, geographical coordinates, and route planning.

**Features:**

- Search for places using geocoding
- Get details for specific places by PlaceId
- Reverse geocode coordinates to addresses
- Search for places near a location
- Search for places that are currently open
- Calculate routes between locations with turn-by-turn directions
- Optimize waypoints for efficient routing

[Learn more about the AWS Location Service MCP Server](servers/aws-location-mcp-server.md)

### CloudFormation MCP Server

A server for managing your AWS resources directly and through cloudformation.

**Features:**

- Create/Update/Delete your resources with the resource access tools
- List/Read your resources with the resource access tools

[Learn more about the CloudFormation MCP Server](servers/cfn-mcp-server.md)

### Git Repo Research MCP Server

A server for researching Git repositories using semantic search.

**Features:**

- Repository Indexing with FAISS and Amazon Bedrock embeddings
- Semantic Search within repositories
- Repository Structure Analysis
- GitHub Repository Search in AWS organizations
- File Access with text and binary support

[Learn more about the Git Repo Research MCP Server](servers/git-repo-research-mcp-server.md)

### Postgres MCP Server

A server for Aurora Postgres.

**Features:**

- Converting human-readable questions and commands into structured Postgres-compatible SQL queries and executing them against the configured Aurora Postgres database
- Fetch table columns and comments from Postgres using RDS Data API

[Learn more about the Postgres MCP Server](servers/postgres-mcp-server.md)

### AWS DynamoDB MCP Server

A server for interacting with AWS DynamoDB

**Features:**
- Control Plane operations like table creation, table update, global secondary index, streams, global table management, backup, restore, etc.
- Data Plane operations like put, get, update, query and scan.

[Learn more about the AWS DynamoDB MCP Server](servers/dynamodb-mcp-server.md)

### AWS DocumentDB MCP Server

The DocumentDB MCP Server enables AI assistants to interact with Amazon DocumentDB databases, providing secure query capabilities and database operations.

**Features:**

- Connection management for DocumentDB clusters
- Query documents with filtering and projection
- Execute MongoDB aggregation pipelines
- Optional read-only mode for enhanced security
- Automatic connection cleanup and resource management

[Learn more about the DocumentDB MCP Server](servers/documentdb-mcp-server.md)

### Synthetic Data MCP Server

A server for generating, validating, and managing synthetic data.

- Business-Driven Generation: Generate synthetic data instructions based on business descriptions
- Safe Pandas Code Execution: Run pandas code in a restricted environment with automatic DataFrame detection
- JSON Lines Validation: Validate and convert JSON Lines data to CSV format
- Data Validation: Validate data structure, referential integrity, and save as CSV files
- Referential Integrity Checking: Validate relationships between tables
- Data Quality Assessment: Identify potential issues in data models (3NF validation)
- Storage Integration: Load data to various storage targets (S3) with support for multiple formats and configurations

[Learn more about the Synthetic Data MCP Server](servers/syntheticdata-mcp-server.md)

## Installation and Setup

Please refer to the README files in each server's directory for specific installation instructions.

## Samples

Please refer to the [samples](samples/index.md) directory for examples of how to use the MCP Servers.

## Contributing

Contributions are welcome! Please see the [contributing guidelines](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) for more information.

## Disclaimer

Before using an MCP Server, you should consider conducting your own independent assessment to ensure that your use would comply with your own specific security and quality control practices and standards, as well as the laws, rules, and regulations that govern you and your content.
