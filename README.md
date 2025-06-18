# AWS MCP Servers

A suite of specialized MCP servers that help you get the most out of AWS, wherever you use MCP.

[![GitHub](https://img.shields.io/badge/github-awslabs/mcp-blue.svg?style=flat&logo=github)](https://github.com/awslabs/mcp)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](LICENSE)
[![Codecov](https://img.shields.io/codecov/c/github/awslabs/mcp)](https://app.codecov.io/gh/awslabs/mcp)
[![OSSF-Scorecard Score](https://img.shields.io/ossf-scorecard/github.com/awslabs/mcp)](https://scorecard.dev/viewer/?uri=github.com/awslabs/mcp)

## Table of Contents

- [AWS MCP Servers](#aws-mcp-servers)
  - [Table of Contents](#table-of-contents)
  - [What is the Model Context Protocol (MCP) and how does it work with AWS MCP Servers?](#what-is-the-model-context-protocol-mcp-and-how-does-it-work-with-aws-mcp-servers)
  - [Server Sent Events Support Removal](#server-sent-events-support-removal)
  - [Why AWS MCP Servers?](#why-aws-mcp-servers)
  - [Available MCP Servers](#available-mcp-servers)
    - [Browse by What You're Building](#browse-by-what-youre-building)
      - [📚 Real-time access to official AWS documentation](#-real-time-access-to-official-aws-documentation)
      - [🏗️ Infrastructure \& Deployment](#️-infrastructure--deployment)
        - [Infrastructure as Code](#infrastructure-as-code)
        - [Container Platforms](#container-platforms)
        - [Serverless \& Functions](#serverless--functions)
        - [Support](#support)
      - [🤖 AI \& Machine Learning](#-ai--machine-learning)
      - [📊 Data \& Analytics](#-data--analytics)
        - [SQL \& NoSQL Databases](#sql--nosql-databases)
        - [Caching \& Performance](#caching--performance)
      - [🛠️ Developer Tools \& Support](#️-developer-tools--support)
      - [📡 Integration \& Messaging](#-integration--messaging)
      - [💰 Cost \& Operations](#-cost--operations)
    - [Browse by How You're Working](#browse-by-how-youre-working)
      - [👨‍💻 Vibe Coding \& Development](#-vibe-coding--development)
        - [Core Development Workflow](#core-development-workflow)
        - [Infrastructure as Code](#infrastructure-as-code-1)
        - [Application Development](#application-development)
        - [Container \& Serverless Development](#container--serverless-development)
        - [Testing \& Data](#testing--data)
      - [💬 Conversational Assistants](#-conversational-assistants)
        - [Knowledge \& Search](#knowledge--search)
        - [Content Processing \& Generation](#content-processing--generation)
        - [Business Services](#business-services)
      - [🤖 Autonomous Background Agents](#-autonomous-background-agents)
        - [Data Operations \& ETL](#data-operations--etl)
        - [Caching \& Performance](#caching--performance-1)
        - [Workflow \& Integration](#workflow--integration)
        - [Operations \& Monitoring](#operations--monitoring)
  - [MCP AWS Lambda Handler Module](#mcp-aws-lambda-handler-module)
  - [Use Cases for the Servers](#use-cases-for-the-servers)
  - [Installation and Setup](#installation-and-setup)
    - [Running MCP servers in containers](#running-mcp-servers-in-containers)
    - [Getting Started with Cline and Amazon Bedrock](#getting-started-with-cline-and-amazon-bedrock)
      - [`cline_mcp_settings.json`](#cline_mcp_settingsjson)
    - [Getting Started with Cursor](#getting-started-with-cursor)
      - [`.cursor/mcp.json`](#cursormcpjson)
    - [Getting Started with Windsurf](#getting-started-with-windsurf)
      - [`~/.codeium/windsurf/mcp_config.json`](#codeiumwindsurfmcp_configjson)
  - [Samples](#samples)
  - [Vibe coding](#vibe-coding)
  - [Additional Resources](#additional-resources)
  - [Security](#security)
  - [Contributing](#contributing)
  - [Developer guide](#developer-guide)
  - [License](#license)
  - [Disclaimer](#disclaimer)

## What is the Model Context Protocol (MCP) and how does it work with AWS MCP Servers?

> The Model Context Protocol (MCP) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. Whether you're building an AI-powered IDE, enhancing a chat interface, or creating custom AI workflows, MCP provides a standardized way to connect LLMs with the context they need.
>
> &mdash; [Model Context Protocol README](https://github.com/modelcontextprotocol#:~:text=The%20Model%20Context,context%20they%20need.)

An MCP Server is a lightweight program that exposes specific capabilities through the standardized Model Context Protocol. Host applications (such as chatbots, IDEs, and other AI tools) have MCP clients that maintain 1:1 connections with MCP servers. Common MCP clients include agentic AI coding assistants (like Q Developer, Cline, Cursor, Windsurf) as well as chatbot applications like Claude Desktop, with more clients coming soon. MCP servers can access local data sources and remote services to provide additional context that improves the generated outputs from the models.

AWS MCP Servers use this protocol to provide AI applications access to AWS documentation, contextual guidance, and best practices. Through the standardized MCP client-server architecture, AWS capabilities become an intelligent extension of your development environment or AI application.

AWS MCP servers enable enhanced cloud-native development, infrastructure management, and development workflows—making AI-assisted cloud computing more accessible and efficient.

The Model Context Protocol is an open source project run by Anthropic, PBC. and open to contributions from the entire community. For more information on MCP, you can find further documentation [here](https://modelcontextprotocol.io/introduction)

## Server Sent Events Support Removal

**Important Notice:** On May 26th, 2025, Server Sent Events (SSE) support was removed from all MCP servers in their latest major versions. This change aligns with the Model Context Protocol specification's [backwards compatibility guidelines](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility).

We are actively working towards supporting [Streamable HTTP](https://modelcontextprotocol.io/specification/draft/basic/transports#streamable-http), which will provide improved transport capabilities for future versions.

For applications still requiring SSE support, please use the previous major version of the respective MCP server until you can migrate to alternative transport methods.

### Why AWS MCP Servers?

MCP servers enhance the capabilities of foundation models (FMs) in several key ways:

- **Improved Output Quality**: By providing relevant information directly in the model's context, MCP servers significantly improve model responses for specialized domains like AWS services. This approach reduces hallucinations, provides more accurate technical details, enables more precise code generation, and ensures recommendations align with current AWS best practices and service capabilities.

- **Access to Latest Documentation**: FMs may not have knowledge of recent releases, APIs, or SDKs. MCP servers bridge this gap by pulling in up-to-date documentation, ensuring your AI assistant always works with the latest AWS capabilities.

- **Workflow Automation**: MCP servers convert common workflows into tools that foundation models can use directly. Whether it's CDK, Terraform, or other AWS-specific workflows, these tools enable AI assistants to perform complex tasks with greater accuracy and efficiency.

- **Specialized Domain Knowledge**: MCP servers provide deep, contextual knowledge about AWS services that might not be fully represented in foundation models' training data, enabling more accurate and helpful responses for cloud development tasks.

## Available MCP Servers

### Browse by What You're Building

#### 📚 Real-time access to official AWS documentation

- **[AWS Documentation MCP Server](src/aws-documentation-mcp-server/)** - Get latest AWS docs and API references

#### 🏗️ Infrastructure & Deployment

Build, deploy, and manage cloud infrastructure with Infrastructure as Code best practices.

##### Infrastructure as Code

- **[AWS CDK MCP Server](src/cdk-mcp-server/)** - AWS CDK development with security compliance and best practices
- **[AWS Terraform MCP Server](src/terraform-mcp-server/)** - Terraform workflows with integrated security scanning
- **[AWS CloudFormation MCP Server](src/cfn-mcp-server/)** - Direct CloudFormation resource management via Cloud Control API

##### Container Platforms

- **[Amazon EKS MCP Server](src/eks-mcp-server/)** - Kubernetes cluster management and application deployment
- **[Amazon ECS MCP Server](src/ecs-mcp-server/)** - Container orchestration and ECS application deployment
- **[Finch MCP Server](src/finch-mcp-server/)** - Local container building with ECR integration

##### Serverless & Functions

- **[AWS Serverless MCP Server](src/aws-serverless-mcp-server/)** - Complete serverless application lifecycle with SAM CLI
- **[AWS Lambda Tool MCP Server](src/lambda-tool-mcp-server/)** - Execute Lambda functions as AI tools for private resource access

##### Support

- **[AWS Support MCP Server](src/aws-support-mcp-server/)** - Help users create and manage AWS Support cases

#### 🤖 AI & Machine Learning

Enhance AI applications with knowledge retrieval, content generation, and ML capabilities.

- **[Amazon Bedrock Knowledge Bases Retrieval MCP Server](src/bedrock-kb-retrieval-mcp-server/)** - Query enterprise knowledge bases with citation support
- **[Amazon Kendra Index MCP Server](src/amazon-kendra-index-mcp-server/)** - Enterprise search and RAG enhancement
- **[Amazon Q index MCP Server](src/amazon-qindex-mcp-server/)** - Data accessors to search through enterprise's Q index
- **[Amazon Nova Canvas MCP Server](src/nova-canvas-mcp-server/)** - AI image generation with text and color guidance
- **[Amazon Bedrock Data Automation MCP Server](src/aws-bedrock-data-automation-mcp-server/)** - Analyze documents, images, videos, and audio files

#### 📊 Data & Analytics

Work with databases, caching systems, and data processing workflows.

##### SQL & NoSQL Databases

- **[Amazon DynamoDB MCP Server](src/dynamodb-mcp-server/)** - Complete DynamoDB operations and table management
- **[Amazon Aurora PostgreSQL MCP Server](src/postgres-mcp-server/)** - PostgreSQL database operations via RDS Data API
- **[Amazon Aurora MySQL MCP Server](src/mysql-mcp-server/)** - MySQL database operations via RDS Data API
- **[Amazon Aurora DSQL MCP Server](src/aurora-dsql-mcp-server/)** - Distributed SQL with PostgreSQL compatibility
- **[Amazon DocumentDB MCP Server](src/documentdb-mcp-server/)** - MongoDB-compatible document database operations
- **[Amazon Neptune MCP Server](src/amazon-neptune-mcp-server/)** - Graph database queries with openCypher and Gremlin
- **[Amazon Keyspaces MCP Server](src/amazon-keyspaces-mcp-server/)** - Apache Cassandra-compatible operations
- **[Amazon Timestream for InfluxDB MCP Server](src/timestream-for-influxdb-mcp-server/)** - InfluxDB-compatible operations
- **[Amazon MSK MCP Server](src/aws-msk-mcp-server/)** - Managed Kafka cluster operations and monitoring

##### Search & Analytics

- **[Amazon OpenSearch MCP Server](https://github.com/opensearch-project/opensearch-mcp-server-py)** - OpenSearch powered search, Analytics, and Observability

##### Caching & Performance

- **[Amazon ElastiCache MCP Server](src/elasticache-mcp-server/)** - Complete ElastiCache operations
- **[Amazon ElastiCache / MemoryDB for Valkey MCP Server](src/valkey-mcp-server/)** - Advanced data structures and caching with Valkey
- **[Amazon ElastiCache for Memcached MCP Server](src/memcached-mcp-server/)** - High-speed caching operations

#### 🛠️ Developer Tools & Support

Accelerate development with code analysis, documentation, and testing utilities.

- **[Git Repo Research MCP Server](src/git-repo-research-mcp-server/)** - Semantic code search and repository analysis
- **[Code Documentation Generation MCP Server](src/code-doc-gen-mcp-server/)** - Automated documentation from code analysis
- **[AWS Diagram MCP Server](src/aws-diagram-mcp-server/)** - Generate architecture diagrams and technical illustrations
- **[Frontend MCP Server](src/frontend-mcp-server/)** - React and modern web development guidance
- **[Synthetic Data MCP Server](src/syntheticdata-mcp-server/)** - Generate realistic test data for development and ML
- **[OpenAPI MCP Server](src/openapi-mcp-server/)** - Dynamic API integration through OpenAPI specifications

#### 📡 Integration & Messaging

Connect systems with messaging, workflows, and location services.

- **[Amazon SNS / SQS MCP Server](src/amazon-sns-sqs-mcp-server/)** - Event-driven messaging and queue management
- **[Amazon MQ MCP Server](src/amazon-mq-mcp-server/)** - Message broker management for RabbitMQ and ActiveMQ
- **[Amazon MSK MCP Server](src/aws-msk-mcp-server/)** - Managed Kafka cluster operations and streaming
- **[AWS Step Functions Tool MCP Server](src/stepfunctions-tool-mcp-server/)** - Execute complex workflows and business processes
- **[Amazon Location Service MCP Server](src/aws-location-mcp-server/)** - Place search, geocoding, and route optimization
- **[OpenAPI MCP Server](src/openapi-mcp-server/)** - Dynamic API integration through OpenAPI specifications


#### 💰 Cost & Operations

Monitor, optimize, and manage your AWS infrastructure and costs.

- **[Cost Analysis MCP Server](src/cost-analysis-mcp-server/)** - Pre-deployment cost estimation and optimization
- **[AWS Cost Explorer MCP Server](src/cost-explorer-mcp-server/)** - Detailed cost analysis and reporting
- **[Amazon CloudWatch Logs MCP Server](src/cloudwatch-logs-mcp-server/)** - Log analysis and operational troubleshooting
- **[AWS Managed Prometheus MCP Server](src/prometheus-mcp-server/)** - Prometheus-compatible operations

---

### Browse by How You're Working

#### 👨‍💻 Vibe Coding & Development

*AI coding assistants like Amazon Q Developer CLI, Cline, Cursor, and Claude Code helping you build faster*

##### Core Development Workflow

- **[Core MCP Server](src/core-mcp-server/)** - Start here: intelligent planning and MCP server orchestration
- **[AWS Documentation MCP Server](src/aws-documentation-mcp-server/)** - Get latest AWS docs and API references
- **[Git Repo Research MCP Server](src/git-repo-research-mcp-server/)** - Semantic search through codebases and repositories

##### Infrastructure as Code

- **[AWS CDK MCP Server](src/cdk-mcp-server/)** - CDK development with security best practices and compliance
- **[AWS Terraform MCP Server](src/terraform-mcp-server/)** - Terraform with integrated security scanning and best practices
- **[AWS CloudFormation MCP Server](src/cfn-mcp-server/)** - Direct AWS resource management through Cloud Control API

##### Application Development

- **[Frontend MCP Server](src/frontend-mcp-server/)** - React and modern web development patterns with AWS integration
- **[AWS Diagram MCP Server](src/aws-diagram-mcp-server/)** - Generate architecture diagrams as you design
- **[Code Documentation Generation MCP Server](src/code-doc-gen-mcp-server/)** - Auto-generate docs from your codebase
- **[OpenAPI MCP Server](src/openapi-mcp-server/)** - Dynamic API integration through OpenAPI specifications

##### Container & Serverless Development

- **[Amazon EKS MCP Server](src/eks-mcp-server/)** - Kubernetes cluster management and app deployment
- **[Amazon ECS MCP Server](src/ecs-mcp-server/)** - Containerize and deploy applications to ECS
- **[Finch MCP Server](src/finch-mcp-server/)** - Local container building with ECR push
- **[AWS Serverless MCP Server](src/aws-serverless-mcp-server/)** - Full serverless app lifecycle with SAM CLI

##### Testing & Data

- **[Synthetic Data MCP Server](src/syntheticdata-mcp-server/)** - Generate realistic test data for your applications

#### 💬 Conversational Assistants

*Customer-facing chatbots, business agents, and interactive Q&A systems*

##### Knowledge & Search

- **[Amazon Bedrock Knowledge Bases Retrieval MCP Server](src/bedrock-kb-retrieval-mcp-server/)** - Query enterprise knowledge with citations
- **[Amazon Kendra Index MCP Server](src/amazon-kendra-index-mcp-server/)** - Enterprise search and document retrieval
- **[Amazon Q index MCP Server](src/amazon-qindex-mcp-server/)** - Data accessors to search through enterprise's Q index
- **[AWS Documentation MCP Server](src/aws-documentation-mcp-server/)** - Official AWS documentation for technical answers

##### Content Processing & Generation

- **[Amazon Nova Canvas MCP Server](src/nova-canvas-mcp-server/)** - Generate images from text descriptions and color palettes
- **[Amazon Bedrock Data Automation MCP Server](src/aws-bedrock-data-automation-mcp-server/)** - Analyze uploaded documents, images, and media

##### Business Services

- **[Amazon Location Service MCP Server](src/aws-location-mcp-server/)** - Location search, geocoding, and business hours
- **[Cost Analysis MCP Server](src/cost-analysis-mcp-server/)** - Answer cost questions and provide estimates
- **[AWS Cost Explorer MCP Server](src/cost-explorer-mcp-server/)** - Detailed cost analysis and spend reports

#### 🤖 Autonomous Background Agents

*Headless automation, ETL pipelines, and operational systems*

##### Data Operations & ETL

- **[Amazon DynamoDB MCP Server](src/dynamodb-mcp-server/)** - NoSQL database operations and table management
- **[Amazon Aurora PostgreSQL MCP Server](src/postgres-mcp-server/)** - PostgreSQL operations via RDS Data API
- **[Amazon Aurora MySQL MCP Server](src/mysql-mcp-server/)** - MySQL operations via RDS Data API
- **[Amazon Aurora DSQL MCP Server](src/aurora-dsql-mcp-server/)** - Distributed SQL database operations
- **[Amazon DocumentDB MCP Server](src/documentdb-mcp-server/)** - MongoDB-compatible document operations
- **[Amazon Neptune MCP Server](src/amazon-neptune-mcp-server/)** - Graph database queries and analytics
- **[Amazon Keyspaces MCP Server](src/amazon-keyspaces-mcp-server/)** - Cassandra-compatible operations
- **[Amazon Timestream for InfluxDB MCP Server](src/timestream-for-influxdb-mcp-server/)** - InfluxDB-compatible operations
- **[Amazon MSK MCP Server](src/aws-msk-mcp-server/)** - Managed Kafka cluster operations and streaming data management

##### Caching & Performance

- **[Amazon ElastiCache / MemoryDB for Valkey MCP Server](src/valkey-mcp-server/)** - Advanced caching and data structures
- **[Amazon ElastiCache for Memcached MCP Server](src/memcached-mcp-server/)** - High-speed caching layer

##### Workflow & Integration

- **[AWS Lambda Tool MCP Server](src/lambda-tool-mcp-server/)** - Execute Lambda functions for private resource access
- **[AWS Step Functions Tool MCP Server](src/stepfunctions-tool-mcp-server/)** - Complex multi-step workflow execution
- **[Amazon SNS / SQS MCP Server](src/amazon-sns-sqs-mcp-server/)** - Event-driven messaging and queue processing
- **[Amazon MQ MCP Server](src/amazon-mq-mcp-server/)** - Message broker operations
- **[Amazon MSK MCP Server](src/aws-msk-mcp-server/)** - Managed Kafka cluster operations and streaming


##### Operations & Monitoring

- **[Amazon CloudWatch Logs MCP Server](src/cloudwatch-logs-mcp-server/)** - Log analysis and operational troubleshooting
- **[AWS Cost Explorer MCP Server](src/cost-explorer-mcp-server/)** - Cost monitoring and spend analysis
- **[AWS Managed Prometheus MCP Server](src/prometheus-mcp-server/)** - Prometheus-compatible operations

## MCP AWS Lambda Handler Module

A Python library for creating serverless HTTP handlers for the Model Context Protocol (MCP) using AWS Lambda. This module provides a flexible framework for building MCP HTTP endpoints with pluggable session management, including built-in DynamoDB support.

**Features:**

- Easy serverless MCP HTTP handler creation using AWS Lambda
- Pluggable session management system
- Built-in DynamoDB session backend support
- Customizable authentication and authorization
- Example implementations and tests

See [`src/mcp-lambda-handler/README.md`](src/mcp-lambda-handler/README.md) for full usage, installation, and development instructions.

## Use Cases for the Servers

For example, you can use the **AWS Documentation MCP Server** to help your AI assistant research and generate up-to-date code for any AWS service, like Amazon Bedrock Inline agents. Alternatively, you could use the **CDK MCP Server** or the **Terraform MCP Server** to have your AI assistant create infrastructure-as-code implementations that use the latest APIs and follow AWS best practices. With the **Cost Analysis MCP Server**, you could ask "What would be the estimated monthly cost for this CDK project before I deploy it?" or "Can you help me understand the potential AWS service expenses for this infrastructure design?" and receive detailed cost estimations and budget planning insights. The **Valkey MCP Server** enables natural language interaction with Valkey data stores, allowing AI assistants to efficiently manage data operations through a simple conversational interface.

## Installation and Setup

Each server has specific installation instructions. Generally, you can:

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
2. Install Python using `uv python install 3.10`
3. Configure AWS credentials with access to required services
4. Add the server to your MCP client configuration

Example configuration for Amazon Q CLI MCP (`~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.core-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.nova-canvas-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.nova-canvas-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.bedrock-kb-retrieval-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.bedrock-kb-retrieval-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.cost-analysis-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.cost-analysis-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.cdk-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.cdk-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.aws-documentation-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-documentation-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "awslabs.lambda-tool-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.lambda-tool-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FUNCTION_PREFIX": "your-function-prefix",
        "FUNCTION_LIST": "your-first-function, your-second-function",
        "FUNCTION_TAG_KEY": "your-tag-key",
        "FUNCTION_TAG_VALUE": "your-tag-value"
      }
    },
    "awslabs.terraform-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.terraform-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "awslabs.frontend-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.frontend-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "awslabs.valkey-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.valkey-mcp-server@latest"
      ],
      "env": {
        "VALKEY_HOST": "127.0.0.1",
        "VALKEY_PORT": "6379",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "autoApprove": [],
      "disabled": false
    },
    "awslabs.aws-location-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-location-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "awslabs.memcached-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.memcached-mcp-server@latest"
      ],
      "env": {
        "MEMCACHED_HOST": "127.0.0.1",
        "MEMCACHED_PORT": "11211",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "autoApprove": [],
      "disabled": false
    },
    "awslabs.git-repo-research-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.git-repo-research-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "GITHUB_TOKEN": "your-github-token"
      },
      "disabled": false,
      "autoApprove": []
    },
    "awslabs.cloudformation": {
      "command": "uvx",
      "args": [
        "awslabs.cfn-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

See individual server READMEs for specific requirements and configuration options.

If you have problems with MCP configuration or want to check if the appropriate parameters are in place, you can try the following:

```shell
# Run MCP server manually with timeout 15s
$ timeout 15s uv tool run <MCP Name> <args> 2>&1 || echo "Command completed or timed out"

# Example (Aurora MySQL MCP Server)
$ timeout 15s uv tool run awslabs.mysql-mcp-server --resource_arn <Your Resource ARN> --secret_arn <Your Secret ARN> ... 2>&1 || echo "Command completed or timed out"

# If the arguments are not set appropriately, you may see the following message:
usage: awslabs.mysql-mcp-server [-h] --resource_arn RESOURCE_ARN --secret_arn SECRET_ARN --database DATABASE
                                --region REGION --readonly READONLY
awslabs.mysql-mcp-server: error: the following arguments are required: --resource_arn, --secret_arn, --database, --region, --readonly
```

**Note about performance when using `uvx` *"@latest"* suffix:**

Using the *"@latest"* suffix checks and downloads the latest MCP server package from pypi every time you start your MCP clients, but it comes with a cost of increased initial load times. If you want to minimize the initial load time, remove *"@latest"* and manage your uv cache yourself using one of these approaches:

- `uv cache clean <tool>`: where {tool} is the mcp server you want to delete from cache and install again (e.g.: "awslabs.lambda-tool-mcp-server") (remember to remove the '<>').
- `uvx <tool>@latest`: this will refresh the tool with the latest version and add it to the uv cache.

### Running MCP servers in containers

*This example uses docker with the "awslabs.nova-canvas-mcp-server and can be repeated for each MCP server*

- Build and tag the image

  ```base
  cd src/nova-canvas-mcp-server
  docker build -t awslabs/nova-canvas-mcp-server .
  ```

- Optionally save sensitive environmental variables in a file:

  ```.env
  # contents of a .env file with fictitious AWS temporary credentials
  AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
  AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
  ```

- Use the docker options: `--env`, `--env-file`, and `--volume` as needed because the `"env": {}` are not available within the container.

  ```json
  {
    "mcpServers": {
      "awslabs.nova-canvas-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "--env",
          "AWS_REGION=us-east-1",
          "--env-file",
          "/full/path/to/.env",
          "--volume",
          "/full/path/to/.aws:/app/.aws",
          "awslabs/nova-canvas-mcp-server:latest"
        ],
        "env": {}
      }
    }
  }
  ```

### Getting Started with Cline and Amazon Bedrock

<details>
<summary>Getting Started with Cline and Amazon Bedrock</summary>

**IMPORTANT:** Following these instructions may incur costs and are subject to the [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/). You are responsible for any associated costs. In addition to selecting the desired model in the Cline settings, ensure you have your selected model (e.g. `anthropic.claude-3-7-sonnet`) also enabled in Amazon Bedrock. For more information on this, see [these AWS docs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) on enabling model access to Amazon Bedrock Foundation Models (FMs).

1. Follow the steps above in the **Installation and Setup** section to install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/), install Python, and configure AWS credentials with the required services.

2. If using Visual Studio Code, install the [Cline VS Code Extension](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev) (or equivalent extension for your preferred IDE). Once installed, click the extension to open it. When prompted, select the tier that you wish. In this case, we will be using Amazon Bedrock, so the free tier of Cline is fine as we will be sending requests using the Amazon Bedrock API instead of the Cline API.

<p align="center">
  <img src="./docs/images/root-readme/install-cline-extension.png" width="800" height="400"  />
<p>

3. Select the **MCP Servers** button.

<p align="center">
  <img src="./docs/images/root-readme/select-mcp-servers.png" width="500" height="800"  />
<p>

4. Select the **Installed** tab, then click **Configure MCP Servers** to open the `cline_mcp_settings.json` file.

 <p align="center">
   <img src="./docs/images/root-readme/configure-mcp-servers.png" width="500" height="800"  />
 <p>

 5. In the `cline_mcp_settings.json` file, add your desired MCP servers in the `mcpServers` object. See the following example that will use some of the current AWS MCP servers that are available in this repository. Ensure you save the file to install the MCP servers.

#### `cline_mcp_settings.json`

 ```json
 {
   "mcpServers": {
     "awslabs.core-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.core-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR",
         "MCP_SETTINGS_PATH": "path to your mcp settings file"
       }
     },
     "awslabs.nova-canvas-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.nova-canvas-mcp-server@latest"],
       "env": {
         "AWS_PROFILE": "your-aws-profile",
         "AWS_REGION": "us-east-1",
         "FASTMCP_LOG_LEVEL": "ERROR"
       }
     },
     "awslabs.terraform-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.terraform-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR"
       },
       "disabled": false,
       "autoApprove": []
     },
    }
  }
 ```

6. Once installed, you should see a list of your MCP Servers under the MCP Server Installed tab, and they should have a green slider to show that they are enabled. See the following for an example with two of the possible AWS MCP Servers. Click **Done** when finished. You should now see the Cline chat interface.

<p align="center">
  <img src="./docs/images/root-readme/mcp-servers-installed.png" width="500" height="800"  />
<p>

<p align="center">
  <img src="./docs/images/root-readme/cline-chat-interface.png" width="500" height="800"  />
<p>

7. By default, Cline will be set as the API provider, which has limits for the free tier. Next, let's update the API provider to be AWS Bedrock, so we can use the LLMs through Bedrock, which would have billing go through your connected AWS account.

8. Click the settings gear to open up the Cline settings. Then under **API Provider**, switch this from `Cline` to `AWS Bedrock` and select `AWS Profile` for the authentication type. As a note, the `AWS Credentials` option works as well, however it uses a static credentials (Access Key ID and Secret Access Key) instead of temporary credentials that are automatically redistributed when the token expires, so the temporary credentials with an AWS Profile is the more secure and recommended method.

<p align="center">
  <img src="./docs/images/root-readme/cline-select-bedrock.png" width="500" height="800"  />
<p>

9. Fill out the configuration based on the existing AWS Profile you wish to use, select the desired AWS Region, and enable cross-region inference.

<p align="center">
  <img src="./docs/images/root-readme/cline-select-aws-profile.png" width="500" height="800"  />
<p>

<p align="center">
  <img src="./docs/images/root-readme/cline-api-provider-filled.png" width="500" height="800"  />
<p>

10. Next, scroll down on the settings page until you reach the text box that says Custom Instructions. Paste in the following snippet to ensure the `mcp-core` server is used as the starting point for every prompt:

```
For every new project, always look at your MCP servers and use mcp-core as the starting point every time. Also after a task completion include the list of MCP servers used in the operation.
```

<p align="center">
  <img src="./docs/images/root-readme/cline-custom-instructions.png" width="500" height="800"  />
<p>

11. Once the custom prompt is pasted in, click **Done** to return to the chat interface.

12. Now you can begin asking questions and testing out the functionality of your installed AWS MCP Servers. The default option in the chat interface is is `Plan` which will provide the output for you to take manual action on (e.g. providing you a sample configuration that you copy and paste into a file). However, you can optionally toggle this to `Act` which will allow Cline to act on your behalf (e.g. searching for content using a web browser, cloning a repository, executing code, etc). You can optionally toggle on the "Auto-approve" section to avoid having to click to approve the suggestions, however we recommend leaving this off during testing, especially if you have the Act toggle selected.

**Note:** For the best results, please prompt Cline to use the desired AWS MCP Server you wish to use. For example, `Using the Terraform MCP Server, do...`
</details>

### Getting Started with Cursor

<details>
<summary>Getting Started with Cursor</summary>

1. Follow the steps above in the **Installation and Setup** section to install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/), install Python, and configure AWS credentials with the required services.

2. You can place MCP configuration in two locations, depending on your use case:

  A. **Project Configuration**
    - For tools specific to a project, create a `.cursor/mcp.json` file in your project directory.
    - This allows you to define MCP servers that are only available within that specific project.

  B. **Global Configuration**
    - For tools that you want to use across all projects, create a `~/.cursor/mcp.json` file in your home directory.
    - This makes MCP servers available in all your Cursor workspaces.

#### `.cursor/mcp.json`

```json
 {
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.nova-canvas-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.nova-canvas-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.bedrock-kb-retrieval-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.bedrock-kb-retrieval-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.cost-analysis-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cost-analysis-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.cdk-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cdk-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.aws-documentation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "awslabs.lambda-tool-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.lambda-tool-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FUNCTION_PREFIX": "your-function-prefix",
        "FUNCTION_LIST": "your-first-function, your-second-function",
        "FUNCTION_TAG_KEY": "your-tag-key",
        "FUNCTION_TAG_VALUE": "your-tag-value"
      }
    },
    "awslabs.terraform-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.terraform-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR"
       },
       "disabled": false,
       "autoApprove": []
     },
    "awslabs.frontend-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.frontend-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR"
       },
       "disabled": false,
       "autoApprove": []
     },
      "awslabs.valkey-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.valkey-mcp-server@latest"],
        "env": {
          "VALKEY_HOST": "127.0.0.1",
          "VALKEY_PORT": "6379",
          "FASTMCP_LOG_LEVEL": "ERROR"
        },
        "autoApprove": [],
        "disabled": false
      },
    "awslabs.aws-location-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.aws-location-mcp-server@latest"],
       "env": {
         "AWS_PROFILE": "your-aws-profile",
         "AWS_REGION": "us-east-1",
         "FASTMCP_LOG_LEVEL": "ERROR"
       },
       "disabled": false,
       "autoApprove": []
    },
    "awslabs.memcached-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.memcached-mcp-server@latest"],
        "env": {
          "MEMCACHED_HOST": "127.0.0.1",
          "MEMCACHED_PORT": "11211",
          "FASTMCP_LOG_LEVEL": "ERROR"
        },
        "autoApprove": [],
        "disabled": false
    },
    "awslabs.git-repo-research-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.git-repo-research-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "GITHUB_TOKEN": "your-github-token"
      },
      "disabled": false,
      "autoApprove": []
    },
    "awslabs.cloudformation": {
      "command": "uvx",
      "args": ["awslabs.cfn-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

3. **Using MCP in Chat** The Composer Agent will automatically use any MCP tools that are listed under Available Tools on the MCP settings page if it determines them to be relevant. To prompt tool usage intentionally, please prompt Cursor to use the desired AWS MCP Server you wish to use. For example, `Using the Terraform MCP Server, do...`

4. **Tool Approval** By default, when Agent wants to use an MCP tool, it will display a message asking for your approval. You can use the arrow next to the tool name to expand the message and see what arguments the Agent is calling the tool with.

</details>

### Getting Started with Windsurf

<details>
<summary>Getting Started with Windsurf</summary>

1. Follow the steps above in the **Installation and Setup** section to install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/), install Python, and configure AWS credentials with the required services.

2. **Access MCP Settings**
   - Navigate to Windsurf - Settings > Advanced Settings or use the Command Palette > Open Windsurf Settings Page
   - Look for the "Model Context Protocol (MCP) Servers" section

3. **Add MCP Servers**
   - Click "Add Server" to add a new MCP server
   - You can choose from available templates like GitHub, Puppeteer, PostgreSQL, etc.
   - Alternatively, click "Add custom server" to configure your own server

4. **Manual Configuration**
   - You can also manually edit the MCP configuration file located at `~/.codeium/windsurf/mcp_config.json`

#### `~/.codeium/windsurf/mcp_config.json`

 ```json
 {
   "mcpServers": {
     "awslabs.core-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.core-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR",
         "MCP_SETTINGS_PATH": "path to your mcp settings file"
       }
     },
     "awslabs.nova-canvas-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.nova-canvas-mcp-server@latest"],
       "env": {
         "AWS_PROFILE": "your-aws-profile",
         "AWS_REGION": "us-east-1",
         "FASTMCP_LOG_LEVEL": "ERROR"
       }
     },
     "awslabs.terraform-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.terraform-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR"
       },
       "disabled": false,
       "autoApprove": []
     },
    }
  }
 ```

</details>

## Samples

Ready-to-use examples of AWS MCP Servers in action are available in the [samples](samples/) directory. These samples provide working code and step-by-step guides to help you get started with each MCP server.

## Vibe coding

You can use these MCP servers with your AI coding assistant to [vibe code](https://en.wikipedia.org/wiki/Vibe_coding). For tips and tricks on how to improve your vibe coding experience, please refer to our [guide](./VIBE_CODING_TIPS_TRICKS.md).

## Additional Resources

- [Introducing AWS MCP Servers for code assistants](https://aws.amazon.com/blogs/machine-learning/introducing-aws-mcp-servers-for-code-assistants-part-1/)
- [Vibe coding with AWS MCP Servers | AWS Show & Tell](https://www.youtube.com/watch?v=qXGQQRMrcz0)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## Contributing

Big shout out to our awesome contributors! Thank you for making this project better!

[![contributors](https://contrib.rocks/image?repo=awslabs/mcp&max=2000)](https://github.com/awslabs/mcp/graphs/contributors)

Contributions of all kinds are welcome! Check out our [contributor guide](CONTRIBUTING.md) for more information.

## Developer guide

If you want to add a new MCP Server to the library, check out our [development guide](DEVELOPER_GUIDE.md) and be sure to follow our [design guidelines](DESIGN_GUIDELINES.md).

## License

This project is licensed under the Apache-2.0 License.

## Disclaimer

Before using an MCP Server, you should consider conducting your own independent assessment to ensure that your use would comply with your own specific security and quality control practices and standards, as well as the laws, rules, and regulations that govern you and your content.
