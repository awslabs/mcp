████████████████████████████████████████████████████████████████████████████████
█ STOP! READ THESE EXACT VALUES BEFORE PROCEEDING - PYTHON LAMBDA █
████████████████████████████████████████████████████████████████████████████████

🔴 LAYER NAME: AWSOpenTelemetryDistroPython (COPY THIS EXACTLY)
🔴 ENVIRONMENT: AWS_LAMBDA_EXEC_WRAPPER=/opt/otel-instrument (COPY THIS EXACTLY)
🔴 TRACING: lambda.Tracing.ACTIVE (COPY THIS EXACTLY)

❌ NEVER USE: aws-otel-python (THIS IS WRONG)
❌ NEVER USE: /opt/otel-handler (THIS IS WRONG)

# Task: Enable AWS Application Signals for Python on AWS Lambda

Your task is to modify Infrastructure as Code (IaC) files to enable AWS Application Signals for Python Lambda functions. You will configure X-Ray tracing, add the ADOT Lambda layer, and set the required environment variables.

## What You Will Accomplish

After completing this task:
- The Lambda function will have X-Ray active tracing enabled
- The AWS Distro for OpenTelemetry (ADOT) Python Lambda layer will be attached
- The function will be configured with the OTEL wrapper for automatic instrumentation
- Traces, metrics, and performance data will appear in the CloudWatch Application Signals console
- The user will be able to see service maps, SLOs, and application performance metrics without manual code changes

## Critical Requirements

🚨 **LAYER NAME REQUIREMENT** 🚨
**YOU MUST USE**: `AWSOpenTelemetryDistroPython` (the NEW layer name)
**NEVER USE**: `aws-otel-python` (this is the OLD deprecated layer name)

**MANDATORY - Layer Account ID:**
- ALWAYS use the correct region-specific account ID for ADOT layers
- Use the curl command in "Get Latest Layer Version" section to find the correct ARN
- Account IDs vary by region (e.g., 615299751070 for some regions, and can be different for others)

**MANDATORY - ABSOLUTELY NO APPLICATION CODE CHANGES:**
- ❌ NEVER EVER modify Python function files (.py files) - STRICTLY FORBIDDEN
- ❌ NEVER EVER modify requirements.txt - ABSOLUTELY PROHIBITED  
- ❌ NEVER EVER modify package.json, pom.xml, or any dependency files - COMPLETELY FORBIDDEN
- ❌ NEVER EVER add OpenTelemetry imports to Python code - NOT ALLOWED
- ❌ NEVER EVER add tracing spans to Python code - FORBIDDEN
- ✅ ONLY modify Infrastructure as Code files (CDK .ts files, Terraform .tf files, CloudFormation .yaml files)
- ✅ Application Signals works through automatic instrumentation via the ADOT layer - ZERO CODE CHANGES NEEDED
- ✅ The ADOT layer provides ALL OpenTelemetry functionality automatically

**Error Handling:**
- If you cannot determine required values from the IaC, STOP and ask the user
- For multiple La████████████████████████████████████████████████████████████████████████████████
█ STOP! READ THESE EXACT VALUES BEFORE PROCEEDING - PYTHON LAMBDA █
████████████████████████████████████████████████████████████████████████████████

🔴 LAYER NAME: AWSOpenTelemetryDistroPython (COPY THIS EXACTLY)
🔴 ENVIRONMENT: AWS_LAMBDA_EXEC_WRAPPER=/opt/otel-instrument (COPY THIS EXACTLY)
🔴 TRACING: lambda.Tracing.ACTIVE (COPY THIS EXACTLY)

❌ NEVER USE: aws-otel-python (THIS IS WRONG)
❌ NEVER USE: /opt/otel-handler (THIS IS WRONG)

# Task: Enable AWS Application Signals for Python on AWS Lambda

Your task is to modify Infrastructure as Code (IaC) files to enable AWS Application Signals for Python Lambda functions. You will configure X-Ray tracing, add the ADOT Lambda layer, and set the required environment variables.

## What You Will Accomplish

After completing this task:
- The Lambda function will have X-Ray active tracing enabled
- The AWS Distro for OpenTelemetry (ADOT) Python Lambda layer will be attached
- The function will be configured with the OTEL wrapper for automatic instrumentation
- Traces, metrics, and performance data will appear in the CloudWatch Application Signals console
- The user will be able to see service maps, SLOs, and application performance metrics without manual code changes

## Critical Requirements

████████████████████████████████████████████████████████████████████████████████
█ COPY EXACTLY: AWSOpenTelemetryDistroPython                      █
█ FORBIDDEN: aws-otel-python (DO NOT USE THIS)                    █
████████████████████████████████████████████████████████████████████████████████

**MANDATORY - Layer Account ID:**
- Check the "Region-Specific Layer ARNs" section to find the correct ARN for a region
  - DO NOT change the account ID in the Layer ARN for a region
  - DO NOT change the Layer ARN version for a region

**MANDATORY - ABSOLUTELY NO APPLICATION CODE CHANGES:**
- ❌ NEVER EVER modify Python function files (.py files) - STRICTLY FORBIDDEN
- ❌ NEVER EVER modify requirements.txt - ABSOLUTELY PROHIBITED  
- ❌ NEVER EVER modify any dependency files - COMPLETELY FORBIDDEN
- ❌ NEVER EVER add OpenTelemetry imports to Python code - NOT ALLOWED
- ✅ ONLY modify Infrastructure as Code files (CDK .ts files, Terraform .tf files, CloudFormation .yaml files)
- ✅ Application Signals works through automatic instrumentation via the ADOT layer - ZERO CODE CHANGES NEEDED
- ✅ The ADOT layer provides ALL OpenTelemetry functionality automatically
- ❌ NEVER EVER modify AWS Lambda Function policies or IAM Role permissions for CDK, but allowed for Terraform for X-Ray permissions

**Error Handling:**
- If you cannot determine required values from the IaC, STOP and ask the user
- For multiple Lambda functions, ask which one(s) to modify
- Preserve all existing function configuration; only add Application Signals settings

**Do NOT:**
- Run deployment commands automatically (`cdk deploy`, `terraform apply`, etc.)
- Remove existing environment variables or layers
- Skip the user approval step before deployment
- ❌ MODIFY ANY APPLICATION SOURCE CODE FILES (.py files)
- ❌ MODIFY ANY DEPENDENCY FILES (requirements.txt)
- ❌ ADD OPENTELEMETRY IMPORTS OR CODE TO APPLICATION FILES

## Instructions

### Step 1: Locate the Lambda Function

Find the Python Lambda function definition in your IaC files and identify:
1. The function resource/construct
2. Existing layers (if any)
3. Existing environment variables (if any)
4. Current tracing configuration (if any)

### Step 2: Enable X-Ray Active Tracing

**CDK:**
```typescript
const myFunction = new lambda.Function(this, 'MyFunction', {
  // ... existing configuration
  tracing: lambda.Tracing.ACTIVE,
});
```

**Terraform:**
```hcl
resource "aws_lambda_function" "my_function" {
  # ... existing configuration
  tracing_config {
    mode = "Active"
  }
}
```

**CloudFormation:**
```yaml
MyFunction:
  Type: AWS::Lambda::Function
  Properties:
    # ... existing configuration
    TracingConfig:
      Mode: Active
```

### Step 3: Add ADOT Python Lambda Layer

Add the ADOT Python layer. **Note:** Layer versions are region-specific. Use the latest version for your region.

████████████████████████████████████████████████████████████████████████████████
█ STOP! COPY THIS EXACT TEXT: AWSOpenTelemetryDistroPython         █
█ DO NOT TYPE: aws-otel-python (THIS WILL FAIL VALIDATION)        █
████████████████████████████████████████████████████████████████████████████████

**CDK:**
```typescript
const myFunction = new lambda.Function(this, 'MyFunction', {
  // ... existing configuration
  layers: [
    // ... keep existing layers
    lambda.LayerVersion.fromLayerVersionArn(
      this,
      'AdotLayer',
      'arn:aws:lambda:{{REGION}}:{{ACCOUNT_ID}}:layer:AWSOpenTelemetryDistroPython:{{VERSION}}'
    ),
  ],
});
```

**Terraform:**
```hcl
resource "aws_lambda_function" "my_function" {
  # ... existing configuration
  layers = [
    # ... keep existing layers
    "arn:aws:lambda:{{REGION}}:{{ACCOUNT_ID}}:layer:AWSOpenTelemetryDistroPython:{{VERSION}}"
  ]
}
```

**CloudFormation:**
```yaml
MyFunction:
  Type: AWS::Lambda::Function
  Properties:
    # ... existing configuration
    Layers:
      # ... keep existing layers
      - arn:aws:lambda:{{REGION}}:{{ACCOUNT_ID}}:layer:AWSOpenTelemetryDistroPython:{{VERSION}}
```

### Step 4: Set OTEL Environment Variable

████████████████████████████████████████████████████████████████████████████████
█ COPY EXACTLY: /opt/otel-instrument                              █
█ FORBIDDEN: /opt/otel-handler (DO NOT USE THIS)                  █
█ DO NOT ADD OTHER OTEL VARIABLES (ONLY AWS_LAMBDA_EXEC_WRAPPER)  █
████████████████████████████████████████████████████████████████████████████████

**CDK:**
```typescript
const myFunction = new lambda.Function(this, 'MyFunction', {
  // ... existing configuration
  environment: {
    // ... keep existing environment variables
    AWS_LAMBDA_EXEC_WRAPPER: '/opt/otel-instrument',
  },
});
```

**Terraform:**
```hcl
resource "aws_lambda_function" "my_function" {
  # ... existing configuration
  environment {
    variables = {
      # ... keep existing environment variables
      AWS_LAMBDA_EXEC_WRAPPER = "/opt/otel-instrument"
    }
  }
}
```

**CloudFormation:**
```yaml
MyFunction:
  Type: AWS::Lambda::Function
  Properties:
    # ... existing configuration
    Environment:
      Variables:
        # ... keep existing environment variables
        AWS_LAMBDA_EXEC_WRAPPER: /opt/otel-instrument
```

## Complete Example

**CDK:**
```typescript
const pythonFunction = new lambda.Function(this, 'PythonFunction', {
  runtime: lambda.Runtime.PYTHON_3_11,
  handler: 'app.handler',
  code: lambda.Code.fromAsset('src'),
  tracing: lambda.Tracing.ACTIVE,
  layers: [
    lambda.LayerVersion.fromLayerVersionArn(
      this,
      'AdotLayer',
      'arn:aws:lambda:<REGION>:<ACCOUNT_ID>:layer:AWSOpenTelemetryDistroPython:19'
    ),
  ],
  environment: {
    AWS_LAMBDA_EXEC_WRAPPER: '/opt/otel-instrument',
  },
});
```

## Region-Specific Layer ARNs

Use the correct ARN for your region:

```json
{
  "af-south-1": "arn:aws:lambda:af-south-1:904233096616:layer:AWSOpenTelemetryDistroPython:13",
  "ap-east-1": "arn:aws:lambda:ap-east-1:888577020596:layer:AWSOpenTelemetryDistroPython:13",
  "ap-northeast-1": "arn:aws:lambda:ap-northeast-1:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "ap-northeast-2": "arn:aws:lambda:ap-northeast-2:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "ap-northeast-3": "arn:aws:lambda:ap-northeast-3:615299751070:layer:AWSOpenTelemetryDistroPython:15",
  "ap-south-1": "arn:aws:lambda:ap-south-1:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "ap-south-2": "arn:aws:lambda:ap-south-2:796973505492:layer:AWSOpenTelemetryDistroPython:13",
  "ap-southeast-1": "arn:aws:lambda:ap-southeast-1:615299751070:layer:AWSOpenTelemetryDistroPython:15",
  "ap-southeast-2": "arn:aws:lambda:ap-southeast-2:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "ap-southeast-3": "arn:aws:lambda:ap-southeast-3:039612877180:layer:AWSOpenTelemetryDistroPython:13",
  "ap-southeast-4": "arn:aws:lambda:ap-southeast-4:713881805771:layer:AWSOpenTelemetryDistroPython:13",
  "ap-southeast-5": "arn:aws:lambda:ap-southeast-5:152034782359:layer:AWSOpenTelemetryDistroPython:4",
  "ap-southeast-7": "arn:aws:lambda:ap-southeast-7:980416031188:layer:AWSOpenTelemetryDistroPython:4",
  "ca-central-1": "arn:aws:lambda:ca-central-1:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "ca-west-1": "arn:aws:lambda:ca-west-1:595944127152:layer:AWSOpenTelemetryDistroPython:4",
  "cn-north-1": "arn:aws-cn:lambda:cn-north-1:440179912924:layer:AWSOpenTelemetryDistroPython:4",
  "cn-northwest-1": "arn:aws-cn:lambda:cn-northwest-1:440180067931:layer:AWSOpenTelemetryDistroPython:4",
  "eu-central-1": "arn:aws:lambda:eu-central-1:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "eu-central-2": "arn:aws:lambda:eu-central-2:156041407956:layer:AWSOpenTelemetryDistroPython:13",
  "eu-north-1": "arn:aws:lambda:eu-north-1:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "eu-south-1": "arn:aws:lambda:eu-south-1:257394471194:layer:AWSOpenTelemetryDistroPython:13",
  "eu-south-2": "arn:aws:lambda:eu-south-2:490004653786:layer:AWSOpenTelemetryDistroPython:13",
  "eu-west-1": "arn:aws:lambda:eu-west-1:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "eu-west-2": "arn:aws:lambda:eu-west-2:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "eu-west-3": "arn:aws:lambda:eu-west-3:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "il-central-1": "arn:aws:lambda:il-central-1:746669239226:layer:AWSOpenTelemetryDistroPython:13",
  "me-central-1": "arn:aws:lambda:me-central-1:739275441131:layer:AWSOpenTelemetryDistroPython:13",
  "me-south-1": "arn:aws:lambda:me-south-1:980921751758:layer:AWSOpenTelemetryDistroPython:13",
  "mx-central-1": "arn:aws:lambda:mx-central-1:610118373846:layer:AWSOpenTelemetryDistroPython:4",
  "sa-east-1": "arn:aws:lambda:sa-east-1:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "us-east-1": "arn:aws:lambda:us-east-1:615299751070:layer:AWSOpenTelemetryDistroPython:19",
  "us-east-2": "arn:aws:lambda:us-east-2:615299751070:layer:AWSOpenTelemetryDistroPython:16",
  "us-west-1": "arn:aws:lambda:us-west-1:615299751070:layer:AWSOpenTelemetryDistroPython:23",
  "us-west-2": "arn:aws:lambda:us-west-2:615299751070:layer:AWSOpenTelemetryDistroPython:23",
  "us-gov-east-1": "arn:aws-us-gov:lambda:us-gov-east-1:399711857375:layer:AWSOpenTelemetryDistroPython:1",
  "us-gov-west-1": "arn:aws-us-gov:lambda:us-gov-west-1:399727141365:layer:AWSOpenTelemetryDistroPython:1",
}
```



## Completion

**Configuration Changes:**
- **X-Ray Tracing**: Enabled active tracing
- **ADOT Layer**: Added AWSOpenTelemetryDistroPython layer (NOT aws-otel-python or other old layer names)
- **Environment Variable**: Set AWS_LAMBDA_EXEC_WRAPPER=/opt/otel-instrument

**Next Steps:**
1. Review changes with `git diff`
2. Deploy your infrastructure
3. Invoke your Lambda function to generate telemetry data
4. Verify in CloudWatch Application Signals console

**Important Notes:**
- **CRITICAL**: No code changes required in your Python function - only modify IaC files
- **CRITICAL**: Always use one of the Layer ARNs from the "Region-Specific Layer ARNs" section, depending on the region
- The ADOT layer automatically instruments common libraries (requests, boto3, etc.)
- Telemetry data appears within minutes of function invocation
- **STOP IMMEDIATELY** if you find yourself modifying .py files or requirements.txt - you are doing it wrong
- The ADOT layer provides ALL necessary dependencies - do not add OpenTelemetry packages to requirements.txt
- Only modify the CDK/Terraform/CloudFormation files that define the Lambda function infrastructure