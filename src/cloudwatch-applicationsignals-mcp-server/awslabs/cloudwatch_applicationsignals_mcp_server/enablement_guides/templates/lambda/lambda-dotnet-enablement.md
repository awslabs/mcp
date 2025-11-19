# Task: Enable AWS Application Signals for .NET on AWS Lambda

Your task is to modify Infrastructure as Code (IaC) files to enable AWS Application Signals for .NET Lambda functions. You will:

1. Add IAM permissions for Application Signals
2. Configure X-Ray tracing
3. Add the ADOT Lambda layer
4. Set the required environment variables.

If you cannot determine a value (such as AWS Region): Ask the user for clarification before proceeding. Do not guess or make up values.

## Region-Specific Layer ARNs

Select the correct ARN for your region:

```json
{
  "af-south-1": "arn:aws:lambda:af-south-1:904233096616:layer:AWSOpenTelemetryDistroDotNet:6",
  "ap-east-1": "arn:aws:lambda:ap-east-1:888577020596:layer:AWSOpenTelemetryDistroDotNet:6",
  "ap-northeast-1": "arn:aws:lambda:ap-northeast-1:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "ap-northeast-2": "arn:aws:lambda:ap-northeast-2:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "ap-northeast-3": "arn:aws:lambda:ap-northeast-3:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "ap-south-1": "arn:aws:lambda:ap-south-1:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "ap-south-2": "arn:aws:lambda:ap-south-2:796973505492:layer:AWSOpenTelemetryDistroDotNet:6",
  "ap-southeast-1": "arn:aws:lambda:ap-southeast-1:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "ap-southeast-2": "arn:aws:lambda:ap-southeast-2:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "ap-southeast-3": "arn:aws:lambda:ap-southeast-3:039612877180:layer:AWSOpenTelemetryDistroDotNet:6",
  "ap-southeast-4": "arn:aws:lambda:ap-southeast-4:713881805771:layer:AWSOpenTelemetryDistroDotNet:6",
  "ap-southeast-5": "arn:aws:lambda:ap-southeast-5:152034782359:layer:AWSOpenTelemetryDistroDotNet:2",
  "ap-southeast-7": "arn:aws:lambda:ap-southeast-7:980416031188:layer:AWSOpenTelemetryDistroDotNet:2",
  "ca-central-1": "arn:aws:lambda:ca-central-1:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "ca-west-1": "arn:aws:lambda:ca-west-1:595944127152:layer:AWSOpenTelemetryDistroDotNet:2",
  "cn-north-1": "arn:aws-cn:lambda:cn-north-1:440179912924:layer:AWSOpenTelemetryDistroDotNet:2",
  "cn-northwest-1": "arn:aws-cn:lambda:cn-northwest-1:440180067931:layer:AWSOpenTelemetryDistroDotNet:2",
  "eu-central-1": "arn:aws:lambda:eu-central-1:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "eu-central-2": "arn:aws:lambda:eu-central-2:156041407956:layer:AWSOpenTelemetryDistroDotNet:6",
  "eu-north-1": "arn:aws:lambda:eu-north-1:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "eu-south-1": "arn:aws:lambda:eu-south-1:257394471194:layer:AWSOpenTelemetryDistroDotNet:6",
  "eu-south-2": "arn:aws:lambda:eu-south-2:490004653786:layer:AWSOpenTelemetryDistroDotNet:6",
  "eu-west-1": "arn:aws:lambda:eu-west-1:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "eu-west-2": "arn:aws:lambda:eu-west-2:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "eu-west-3": "arn:aws:lambda:eu-west-3:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "il-central-1": "arn:aws:lambda:il-central-1:746669239226:layer:AWSOpenTelemetryDistroDotNet:6",
  "me-central-1": "arn:aws:lambda:me-central-1:739275441131:layer:AWSOpenTelemetryDistroDotNet:6",
  "me-south-1": "arn:aws:lambda:me-south-1:980921751758:layer:AWSOpenTelemetryDistroDotNet:6",
  "mx-central-1": "arn:aws:lambda:mx-central-1:610118373846:layer:AWSOpenTelemetryDistroDotNet:2",
  "sa-east-1": "arn:aws:lambda:sa-east-1:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "us-east-1": "arn:aws:lambda:us-east-1:615299751070:layer:AWSOpenTelemetryDistroDotNet:7",
  "us-east-2": "arn:aws:lambda:us-east-2:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "us-west-1": "arn:aws:lambda:us-west-1:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "us-west-2": "arn:aws:lambda:us-west-2:615299751070:layer:AWSOpenTelemetryDistroDotNet:6",
  "us-gov-east-1": "arn:aws-us-gov:lambda:us-gov-east-1:399711857375:layer:AWSOpenTelemetryDistroDotNet:1",
  "us-gov-west-1": "arn:aws-us-gov:lambda:us-gov-west-1:399727141365:layer:AWSOpenTelemetryDistroDotNet:1"
}
```

## Instructions

### Step 1: Add IAM Permissions

Add the AWS managed policy `CloudWatchLambdaApplicationSignalsExecutionRolePolicy` to the Lambda function's execution role.

**CDK:**
```typescript
const role = new iam.Role(this, 'LambdaRole', {
  assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
  managedPolicies: [
    iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
    iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLambdaApplicationSignalsExecutionRolePolicy'),
    // ... keep existing policies
  ],
});

const myFunction = new lambda.Function(this, 'MyFunction', {
  // ... existing configuration
  role: role,
});
```

**Terraform:**
```hcl
resource "aws_iam_role" "lambda_role" {
  name = "lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "application_signals" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLambdaApplicationSignalsExecutionRolePolicy"
}

resource "aws_lambda_function" "my_function" {
  # ... existing configuration
  role = aws_iam_role.lambda_role.arn
}
```

**CloudFormation:**
```yaml
LambdaRole:
  Type: AWS::IAM::Role
  Properties:
    AssumeRolePolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Principal:
            Service: lambda.amazonaws.com
          Action: sts:AssumeRole
    ManagedPolicyArns:
      - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      - arn:aws:iam::aws:policy/CloudWatchLambdaApplicationSignalsExecutionRolePolicy
      # ... keep existing policies

MyFunction:
  Type: AWS::Lambda::Function
  Properties:
    # ... existing configuration
    Role: !GetAtt LambdaRole.Arn
```

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

### Step 3: Add ADOT .NET Lambda Layer

Use the layer name `AWSOpenTelemetryDistroDotNet` with automatic region detection. The code below includes a complete mapping that will automatically select the correct layer ARN based on your deployment region.

**CDK:**
```typescript
const layerArns: { [region: string]: string } = {
  'af-south-1': 'arn:aws:lambda:af-south-1:904233096616:layer:AWSOpenTelemetryDistroDotNet:6',
  'ap-east-1': 'arn:aws:lambda:ap-east-1:888577020596:layer:AWSOpenTelemetryDistroDotNet:6',
  // ... (see Region-Specific Layer ARNs section above for complete mapping)
};

const myFunction = new lambda.Function(this, 'MyFunction', {
  // ... existing configuration
  layers: [
    // ... keep existing layers
    lambda.LayerVersion.fromLayerVersionArn(
      this,
      'AdotLayer',
      layerArns[this.region]
    ),
  ],
});
```

**Terraform:**
```hcl
locals {
  layer_arns = {
    "af-south-1"     = "arn:aws:lambda:af-south-1:904233096616:layer:AWSOpenTelemetryDistroDotNet:6"
    "ap-east-1"      = "arn:aws:lambda:ap-east-1:888577020596:layer:AWSOpenTelemetryDistroDotNet:6"
    # ... (see Region-Specific Layer ARNs section above for complete mapping)
  }
}

data "aws_region" "current" {}

resource "aws_lambda_function" "my_function" {
  # ... existing configuration
  layers = [
    # ... keep existing layers
    local.layer_arns[data.aws_region.current.name]
  ]
}
```

**CloudFormation:**
```yaml
Mappings:
  LayerArns:
    af-south-1:
      arn: arn:aws:lambda:af-south-1:904233096616:layer:AWSOpenTelemetryDistroDotNet:6
    ap-east-1:
      arn: arn:aws:lambda:ap-east-1:888577020596:layer:AWSOpenTelemetryDistroDotNet:6
    # ... (see Region-Specific Layer ARNs section above for complete mapping)

Resources:
  MyFunction:
    Type: AWS::Lambda::Function
    Properties:
      # ... existing configuration
      Layers:
        # ... keep existing layers
        - !FindInMap [LayerArns, !Ref 'AWS::Region', arn]
```

### Step 4: Set Environment Variable

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
const layerArns: { [region: string]: string } = {
  'af-south-1': 'arn:aws:lambda:af-south-1:904233096616:layer:AWSOpenTelemetryDistroDotNet:6',
  'ap-east-1': 'arn:aws:lambda:ap-east-1:888577020596:layer:AWSOpenTelemetryDistroDotNet:6',
  // ... (see Region-Specific Layer ARNs section above for complete mapping)
};

const dotnetFunction = new lambda.Function(this, 'DotNetFunction', {
  runtime: lambda.Runtime.DOTNET_6,
  handler: 'MyApp::MyApp.Function::FunctionHandler',
  code: lambda.Code.fromAsset('src/MyApp/bin/Release/net6.0/publish'),
  tracing: lambda.Tracing.ACTIVE,
  layers: [
    lambda.LayerVersion.fromLayerVersionArn(
      this,
      'AdotLayer',
      layerArns[this.region]
    ),
  ],
  environment: {
    AWS_LAMBDA_EXEC_WRAPPER: '/opt/otel-instrument',
  },
});
```

## Completion

**Tell the user:**

"I've completed the Application Signals enablement for your .NET Lambda function. Here's what I modified:

**Configuration Changes:**
- IAM Permissions: Added CloudWatchLambdaApplicationSignalsExecutionRolePolicy
- X-Ray Tracing: Enabled active tracing
- ADOT Layer: Added AWSOpenTelemetryDistroDotNet layer
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
