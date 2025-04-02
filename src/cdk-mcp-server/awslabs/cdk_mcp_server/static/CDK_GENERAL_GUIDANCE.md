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

## Decision Flow for CDK Implementation

When implementing AWS infrastructure with CDK, consider these complementary approaches:

1. **For Common Architecture Patterns: AWS Solutions Constructs**
   - Use the `GetAwsSolutionsConstructPattern` tool to search for patterns that match your use case
   - Example: `GetAwsSolutionsConstructPattern(services=["lambda", "dynamodb"])`
   - AWS Solutions Constructs implement AWS best practices by default
   - For complete documentation: `aws-solutions-constructs://{pattern_name}`
   - Ideal for REST APIs, serverless backends, data processing pipelines, etc.

2. **For GenAI/AI/ML Use Cases: GenAI CDK Constructs**
   - Use the `SearchGenAICDKConstructs` tool for specialized AI/ML constructs
   - These simplify implementation of Bedrock, SageMaker, and other AI services
   - Perfect for agents, knowledge bases, vector stores, and other GenAI components

   **Installation:**
   ```typescript
   // TypeScript
   // Create or use an existing CDK application
   cdk init app --language typescript
   // Install the package
   npm install @cdklabs/generative-ai-cdk-constructs
   // Import the library
   import * as genai from '@cdklabs/generative-ai-cdk-constructs';
   ```

   ```python
   # Python
   # Create or use an existing CDK application
   cdk init app --language python
   # Install the package
   pip install cdklabs.generative-ai-cdk-constructs
   # Import the library
   import cdklabs.generative_ai_cdk_constructs
   ```

3. **For All Projects: Apply CDK Nag**
   - Always apply CDK Nag to ensure security best practices
   - Use the `ExplainCDKNagRule` tool to understand specific rules

4. **For Custom Requirements: Custom Implementation**
   - Create custom CDK code when no suitable constructs exist
   - Follow AWS Well-Architected best practices

> **IMPORTANT**: AWS Solutions Constructs and GenAI CDK Constructs are complementary and can be used together in the same project. For example, you might use GenAI CDK Constructs for Bedrock components and AWS Solutions Constructs for the REST API and database layers of your application.

## Key Principles

- **Security First**: Always implement security best practices by default
- **Cost Optimization**: Design resources to minimize costs while meeting requirements
- **Operational Excellence**: Implement proper monitoring, logging, and observability
- **Serverless-First**: Prefer serverless services when possible
- **Infrastructure as Code**: Use CDK to define all infrastructure
- **Use Vetted Patterns**: Prefer AWS Solutions Constructs over custom implementations
- **Regional Awareness**: Consider regional availability and constraints for services

## Amazon Bedrock Cross-Region Inference Profiles

When working with Amazon Bedrock foundation models, many models (including Claude models, Meta Llama models, and Amazon's own Nova models) require the use of inference profiles rather than direct on-demand usage in specific regions. Failing to use inference profiles can result in errors like:

```
Invocation of model ID anthropic.claude-3-7-sonnet-20250219-v1:0 with on-demand throughput isn't supported.
Retry your request with the ID or ARN of an inference profile that contains this model.
```

### Using Cross-Region Inference Profiles

To properly configure Bedrock models with cross-region inference profiles:

#### TypeScript

```typescript
import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';

// Create a cross-region inference profile for Claude
const claudeInferenceProfile = bedrock.CrossRegionInferenceProfile.fromConfig({
  // Choose the appropriate region:
  // US (default) - bedrock.CrossRegionInferenceProfileRegion.US
  // EU - bedrock.CrossRegionInferenceProfileRegion.EU
  // APAC - bedrock.CrossRegionInferenceProfileRegion.APAC
  geoRegion: bedrock.CrossRegionInferenceProfileRegion.US,
  model: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_7_SONNET_V1_0
});

// Use the inference profile with your agent or other Bedrock resources
const agent = new bedrock.Agent(this, 'MyAgent', {
  // Use the inference profile instead of directly using the foundation model
  foundationModel: claudeInferenceProfile,
  // Other agent configuration...
});
```

#### Python

```python
from cdklabs.generative_ai_cdk_constructs import bedrock

# Create a cross-region inference profile for Claude
claude_inference_profile = bedrock.CrossRegionInferenceProfile.from_config(
    # Choose the appropriate region:
    # US (default) - bedrock.CrossRegionInferenceProfileRegion.US
    # EU - bedrock.CrossRegionInferenceProfileRegion.EU
    # APAC - bedrock.CrossRegionInferenceProfileRegion.APAC
    geo_region=bedrock.CrossRegionInferenceProfileRegion.US,
    model=bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_7_SONNET_V1_0
)

# Use the inference profile with your agent or other Bedrock resources
agent = bedrock.Agent(self, "MyAgent",
    # Use the inference profile instead of directly using the foundation model
    foundation_model=claude_inference_profile,
    # Other agent configuration...
)
```

### Regional Considerations

- **Model Availability**: Not all foundation models are available in all regions
- **Inference Profile Requirements**: Some models require inference profiles in specific regions
- **Performance**: Choose the region closest to your users for optimal latency
- **Compliance**: Consider data residency requirements when selecting regions

Always check the [Amazon Bedrock documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html) for the latest information on model availability and regional constraints.

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

CDK Nag is a crucial tool for ensuring your CDK applications follow AWS security best practices. **Always apply CDK Nag to all your stacks by default.**

Key security practices to remember:
- Follow the principle of least privilege for IAM
- Secure S3 buckets with encryption, access controls, and policies
- Implement secure authentication with Cognito
- Secure API Gateway endpoints with proper authorization

For detailed guidance, use the `CDKNagGuidance` tool.

## Operational Excellence with Lambda Powertools

Always implement Lambda Powertools for:
- Structured Logging
- Tracing
- Metrics

For detailed guidance, use the `LambdaPowertoolsGuidance` tool.

## Available MCP Tools

This MCP server provides several tools to help you implement AWS CDK best practices:

1. **CDKGeneralGuidance**: This document - general CDK best practices
2. **ExplainCDKNagRule**: Explain a specific CDK Nag rule with AWS Well-Architected guidance
3. **CheckCDKNagSuppressions**: Check if CDK code contains Nag suppressions that require human review
4. **GenerateBedrockAgentSchemaFromFile**: Generate OpenAPI schema for Bedrock Agent Action Groups from Lambda functions
5. **GetAwsSolutionsConstructPattern**: Search and discover AWS Solutions Constructs patterns
6. **SearchGenAICDKConstructs**: Search for GenAI CDK constructs by name or type

## Available MCP Resources

This MCP server also provides several resources for accessing documentation:

1. **cdk-nag://rules/{rule_pack}**: Get all rules for a specific CDK Nag rule pack
2. **cdk-nag://warnings/{rule_pack}**: Get warnings for a specific CDK Nag rule pack
3. **cdk-nag://errors/{rule_pack}**: Get errors for a specific CDK Nag rule pack
4. **lambda-powertools://{topic}**: Get Lambda Powertools guidance on a specific topic
5. **aws-solutions-constructs://{pattern_name}**: Get complete documentation for an AWS Solutions Constructs pattern
6. **genai-cdk-constructs://{construct_type}/{construct_name}**: Get documentation for a GenAI CDK construct

Always check for these tools and resources when implementing CDK infrastructure to ensure you're following AWS best practices.
