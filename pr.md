# AWS Cloud Control API MCP Server

## Summary
This PR introduces the **AWS Cloud Control API MCP Server** (`ccapi-mcp-server`), a comprehensive Model Context Protocol server that enables AI assistants to manage AWS resources through the AWS Cloud Control API with integrated security scanning via Checkov and enforced token-based workflows for transparency and security.

## Changes

### New MCP Server with 12 Core Tools

1. **`check_environment_variables()`** - Validates AWS credential configuration
2. **`get_aws_session_info()`** - Retrieves current AWS session details with credential masking
3. **`get_aws_account_info()`** - Quick AWS account information lookup
4. **`get_resource_schema_information()`** - Fetches AWS resource type schemas
5. **`list_resources()`** - Lists existing AWS resources by type
6. **`get_resource()`** - Retrieves detailed information about specific resources
7. **`generate_infrastructure_code()`** - Creates secure resource definitions with default tags
8. **`explain()`** - **MANDATORY** transparency tool that shows users exactly what will be created/modified
9. **`run_checkov()`** - Security scanning with Checkov (configurable: enabled/disabled)
10. **`create_resource()`** - Creates AWS resources with security validation
11. **`update_resource()`** - Updates existing resources with patch operations
12. **`delete_resource()`** - Safely deletes resources with confirmation requirements

### Key Features
- **Enforced Token-Based Workflow**: Prevents resource creation without user transparency
- **Configurable Security Scanning**: `SECURITY_SCANNING=enabled/disabled` environment variable
- **Comprehensive Testing**: 90%+ test coverage with 315+ test cases
- **CloudFormation Template Generation**: Generate IaC from existing resources via `create_template()`
- **Automatic Management Tags**: Default compliance tags applied to all resources
- **AWS API Error Handling**: User-friendly error messages and troubleshooting

## User Experience

### Before
Users had no standardized way to:
- Manage AWS resources through MCP with integrated security validation
- Get mandatory transparency of infrastructure changes before execution
- Ensure consistent security scanning and compliance tagging
- Generate CloudFormation templates from existing resources via MCP

### After

#### Enforced Token-Based Workflow for Transparency
The server enforces a secure, transparent workflow that **cannot be bypassed**:

```
1. generate_infrastructure_code()
   → Returns properties_token + properties_for_explanation

2. explain(properties_token=token)
   → MANDATORY: Shows complete resource breakdown to user
   → Returns execution_token (consumes properties_token)

3. run_checkov() [if SECURITY_SCANNING=enabled]
   → Validates security compliance
   → Returns checkov_validation_token

4. create_resource(execution_token=token, checkov_validation_token=token)
   → Creates resource using exact explained properties
   → Cannot bypass explanation step
```

#### Configurable Security Scanning

**When `SECURITY_SCANNING=enabled` (default)**:
- Checkov security scanning is **required** before resource creation
- Failed security checks block resource creation with detailed remediation steps
- Users must explicitly acknowledge security risks to proceed

**When `SECURITY_SCANNING=disabled`**:
- Security scanning is bypassed for faster development workflows
- Users receive clear warning about disabled security validation
- Recommended for sandbox/development environments only

#### Example Workflows

**Secure Resource Creation**:
```
User: "Create an S3 bucket for my project"

→ AI calls generate_infrastructure_code()
→ AI calls explain() and shows user:
  "## S3 Bucket Creation
  **Properties**: BucketName: my-project-bucket
  **Security**: Encryption enabled, public access blocked
  **Tags**: MANAGED_BY=CCAPI-MCP-SERVER (auto-applied)"

→ AI calls run_checkov() for security validation
→ AI calls create_resource() with validated tokens
→ Bucket created with security compliance and management tags
```

**Resource Updates with Transparency**:
```
User: "Add versioning to my S3 bucket"

→ AI calls generate_infrastructure_code() with patch document
→ AI calls explain() showing exact changes to be made
→ User sees before/after comparison
→ AI calls update_resource() with explained changes only
```

**Infrastructure Discovery**:
```
User: "Generate CloudFormation for my existing resources"

→ AI calls create_template() to generate IaC from live resources
→ Returns CloudFormation template for version control
→ Can convert to Terraform/CDK as needed
```

### Key Benefits
- **Security First**: Integrated Checkov prevents insecure configurations by default
- **Complete Transparency**: Users always see exactly what will be created/modified
- **Compliance Ready**: Automatic management tags for resource tracking
- **Flexible Security**: Configurable scanning for different environments
- **Error Prevention**: Token workflow prevents accidental resource creation
- **Audit Trail**: All operations include explanation and validation steps
