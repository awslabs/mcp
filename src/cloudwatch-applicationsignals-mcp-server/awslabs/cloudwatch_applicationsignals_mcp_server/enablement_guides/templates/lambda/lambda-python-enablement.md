# Task: Enable AWS Application Signals for Python on AWS Lambda

Your task is to modify Infrastructure as Code (IaC) files to enable AWS Application Signals for Python Lambda functions. You will:

1. Configure X-Ray tracing
2. Add the ADOT Lambda layer
3. Set the required environment variables.

If you cannot determine a value (such as AWS Region): Ask the user for clarification before proceeding. Do not guess or make up values.

## Region-Specific Layer ARNs

Select the correct ARN for your region:

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
  "us-gov-west-1": "arn:aws-us-gov:lambda:us-gov-west-1:399727141365:layer:AWSOpenTelemetryDistroPython:1"
}
```

## Instructions

### Step 1: Enable X-Ray Active Tracing

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

### Step 2: Add ADOT Python Lambda Layer

Use the layer name `AWSOpenTelemetryDistroPython` and select the appropriate ARN from the region-specific list above. Only add the one necessary Layer ARN from the list above, like the examples below.

**CDK:**
```typescript
const myFunction = new lambda.Function(this, 'MyFunction', {
  // ... existing configuration
  layers: [
    // ... keep existing layers
    lambda.LayerVersion.fromLayerVersionArn(
      this,
      'AdotLayer',
      'arn:aws:lambda:us-east-1:615299751070:layer:AWSOpenTelemetryDistroPython:19'
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
    "arn:aws:lambda:us-east-1:615299751070:layer:AWSOpenTelemetryDistroPython:19"
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
      - arn:aws:lambda:us-east-1:615299751070:layer:AWSOpenTelemetryDistroPython:19
```

### Step 3: Set Environment Variable

Add the `AWS_LAMBDA_EXEC_WRAPPER` environment variable with value `/opt/otel-instrument`.

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
      'arn:aws:lambda:us-east-1:615299751070:layer:AWSOpenTelemetryDistroPython:19'
    ),
  ],
  environment: {
    AWS_LAMBDA_EXEC_WRAPPER: '/opt/otel-instrument',
  },
});
```

## Completion

**Tell the user:**

"I've completed the Application Signals enablement for your Python Lambda function. Here's what I modified:

**Configuration Changes:**
- X-Ray Tracing: Enabled active tracing
- ADOT Layer: Added AWSOpenTelemetryDistroPython layer
- Environment Variable: Set AWS_LAMBDA_EXEC_WRAPPER=/opt/otel-instrument

**Next Steps:**
1. Review the changes I made using `git diff`
2. Deploy your infrastructure:
   - For CDK: `cdk deploy`
   - For Terraform: `terraform apply`
   - For CloudFormation: Deploy your stack
3. After deployment, invoke your Lambda function to generate telemetry data

**Verification:**
Once deployed, you can verify Application Signals is working by:
- Opening the AWS CloudWatch Console
- Navigating to Application Signals → Services
- Looking for your Lambda function service
- Checking that traces and metrics are being collected

**Monitor Application Health:**
After enablement, you can monitor your Lambda function's operational health using Application Signals dashboards. For more information, see [Monitor the operational health of your applications with Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Services.html).

Let me know if you'd like me to make any adjustments before you deploy!"
