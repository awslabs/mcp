# AWS CDK General Guidance

This guide provides essential guidance for AWS CDK development, focusing on when to use specific constructs and tools.

## Getting Started with CDK

Always initialize CDK projects properly using the CDK CLI:

```bash
# For TypeScript projects
cdk init app --language typescript

# For Python projects
cdk init app --language python
```

Proper initialization ensures:

- Consistent project structure
- Correct dependency setup
- Appropriate tsconfig/package.json configuration
- Necessary boilerplate files

This foundation helps avoid common issues and ensures compatibility with the AWS CDK ecosystem.

## Development Workflow

When developing CDK applications, use these commands for an efficient workflow:

```bash
# Synthesize CloudFormation templates (recommended for validation)
cdk synth

# Deploy your CDK application
cdk deploy

# Compare deployed stack with current state
cdk diff
```

**Important**: Prefer `cdk synth` over `npm run build` or `tsc` for TypeScript projects. The `cdk synth` command:

- Automatically compiles TypeScript code when needed
- Validates CDK constructs and catches potential deployment issues
- Generates CloudFormation templates for inspection
- Provides more informative error messages for debugging

## CDK Implementation Approach and Workflow

# Compare deployed stack with current state

### Common Architecture Patterns

**For standard application architectures:**

- Use the `GetAwsSolutionsConstructPattern` tool to find pre-built patterns
- AWS Solutions Constructs implement AWS best practices by default
- Ideal for REST APIs, serverless backends, data processing pipelines, etc.
- Example: `GetAwsSolutionsConstructPattern(services=["lambda", "dynamodb"])`
- For complete documentation: `aws-solutions-constructs://{pattern_name}`

**Key benefits:**
- Accelerated development with vetted patterns
- Built-in security and best practices
- Reduced complexity for multi-service architectures

### GenAI/AI/ML Implementations

**For AI/ML and generative AI workloads:**

- Use the `SearchGenAICDKConstructs` tool for specialized AI/ML constructs
- These simplify implementation of Bedrock, SageMaker, and other AI services
- Perfect for agents, knowledge bases, vector stores, and other GenAI components

**Installation:**

```typescript
// TypeScript
npm install @cdklabs/generative-ai-cdk-constructs
import * as genai from '@cdklabs/generative-ai-cdk-constructs';
```

```python
# Python
pip install cdklabs.generative-ai-cdk-constructs
import cdklabs.generative_ai_cdk_constructs
```

**Regional considerations for Bedrock:**
- Many foundation models require inference profiles in specific regions
- Use `CrossRegionInferenceProfile` class for proper configuration
- For details: `genai-cdk-constructs://bedrock/profiles`

### Combined Implementation Patterns

**Important:** AWS Solutions Constructs and GenAI CDK Constructs can be used together in the same project:

- Use GenAI CDK Constructs for Bedrock components (agents, knowledge bases)
- Use AWS Solutions Constructs for REST APIs, databases, and other infrastructure
- Apply CDK Nag across all components for security validation

**Example combined architecture:**
- REST API backend using aws-apigateway-lambda-dynamodb construct
- Bedrock Agent using GenAI CDK constructs for natural language processing
- Shared data layer between traditional and AI components

### Implementation Workflow

Follow this step-by-step workflow for developing AWS CDK applications:

1. **Get CDK Guidance**: Start with the **CDKGeneralGuidance** tool to understand best practices.

2. **Initialize CDK Project**: Use `cdk init app` to create your project with proper structure.

3. **Choose Implementation Approach**:
   - For common patterns: Use **GetAwsSolutionsConstructPattern** tool
   - For GenAI applications: Use **SearchGenAICDKConstructs** tool
   - For custom requirements: Develop custom CDK code following best practices

4. **For Lambda Functions**:
   - For observability: Implement Lambda Powertools (see `lambda-powertools://cdk` for details)
   - For Lambda layers: Use **LambdaLayerDocumentationProvider** tool

5. **For Bedrock Agents with Action Groups**:
   - Create Lambda function with BedrockAgentResolver from Lambda Powertools
   - Use **GenerateBedrockAgentSchema** tool to generate OpenAPI schema
   - Integrate schema into Agent CDK code

6. **Apply Security Best Practices**:
   - Always apply CDK Nag to ensure security best practices
   - Use **ExplainCDKNagRule** tool to understand specific rules
   - Validate suppressions with **CheckCDKNagSuppressions** tool

7. **Validate and Deploy**:
   - Run `cdk synth` to check for errors and generate CloudFormation
   - Ensure all CDK Nag warnings are resolved or properly justified
   - Deploy using `cdk deploy`

## Key Principles

- **Security First**: Always implement security best practices by default
- **Cost Optimization**: Design resources to minimize costs while meeting requirements
- **Operational Excellence**: Implement proper monitoring, logging, and observability
- **Serverless-First**: Prefer serverless services when possible
- **Infrastructure as Code**: Use CDK to define all infrastructure
- **Use Vetted Patterns**: Prefer AWS Solutions Constructs over custom implementations
- **Regional Awareness**: Consider regional availability and constraints for services

## AWS Solutions Constructs

AWS Solutions Constructs are vetted architecture patterns that combine multiple AWS services to solve common use cases following AWS Well-Architected best practices.

**Key benefits:**

- Accelerated Development: Implement common patterns without boilerplate code
- Best Practices Built-in: Security, reliability, and performance best practices
- Reduced Complexity: Simplified interfaces for multi-service architectures
- Well-Architected: Patterns follow AWS Well-Architected Framework principles

**When to use Solutions Constructs:**

- Implementing common architecture patterns (e.g., API + Lambda + DynamoDB)
- You want secure defaults and best practices applied automatically
- You need to quickly prototype or build production-ready infrastructure

To discover available patterns, use the `GetAwsSolutionsConstructPattern` tool.

## Security with CDK Nag

CDK Nag ensures your CDK applications follow AWS security best practices. **Always apply CDK Nag to all stacks.**

**When to use CDK Nag tools:**

- **ExplainCDKNagRule**: When encountering warnings that need remediation
- **CheckCDKNagSuppressions**: During code reviews to verify suppression justifications

Key security practices:

- Follow least privilege for IAM
- Secure S3 buckets with encryption and access controls
- Implement secure authentication with Cognito
- Secure API Gateway endpoints with proper authorization

## Operational Excellence with Lambda Powertools

**Always implement Lambda Powertools** for structured logging, tracing, and metrics. For detailed guidance, use the `lambda-powertools://cdk` resource.

**Critical for Bedrock Agents**: When creating Bedrock Agents with Action Groups, use BedrockAgentResolver from Lambda Powertools with the **GenerateBedrockAgentSchema** tool to generate the required OpenAPI schema.

## Tool Selection Guide

Match CDK tasks to appropriate tools:

| Task | Tool | Common Mistakes |
|------|------|-----------------|
| Generate Bedrock Agent schema | GenerateBedrockAgentSchema | ❌ Missing schema generation or not running script to create openapi.json |
| Understand CDK Nag rules | ExplainCDKNagRule | ❌ Ignoring security warnings without understanding remediation steps |
| Find architecture patterns | GetAwsSolutionsConstructPattern | ❌ Building common patterns from scratch instead of using vetted constructs |
| Implement GenAI features | SearchGenAICDKConstructs | ❌ Building GenAI components without specialized constructs |
| Access Lambda layer docs | LambdaLayerDocumentationProvider | ❌ Missing proper Lambda layer structure or configuration |
| Add Lambda observability | lambda-powertools://cdk | ❌ Missing structured logging and monitoring |
| Audit CDK Nag suppressions | CheckCDKNagSuppressions | ❌ Insufficient documentation for security suppressions |
