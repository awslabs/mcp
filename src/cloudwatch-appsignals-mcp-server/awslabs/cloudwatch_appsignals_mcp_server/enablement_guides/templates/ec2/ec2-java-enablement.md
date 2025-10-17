# Enable AWS Application Signals for Java on EC2

This guide provides instructions for modifying Infrastructure as Code (IaC) to enable Application Signals for a Java application running on EC2. The examples use CDK TypeScript, but the concepts apply to CloudFormation and Terraform as well.

## Overview

To enable Application Signals, you need to modify the IaC to:
1. Add CloudWatchAgentServerPolicy to the EC2 instance role
2. Install and configure the CloudWatch Agent via UserData
3. Download ADOT Java auto-instrumentation agent via UserData
4. Configure OpenTelemetry environment variables and start the application (Docker or non-Docker)

**Note:** This guide covers both Docker-based and non-Docker deployments. Follow the appropriate sections for your deployment type.

## Prerequisites

**IMPORTANT:** Install these system dependencies at the beginning of your UserData script, BEFORE any other Application Signals setup commands:

### Required Packages (Amazon Linux)
```bash
yum install -y wget docker
```

**Critical:** `wget` is NOT pre-installed on Amazon Linux 2023 (though it is on AL2). Always install it explicitly.

### Installation Pattern
```typescript
instance.userData.addCommands(
  'yum update -y',
  'yum install -y wget docker',  // Install all dependencies first
  // ... then proceed with CloudWatch Agent installation
);
```

### Other Distributions
- **Ubuntu/Debian:** `apt-get install -y wget docker.io`
- **RHEL/CentOS:** `yum install -y wget docker`

## Step 1: Update IAM Role

Modify the EC2 instance role to include CloudWatchAgentServerPolicy:

```typescript
const role = new iam.Role(this, 'AppRole', {
  assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
  managedPolicies: [
    iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
    // ... existing policies
  ],
});
```

## Step 2: Install and Configure CloudWatch Agent

Add these commands to the EC2 instance's UserData to install and start the CloudWatch Agent:

```typescript
instance.userData.addCommands(
  '# Download and install CloudWatch Agent',
  'wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm',
  'rpm -U ./amazon-cloudwatch-agent.rpm',
  '',
  '# Create CloudWatch Agent configuration for Application Signals',
  'cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF',
  '{',
  '  "traces": {',
  '    "traces_collected": {',
  '      "application_signals": {}',
  '    }',
  '  },',
  '  "logs": {',
  '    "metrics_collected": {',
  '      "application_signals": {}',
  '    }',
  '  }',
  '}',
  'EOF',
  '',
  '# Start CloudWatch Agent with Application Signals configuration',
  '/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \\',
  '  -a fetch-config \\',
  '  -m ec2 \\',
  '  -s \\',
  '  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json',
);
```

## Step 3: Download ADOT Java Auto-Instrumentation Agent

Add these commands to UserData to download the AWS Distro for OpenTelemetry Java agent:

```typescript
instance.userData.addCommands(
  '# Download ADOT Java auto-instrumentation agent',
  'wget -O /opt/aws-opentelemetry-agent.jar https://github.com/aws-observability/aws-otel-java-instrumentation/releases/latest/download/aws-opentelemetry-agent.jar',
);
```

## Step 4: Configure Environment Variables and Start Application

Choose the appropriate configuration based on your deployment type:

### Option A: Docker-based Deployment

If your application runs in a Docker container, you need to:

1. **Mount the ADOT Java agent into the container** and set environment variables via `-e` flags:

```typescript
instance.userData.addCommands(
  '# Run container with ADOT Java agent and Application Signals environment variables',
  `docker run -d --name {{APP_NAME}} \\`,
  `  -p {{PORT}}:{{PORT}} \\`,
  `  -v /opt/aws-opentelemetry-agent.jar:/opt/aws-opentelemetry-agent.jar \\`,
  `  -e PORT={{PORT}} \\`,
  `  -e SERVICE_NAME={{SERVICE_NAME}} \\`,
  `  -e JAVA_TOOL_OPTIONS="-javaagent:/opt/aws-opentelemetry-agent.jar" \\`,
  `  -e OTEL_METRICS_EXPORTER=none \\`,
  `  -e OTEL_LOGS_EXPORTER=none \\`,
  `  -e OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true \\`,
  `  -e OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics \\`,
  `  -e OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \\`,
  `  -e OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4316/v1/traces \\`,
  `  -e OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}} \\`,
  `  --network host \\`,
  `  {{IMAGE_URI}}`,
);
```

**Important for Docker:**
- Use `-v /opt/aws-opentelemetry-agent.jar:/opt/aws-opentelemetry-agent.jar` to mount the agent JAR file from the host into the container
- Use `--network host` to allow the container to communicate with the CloudWatch Agent running on the EC2 host at `localhost:4316` and `localhost:2000`. Without this, the container cannot reach the agent because `localhost` inside the container refers to the container's own network namespace, not the host.

### Option B: Non-Docker Deployment

If your application runs directly on EC2 (not in a container), set environment variables and start with the Java agent:

```typescript
instance.userData.addCommands(
  '# Set OpenTelemetry environment variables and start application',
  'cd {{APP_DIR}}',
  'JAVA_TOOL_OPTIONS=" -javaagent:/opt/aws-opentelemetry-agent.jar" \\',
  'OTEL_METRICS_EXPORTER=none \\',
  'OTEL_LOGS_EXPORTER=none \\',
  'OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true \\',
  'OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics \\',
  'OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \\',
  'OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4316/v1/traces \\',
  'OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}} \\',
  'java -jar {{JAR_FILE}}',
);
```

## Translation Notes for Other IaC Tools

**CloudFormation (YAML):**
- IAM role: Add `CloudWatchAgentServerPolicy` to `ManagedPolicyArns`
- UserData: Add commands to `AWS::EC2::Instance` `UserData` property using `Fn::Base64` and `Fn::Sub`

**Terraform:**
- IAM role: Add `arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy` to `aws_iam_role_policy_attachment`
- UserData: Add commands to `aws_instance` `user_data` property

## Placeholders

The following placeholders should be replaced with actual values from the customer's environment:
- `{{SERVICE_NAME}}`: The service name for Application Signals (e.g., `my-java-app`)
- `{{APP_DIR}}`: The directory containing the application code (e.g., `/opt/myapp`) - **Non-Docker only**
- `{{JAR_FILE}}`: The Java application JAR file (e.g., `myapp-1.0.0.jar`) - **Non-Docker only**
- `{{APP_NAME}}`: The container name (e.g., `java-springboot`) - **Docker only**
- `{{PORT}}`: The application port (e.g., `8080`) - **Docker only**
- `{{IMAGE_URI}}`: The Docker image URI - **Docker only**

## Important: User Review and Deployment

After modifying the IaC files, the user should:
1. Review all changes to ensure they are correct
2. Deploy the updated infrastructure using their standard deployment process (e.g., `cdk deploy`)
3. Verify Application Signals data appears in the CloudWatch console after deployment
