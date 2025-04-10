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
- Use `awslabs.cdk-mcp-server` for infrastructure patterns
  - AmazonWebServicesCDKGuidance: tool for retrieving prescriptive guidance for buidling AWS resources using CDK
- Use `awslabs.core-mcp-server` tools for:
  - get_prompt_understanding: Initial query analysis
  - get_plan: Generate implementation strategy
- Use `aswlabs.bedrock-kb-retrieval-mcp-server` to query user defined KB
- Use `awslabs.nova-canvas-expert-mcp-server` to help create images
  - get_imagegenerate_image: Generate an image for the UI
  - generate_image_with_colors: Generate images using color pallet

-Use `awslabs.cost-analasys-mcp-server`  for analyzing AWS service costs
  - get_pricing_from_web: Get pricing information from AWS pricing webpage
  - get_pricing_from_api: Get pricing information from AWS Price List API
  - generate_cost_analysis_report: Generate a detailed cost analysis report based on pricing data

-Use `awslabs.aws-documentation-mcp-server` for requesting specific AWS documentation
    - Use `search_documentation` when: You need to find documentation about a specific AWS service or feature
    - Use `read_documentation` when: You have a specific documentation URL and need its content
    - Use `recommend` when: You want to find related content to a documentation page you're already viewing or need to find newly released information
    - Use `recommend` as a fallback when: Multiple searches have not yielded the specific information needed

### 2.2 Modern AWS Service Categories

Map user requirements to these AWS categories:

#### Compute
- AWS Lambda (serverless functions)
- ECS Fargate (containerized applications)
- EC2 (virtual machines)
- App Runner (containerized web apps)
- Batch (batch processing)
- Lightsail (simplified virtual servers)
- Elastic Beanstalk (PaaS)

#### Storage
- DynamoDB (NoSQL data)
- Aurora Serverless v2 (relational data)
- S3 (object storage)
- OpenSearch Serverless (search and analytics)
- RDS (relational databases)
- DocumentDB
- ElastiCache (in-memory caching)
- FSx (file systems)
- EFS (elastic file system)
- S3 Glacier (long-term archival)

#### AI/ML
- Bedrock (foundation models)
- Bedrock Knowledge Base (knowledge base)
- SageMaker (custom ML models)
- Bedrock Data Automation (IDP)
- Rekognition (image and video analysis)
- Comprehend (natural language processing)
- Transcribe (speech-to-text)
- Polly (text-to-speech)
- Kendra (intelligent search)
- Personalize (personalization and recommendations)
- Forecast (time-series forecasting)

#### Data & Analytics
- Redshift (data warehousing)
- Athena (serverless SQL queries)
- Glue (ETL service)
- EMR (big data processing)
- Kinesis (real-time data streaming)
- QuickSight (business intelligence)
- Lake Formation (data lake)
- DataZone (data management)
- MSK (managed Kafka)

#### Frontend
- Amplify Gen2 (full-stack applications)
- CloudFront (content delivery)
- AppSync (GraphQL APIs)
- API Gateway (REST APIs)
- S3 (static assets)
- Location Service (maps and location)
- Pinpoint (customer engagement)

#### Security
- Cognito (authentication)
- IAM (access control)
- KMS (encryption)
- WAF (web security)
- Shield (DDoS protection)
- GuardDuty (threat detection)
- Security Hub (security posture)
- Macie (data security)
- Inspector (vulnerability management)
- Verified Permissions (fine-grained permissions)
- Certificate Manager (SSL/TLS certificates)

#### Networking
- VPC (virtual private cloud)
- Route 53 (DNS service)
- CloudFront (CDN)
- Global Accelerator (network performance)
- Transit Gateway (network transit hub)
- Direct Connect (dedicated network connection)
- VPN (secure connection)
- App Mesh (service mesh)

#### DevOps
- CodePipeline (CI/CD pipeline)
- CodeBuild (build service)
- CodeDeploy (deployment service)
- CodeCommit (git repository)
- CodeArtifact (artifact repository)
- CloudFormation (infrastructure as code)
- CDK (infrastructure as code)
- CloudWatch (monitoring)
- X-Ray (distributed tracing)

## 3. Example Translation

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

1. Implementation Approach:
- Use ui-expert.BaseUserInterfaceWebApp for frontend structure
- Use cdk-expert for infrastructure setup
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
<tool_name>get_prompt_understanding</tool_name>
</use_mcp_tool>
```

2. Domain Research:
```md
# Getting  Domain guidance
<use_mcp_tool>
<server_name>awslabs.bedrock-kb-retrieval-mcp-server</server_name>
<tool_name>QueryKnowledgeBases</tool_name>
<arguments>
{
  "query": "what services are allowed internally on aws",
  "knowledge_base_id": "KBID",
  "number_of_results": "10",


}
</arguments>
</use_mcp_tool>
```

3. Architecture Planning:
```md
# Getting CDK infrastructure guidance
<use_mcp_tool>
<server_name>awslabs.cdk-mcp-server</server_name>
<tool_name>AmazonWebServicesCDKGuidance</tool_name>
<arguments>
{
  "query": "infrastructure patterns for specific requirements"
}
</arguments>
</use_mcp_tool>
```

## 5. Additional MCP Server Tools

### 5.1 NovaCanvas Expert

Generate images for for use in UI or solution architecture diagrams:

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
  "quality": "premium"
}
</arguments>
</use_mcp_tool>
```

### 5.2 AWS Cost Analysis Expert

Generate images for for use in UI or solution architecture diagrams:

```md
# Generating architecture visualization
<use_mcp_tool>
<server_name>awslabs.cost-analysis-mcp-server</server_name>
<tool_name>get_pricing_from_web</tool_name>
<arguments>
{
  "service_code": "3D isometric view of AWS cloud architecture with Lambda functions, API Gateway, and DynamoDB tables, professional technical
}
</arguments>
</use_mcp_tool>
```



Example Workflow:
1. Research industry basics using brave search
2. Identify common patterns and requirements
3. Search AWS docs for specific solutions
4. Use get_pages to deep dive into relevant documentation
5. Map findings to AWS services and patterns

Key Research Areas:
- Industry-specific compliance requirements
- Common technical challenges
- Established solution patterns
- Performance requirements
- Security considerations
- Cost sensitivity
- Integration requirements

Remember: The goal is to translate general application requirements into specific, modern AWS services and patterns while considering scalability, security, and cost-effectiveness.
