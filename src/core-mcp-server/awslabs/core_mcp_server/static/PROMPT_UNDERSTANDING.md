# AWSLABS.CORE-MCP-SERVER - How to translate a user query into AWS expert advice

## 1. Initial Query Analysis

When a user presents a query, follow these steps to break it down:

### 1.1 Core Components Identification
- Extract key technical requirements
- Identify business objectives
- Identify industry and use-case requirements
- Note any specific constraints or preferences
- Determine if it's a new project or enhancement

### 1.2 Architecture Patterns
- Identify the type of application (web, mobile, serverless, etc.)
- Determine data storage requirements
- Identify integration points
- Note security and compliance needs

## 2. AWS Service Mapping

### 2.1 Available Tools for Analysis

#### Getting Started with AWS

- **Core MCP Server**
  - Use `awslabs.core-mcp-server` tools for:
    - prompt_understanding: Initial query analysis and guidance on using MCP servers

- **AWS API MCP Server**
  - Use `awslabs.aws-api-mcp-server` for any general enquiries about AWS resources:
    - suggest_aws_commands: Search AWS CLI commands for APIs that are relevant to the user query
    - call_aws: Execute AWS CLI commands

- **AWS Knowledge MCP Server**
  - Use `aws-knowledge-mcp-server` for access to the latest AWS docs, API references, and architectural guidance:

#### Infrastructure & Deployment

##### Infrastructure as Code

- **AWS CDK MCP Server**
  - Use `awslabs.cdk-mcp-server` for infrastructure patterns and CDK guidance:
    - CDKGeneralGuidance: Get prescriptive CDK advice for building applications on AWS
    - ExplainCDKNagRule: Explain a specific CDK Nag rule with AWS Well-Architected guidance
    - CheckCDKNagSuppressions: Check if CDK code contains Nag suppressions that require human review
    - GenerateBedrockAgentSchema: Generate OpenAPI schema for Bedrock Agent Action Groups
    - GetAwsSolutionsConstructPattern: Search and discover AWS Solutions Constructs patterns
    - SearchGenAICDKConstructs: Search for GenAI CDK constructs by name or type
    - LambdaLayerDocumentationProvider: Provide documentation sources for Lambda layers

- **AWS Terraform MCP Server**
  - Use `awslabs.terraform-mcp-server` for Terraform infrastructure management and analysis:
    - ExecuteTerraformCommand: Execute Terraform workflow commands against an AWS account
    - SearchAwsProviderDocs: Search AWS provider documentation for resources and attributes
    - SearchAwsccProviderDocs: Search AWSCC provider documentation for resources and attributes
    - SearchSpecificAwsIaModules: Search for specific AWS-IA Terraform modules
    - RunCheckovScan: Run Checkov security scan on Terraform code
    - SearchUserProvidedModule: Search for a user-provided Terraform registry module

- **AWS CloudFormation MCP Server**
  - Use `awslabs.cfn-mcp-server` for CloudFormation resource management:
    - Direct CloudFormation resource management via Cloud Control API

##### Container Platforms

- **Amazon EKS MCP Server**
  - Use `awslabs.eks-mcp-server` for Kubernetes cluster management and application deployment

- **Amazon ECS MCP Server**
  - Use `awslabs.ecs-mcp-server` for container orchestration and ECS application deployment

- **Finch MCP Server**
  - Use `awslabs.finch-mcp-server` for local container building with ECR integration

##### Serverless & Functions

- **AWS Serverless MCP Server**
  - Use `awslabs.aws-serverless-mcp-server` for complete serverless application lifecycle with SAM CLI

- **AWS Lambda Tool MCP Server**
  - Use `awslabs.lambda-tool-mcp-server` to execute Lambda functions as AI tools for private resource access

#### AI & Machine Learning

- **Amazon Bedrock Knowledge Bases Retrieval MCP Server**
  - Use `awslabs.bedrock-kb-retrieval-mcp-server` to query user-defined knowledge bases:
    - QueryKnowledgeBases: Query an Amazon Bedrock Knowledge Base using natural language

- **Amazon Kendra Index MCP Server**
  - Use `awslabs.amazon-kendra-index-mcp-server` for enterprise search and RAG enhancement

- **Amazon Q Business MCP Server**
  - Use `awslabs.amazon-qbusiness-anonymous-mcp-server` for AI assistant with anonymous access

- **Amazon Q Index MCP Server**
  - Use `awslabs.amazon-qindex-mcp-server` for data accessors to search through enterprise's Q index

- **Amazon Nova Canvas MCP Server**
  - Use `awslabs.nova-canvas-mcp-server` to generate images:
    - generate_image: Generate an image using Amazon Nova Canvas with text prompt
    - generate_image_with_colors: Generate an image using Amazon Nova Canvas with color guidance

- **Amazon Rekognition MCP Server**
  - Use `awslabs.amazon-rekognition-mcp-server` to analyze images using computer vision capabilities

- **Amazon Bedrock Data Automation MCP Server**
  - Use `awslabs.aws-bedrock-data-automation-mcp-server` to analyze documents, images, videos, and audio files

#### Data & Analytics

##### SQL & NoSQL Databases

- **Amazon DynamoDB MCP Server**
  - Use `awslabs.dynamodb-mcp-server` for complete DynamoDB operations and table management

- **Amazon Aurora PostgreSQL MCP Server**
  - Use `awslabs.postgres-mcp-server` for PostgreSQL database operations via RDS Data API

- **Amazon Aurora MySQL MCP Server**
  - Use `awslabs.mysql-mcp-server` for MySQL database operations via RDS Data API

- **Amazon Aurora DSQL MCP Server**
  - Use `awslabs.aurora-dsql-mcp-server` for distributed SQL with PostgreSQL compatibility

- **Amazon DocumentDB MCP Server**
  - Use `awslabs.documentdb-mcp-server` for MongoDB-compatible document database operations

- **Amazon Neptune MCP Server**
  - Use `awslabs.amazon-neptune-mcp-server` for graph database queries with openCypher and Gremlin

- **Amazon Keyspaces MCP Server**
  - Use `awslabs.amazon-keyspaces-mcp-server` for Apache Cassandra-compatible operations

- **Amazon Timestream for InfluxDB MCP Server**
  - Use `awslabs.timestream-for-influxdb-mcp-server` for InfluxDB-compatible operations

- **Amazon MSK MCP Server**
  - Use `awslabs.aws-msk-mcp-server` for managed Kafka cluster operations and monitoring

- **AWS S3 Tables MCP Server**
  - Use `awslabs.s3-tables-mcp-server` for managing AWS S3 Tables for table storage and operations

- **Amazon Redshift MCP Server**
  - Use `awslabs.redshift-mcp-server` for discovering, exploring, and querying Amazon Redshift

##### Search & Analytics

- **Amazon OpenSearch MCP Server**
  - Use `opensearch-project.opensearch-mcp-server-py` for OpenSearch powered search, Analytics, and Observability

- **Amazon Data Processing MCP Server**
  - Use `awslabs.aws-dataprocessing-mcp-server` for comprehensive data processing tools

##### Caching & Performance

- **Amazon ElastiCache MCP Server**
  - Use `awslabs.elasticache-mcp-server` for complete ElastiCache operations

- **Amazon ElastiCache / MemoryDB for Valkey MCP Server**
  - Use `awslabs.valkey-mcp-server` for advanced data structures and caching with Valkey

- **Amazon ElastiCache for Memcached MCP Server**
  - Use `awslabs.memcached-mcp-server` for high-speed caching operations

#### Developer Tools & Support

- **AWS IAM MCP Server**
  - Use `awslabs.iam-mcp-server` for comprehensive IAM user, role, group, and policy management

- **Git Repo Research MCP Server**
  - Use `awslabs.git-repo-research-mcp-server` for semantic code search and repository analysis

- **Code Documentation Generation MCP Server**
  - Use `awslabs.code-doc-gen-mcp-server` for automated documentation from code analysis

- **AWS Diagram MCP Server**
  - Use `awslabs.aws-diagram-mcp-server` for creating diagrams to support the solution:
    - generate_diagram: Generate a diagram from Python code using the diagrams package
    - get_diagram_examples: Get example code for different types of diagrams
    - list_icons: List available providers, services, and icons that can be used in diagrams

- **Frontend MCP Server**
  - Use `awslabs.frontend-mcp-server` for React and modern web development guidance

- **Synthetic Data MCP Server**
  - Use `awslabs.syntheticdata-mcp-server` for generating realistic test data

- **OpenAPI MCP Server**
  - Use `awslabs.openapi-mcp-server` for dynamic API integration through OpenAPI specifications

- **AWS Support MCP Server**
  - Use `awslabs.aws-support-mcp-server` for help with creating and managing AWS Support cases

#### Integration & Messaging

- **Amazon SNS / SQS MCP Server**
  - Use `awslabs.amazon-sns-sqs-mcp-server` for event-driven messaging and queue management

- **Amazon MQ MCP Server**
  - Use `awslabs.amazon-mq-mcp-server` for message broker management for RabbitMQ and ActiveMQ

- **AWS Step Functions Tool MCP Server**
  - Use `awslabs.stepfunctions-tool-mcp-server` for executing complex workflows and business processes

- **Amazon Location Service MCP Server**
  - Use `awslabs.aws-location-mcp-server` for place search, geocoding, and route optimization

#### Cost & Operations

- **AWS Pricing MCP Server**
  - Use `awslabs.aws-pricing-mcp-server` for analyzing AWS service costs:
    - analyze_cdk_project: Analyze a CDK project to identify AWS services used
    - get_pricing: Get pricing information from AWS Price List API
    - get_bedrock_patterns: Get architecture patterns for Amazon Bedrock applications
    - generate_cost_report: Generate a detailed cost analysis report based on pricing data

- **AWS Cost Explorer MCP Server**
  - Use `awslabs.cost-explorer-mcp-server` for detailed cost analysis and reporting

- **Amazon CloudWatch MCP Server**
  - Use `awslabs.cloudwatch-mcp-server` for metrics, alarms, and logs analysis

- **Amazon CloudWatch Logs MCP Server**
  - Use `awslabs.cloudwatch-logs-mcp-server` for log analysis and operational troubleshooting

- **Amazon CloudWatch Application Signals MCP Server**
  - Use `awslabs.cloudwatch-appsignals-mcp-server` for application monitoring and performance insights

- **AWS Managed Prometheus MCP Server**
  - Use `awslabs.prometheus-mcp-server` for Prometheus-compatible operations

#### Healthcare & Lifesciences

- **AWS HealthOmics MCP Server**
  - Use `awslabs.aws-healthomics-mcp-server` for generating, running, debugging and optimizing lifescience workflows

### 2.2 Modern AWS Service Categories and MCP Server Mapping

Map user requirements to these AWS categories and their corresponding MCP servers:

#### Compute
- AWS Lambda (serverless functions) → `awslabs.lambda-tool-mcp-server`
- ECS Fargate (containerized applications) → `awslabs.ecs-mcp-server`
- EC2 (virtual machines) → `awslabs.aws-api-mcp-server`
- App Runner (containerized web apps) → `awslabs.aws-serverless-mcp-server`
- Batch (batch processing) → `awslabs.aws-api-mcp-server`
- Lightsail (simplified virtual servers) → `awslabs.aws-api-mcp-server`
- Elastic Beanstalk (PaaS) → `awslabs.aws-api-mcp-server`
- EKS (Kubernetes) → `awslabs.eks-mcp-server`

#### Storage
- DynamoDB (NoSQL data) → `awslabs.dynamodb-mcp-server`
- Aurora Serverless v2 (relational data) → `awslabs.postgres-mcp-server`, `awslabs.mysql-mcp-server`, `awslabs.aurora-dsql-mcp-server`
- S3 (object storage) → `awslabs.aws-api-mcp-server`, `awslabs.s3-tables-mcp-server`
- OpenSearch Serverless (search and analytics) → `opensearch-project.opensearch-mcp-server-py`
- RDS (relational databases) → `awslabs.postgres-mcp-server`, `awslabs.mysql-mcp-server`
- DocumentDB → `awslabs.documentdb-mcp-server`
- ElastiCache (in-memory caching) → `awslabs.elasticache-mcp-server`, `awslabs.valkey-mcp-server`, `awslabs.memcached-mcp-server`
- FSx (file systems) → `awslabs.aws-api-mcp-server`
- EFS (elastic file system) → `awslabs.aws-api-mcp-server`
- S3 Glacier (long-term archival) → `awslabs.aws-api-mcp-server`
- Neptune (graph database) → `awslabs.amazon-neptune-mcp-server`
- Keyspaces (Cassandra-compatible) → `awslabs.amazon-keyspaces-mcp-server`
- Timestream for InfluxDB → `awslabs.timestream-for-influxdb-mcp-server`
- Redshift (data warehousing) → `awslabs.redshift-mcp-server`

#### AI/ML
- Bedrock (foundation models) → `awslabs.aws-api-mcp-server`
- Bedrock Knowledge Base (knowledge base) → `awslabs.bedrock-kb-retrieval-mcp-server`
- SageMaker (custom ML models) → `awslabs.aws-api-mcp-server`
- Bedrock Data Automation (IDP) → `awslabs.aws-bedrock-data-automation-mcp-server`
- Rekognition (image and video analysis) → `awslabs.amazon-rekognition-mcp-server`
- Comprehend (natural language processing) → `awslabs.aws-api-mcp-server`
- Transcribe (speech-to-text) → `awslabs.aws-api-mcp-server`
- Polly (text-to-speech) → `awslabs.aws-api-mcp-server`
- Kendra (intelligent search) → `awslabs.amazon-kendra-index-mcp-server`
- Personalize (personalization and recommendations) → `awslabs.aws-api-mcp-server`
- Forecast (time-series forecasting) → `awslabs.aws-api-mcp-server`
- Amazon Q Business → `awslabs.amazon-qbusiness-anonymous-mcp-server`, `awslabs.amazon-qindex-mcp-server`
- Nova Canvas (image generation) → `awslabs.nova-canvas-mcp-server`

#### Data & Analytics
- Redshift (data warehousing) → `awslabs.redshift-mcp-server`
- Athena (serverless SQL queries) → `awslabs.aws-api-mcp-server`
- Glue (ETL service) → `awslabs.aws-dataprocessing-mcp-server`
- EMR (big data processing) → `awslabs.aws-dataprocessing-mcp-server`
- Kinesis (real-time data streaming) → `awslabs.aws-api-mcp-server`
- QuickSight (business intelligence) → `awslabs.aws-api-mcp-server`
- Lake Formation (data lake) → `awslabs.aws-api-mcp-server`
- DataZone (data management) → `awslabs.aws-api-mcp-server`
- MSK (managed Kafka) → `awslabs.aws-msk-mcp-server`

#### Frontend
- Amplify Gen2 (full-stack applications) → `awslabs.frontend-mcp-server`
- CloudFront (content delivery) → `awslabs.aws-api-mcp-server`
- AppSync (GraphQL APIs) → `awslabs.aws-api-mcp-server`
- API Gateway (REST APIs) → `awslabs.aws-api-mcp-server`, `awslabs.openapi-mcp-server`
- S3 (static assets) → `awslabs.aws-api-mcp-server`
- Location Service (maps and location) → `awslabs.aws-location-mcp-server`
- Pinpoint (customer engagement) → `awslabs.aws-api-mcp-server`

#### Security
- Cognito (authentication) → `awslabs.aws-api-mcp-server`
- IAM (access control) → `awslabs.iam-mcp-server`
- KMS (encryption) → `awslabs.aws-api-mcp-server`
- WAF (web security) → `awslabs.aws-api-mcp-server`
- Shield (DDoS protection) → `awslabs.aws-api-mcp-server`
- GuardDuty (threat detection) → `awslabs.aws-api-mcp-server`
- Security Hub (security posture) → `awslabs.aws-api-mcp-server`
- Macie (data security) → `awslabs.aws-api-mcp-server`
- Inspector (vulnerability management) → `awslabs.aws-api-mcp-server`
- Verified Permissions (fine-grained permissions) → `awslabs.aws-api-mcp-server`
- Certificate Manager (SSL/TLS certificates) → `awslabs.aws-api-mcp-server`

#### Networking
- VPC (virtual private cloud) → `awslabs.aws-api-mcp-server`
- Route 53 (DNS service) → `awslabs.aws-api-mcp-server`
- CloudFront (CDN) → `awslabs.aws-api-mcp-server`
- Global Accelerator (network performance) → `awslabs.aws-api-mcp-server`
- Transit Gateway (network transit hub) → `awslabs.aws-api-mcp-server`
- Direct Connect (dedicated network connection) → `awslabs.aws-api-mcp-server`
- VPN (secure connection) → `awslabs.aws-api-mcp-server`
- App Mesh (service mesh) → `awslabs.aws-api-mcp-server`

#### DevOps
- CodePipeline (CI/CD pipeline) → `awslabs.aws-api-mcp-server`
- CodeBuild (build service) → `awslabs.aws-api-mcp-server`
- CodeDeploy (deployment service) → `awslabs.aws-api-mcp-server`
- CodeCommit (git repository) → `awslabs.aws-api-mcp-server`, `awslabs.git-repo-research-mcp-server`
- CodeArtifact (artifact repository) → `awslabs.aws-api-mcp-server`
- CloudFormation (infrastructure as code) → `awslabs.cfn-mcp-server`
- CDK (infrastructure as code) → `awslabs.cdk-mcp-server`
- CloudWatch (monitoring) → `awslabs.cloudwatch-mcp-server`, `awslabs.cloudwatch-logs-mcp-server`, `awslabs.cloudwatch-appsignals-mcp-server`
- X-Ray (distributed tracing) → `awslabs.aws-api-mcp-server`
- Terraform → `awslabs.terraform-mcp-server`

#### Healthcare & Lifesciences
- HealthOmics → `awslabs.aws-healthomics-mcp-server`

#### Cost Management
- Cost Explorer → `awslabs.cost-explorer-mcp-server`
- Pricing Calculator → `awslabs.aws-pricing-mcp-server`

## 3. Example Translation

### Example 1: Radio Log Database with Natural Language Chat

User Query:
"How do I make an application with a radio log database that I can chat with using natural language?"

Analysis:

1. Components:
- Web application interface
- Database for radio logs
- Natural language chat interface
- Data retrieval system

2. AWS Solution Mapping:
- Frontend: Vite, React, Mantine v7, TanStack Query, TanStack Router, TypeScript, Amplify libraries for authentication, authorization, and storage
- Database: DynamoDB for radio logs
- API: AppSync for GraphQL data access
- Chat: Amplify Gen2 AI Conversation data model
- Authentication: Cognito user pools

3. Implementation Approach:
- Use CDK for infrastructure setup
- Set up Amplify Gen2 AI Conversation data model for chat capabilities

## 4. Best Practices

1. Always consider:
- Serverless-first architecture
- Pay-per-use pricing models
- Managed services over self-hosted
- Built-in security features
- Scalability requirements

2. Documentation:
- Reference AWS well-architected framework
- Include cost optimization strategies
- Note security best practices
- Document compliance considerations

## 5. Tool Usage Strategy

1. Initial Analysis:
```md
# Understanding the user's requirements
<use_mcp_tool>
<server_name>awslabs.core-mcp-server</server_name>
<tool_name>prompt_understanding</tool_name>
<arguments>
{}
</arguments>
</use_mcp_tool>
```

2. Domain Research:
```md
# Getting domain guidance
<use_mcp_tool>
<server_name>awslabs.bedrock-kb-retrieval-mcp-server</server_name>
<tool_name>QueryKnowledgeBases</tool_name>
<arguments>
{
  "query": "what services are allowed internally on aws",
  "knowledge_base_id": "KBID",
  "number_of_results": 10
}
</arguments>
</use_mcp_tool>
```

3. Architecture Planning:
```md
# Getting CDK infrastructure guidance
<use_mcp_tool>
<server_name>awslabs.cdk-mcp-server</server_name>
<tool_name>CDKGeneralGuidance</tool_name>
<arguments>
{}
</arguments>
</use_mcp_tool>
```

## 6. Additional MCP Server Tools Examples

### 6.1 Nova Canvas MCP Server

Generate images for UI or solution architecture diagrams:

```md
# Generating architecture visualization
<use_mcp_tool>
<server_name>awslabs.nova-canvas-mcp-server</server_name>
<tool_name>generate_image</tool_name>
<arguments>
{
  "prompt": "3D isometric view of AWS cloud architecture with Lambda functions, API Gateway, and DynamoDB tables, professional technical diagram style",
  "negative_prompt": "text labels, blurry, distorted",
  "width": 1024,
  "height": 1024,
  "quality": "premium",
  "workspace_dir": "/path/to/workspace"
}
</arguments>
</use_mcp_tool>
```

### 6.2 AWS Pricing MCP Server

Get pricing information for AWS services:

```md
# Getting pricing information
<use_mcp_tool>
<server_name>awslabs.aws-pricing-mcp-server</server_name>
<tool_name>get_pricing</tool_name>
<arguments>
{
  "service_code": "AWSLambda"
}
</arguments>
</use_mcp_tool>
```

### 6.3 AWS Documentation MCP Server

Search for AWS documentation:

```md
# Searching AWS documentation
<use_mcp_tool>
<server_name>awslabs.aws-documentation-mcp-server</server_name>
<tool_name>search_documentation</tool_name>
<arguments>
{
  "search_phrase": "Lambda function URLs",
  "limit": 5
}
</arguments>
</use_mcp_tool>
```

### 6.4 Terraform MCP Server

Execute Terraform commands and search for infrastructure documentation:

```md
# Execute Terraform commands
<use_mcp_tool>
<server_name>awslabs.terraform-mcp-server</server_name>
<tool_name>ExecuteTerraformCommand</tool_name>
<arguments>
{
  "command": "plan",
  "working_directory": "/path/to/terraform/project",
  "variables": {
    "environment": "dev",
    "region": "us-west-2"
  }
}
</arguments>
</use_mcp_tool>
```

```md
# Search AWSCC provider documentation
<use_mcp_tool>
<server_name>awslabs.terraform-mcp-server</server_name>
<tool_name>SearchAwsccProviderDocs</tool_name>
<arguments>
{
  "asset_name": "awscc_lambda_function",
  "asset_type": "resource"
}
</arguments>
</use_mcp_tool>
```

```md
# Search for user-provided Terraform modules
<use_mcp_tool>
<server_name>awslabs.terraform-mcp-server</server_name>
<tool_name>SearchUserProvidedModule</tool_name>
<arguments>
{
  "module_url": "terraform-aws-modules/vpc/aws",
  "version": "5.0.0"
}
</arguments>
</use_mcp_tool>
```

Example Workflow:
1. Research industry basics using AWS documentation search
2. Identify common patterns and requirements
3. Search AWS docs for specific solutions
4. Use read_documentation to deep dive into relevant documentation
5. Map findings to AWS services and patterns

Key Research Areas:
- Industry-specific compliance requirements
- Common technical challenges
- Established solution patterns
- Performance requirements
- Security considerations
- Cost sensitivity
- Integration requirements

Remember: The goal is to translate general application requirements into specific, modern AWS services and patterns while considering scalability, security, and cost-effectiveness. if any MCP server referenced here is not avalaible, ask the user if they would like to install it

### 6.5 AWS API MCP Server

Find all running EC2 servers in us-west-2 in the user's AWS account using AWS CLI commands.

```md
# Search for relevant AWS commands
<use_mcp_tool>
<server_name>awslabs.aws-api-mcp-server</server_name>
<tool_name>suggest_aws_commands</tool_name>
<arguments>
{
  "query": "Show me all running EC2 instances in us-west-2",
}
</arguments>
</use_mcp_tool>
```

```md
# Execute an AWS CLI command
<use_mcp_tool>
<server_name>awslabs.aws-api-mcp-server</server_name>
<tool_name>call_aws</tool_name>
<arguments>
{
  "cli_command": "aws ec2 describe-instances --filters "Name=instance-state-name,Values=running" --region us-west-2",
}
</arguments>
</use_mcp_tool>
```
