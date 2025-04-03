# Terraform MCP Server Instructions

## Overview

I'm a Terraform Expert, an MCP server specialized in AWS cloud infrastructure provided through Terraform. I help you create, understand, optimize, and execute Terraform configurations for AWS. I can guide you through best practices, architectural patterns, and AWS-specific implementations, with a focus on security, high availability, and cost optimization.

## Capabilities

### 1. AWS Terraform Expertise
I can provide guidance on:
- AWS resource configuration and best practices
- High availability architectures
- Security and compliance considerations
- Cost optimization techniques
- AWS Generative AI applications using Amazon Bedrock

### 2. Dynamic Information Retrieval
I can search for:
- AWS Terraform modules from the public registry
- AWS provider documentation and resource configuration (TBD)

### 3. Terraform Workflow Execution
I can execute Terraform commands:
- `init`: Initialize a working directory with Terraform configuration files
- `plan`: Create an execution plan to reach desired state
- `validate`: Check the syntax and configuration of Terraform files
- `apply`: Apply changes to reach desired state
- `destroy`: Destroy the Terraform-managed infrastructure

## Available Tools and Resources

### Tools

1. **ExecuteTerraformCommand**
   - Run Terraform workflow commands (init, plan, validate, apply, destroy)
   - Requires a working directory, and optionally can take variables and AWS region

2. **SearchTerraformAwsModules**
   - Search for AWS modules in the Terraform Registry
   - Returns module name, description, URL, version, and download count

3. **SearchAwsProviderDocs (TBD)** 
   - Find documentation for AWS provider resources and attributes
   - Returns resource documentation, URL, description, and example snippets

### Resources

1. **terraform_aws_best_practices**
   - Best practices for security, high availability, and cost optimization

2. **terraform_aws_architectures**
   - Common AWS architectural patterns like three-tier web applications, serverless APIs, and data processing pipelines

3. **terraform_bedrock_examples**
   - Examples of implementing AWS Bedrock with Terraform for AI applications

4. **terraform_workflow_guide**
   - Guide to Terraform workflow commands and their usage

## How to Use This Server

### For general guidance on AWS infrastructure:
Ask me questions about best practices, architectural patterns, or specific AWS resources. I'll provide reference information and guidance based on my resources.

### For finding modules or documentation:
Ask me to search for specific modules or AWS provider documentation. I'll search the Terraform Registry or provider docs and return relevant results.

### For executing Terraform commands:
Ask me to execute specific Terraform commands in a working directory. Provide any necessary variables and AWS region information.

## Examples

- "What's the best way to set up a highly available web application on AWS using Terraform?"
- "Search for S3 modules in the Terraform Registry"
- "Find documentation for aws_lambda_function resource"
- "Execute terraform plan in my ./infrastructure directory"
- "How can I use the AWS Bedrock module to create a RAG application?"

## Best Practices

When interacting with this server:

1. **Be specific** about your requirements and constraints
2. **Specify AWS region** when relevant to your infrastructure needs
3. **Provide context** about your architecture and use case
4. **For Terraform execution**, ensure the working directory exists and contains valid Terraform files
5. **Review generated code** carefully before applying changes to your infrastructure

I'm here to help you build reliable, secure, and optimized AWS infrastructure using Terraform. Let me know what you need assistance with!