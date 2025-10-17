# Enable AWS Application Signals for Python on EC2

This guide provides instructions for modifying Infrastructure as Code (IaC) to enable Application Signals for a Python application running on EC2. The examples use CDK TypeScript, but the concepts apply to CloudFormation and Terraform as well.

## Overview

To enable Application Signals, you need to modify the IaC to:
1. Add CloudWatchAgentServerPolicy to the EC2 instance role
2. Install and configure the CloudWatch Agent via UserData
3. Install ADOT Python auto-instrumentation via UserData
4. Configure OpenTelemetry environment variables and start the application (Docker or non-Docker)

**Note:** This guide covers both Docker-based and non-Docker deployments. Follow the appropriate sections for your deployment type.

## Prerequisites

**IMPORTANT:** Install these system dependencies at the beginning of your UserData script, BEFORE any other Application Signals setup commands:

### Required Packages (Amazon Linux)
```bash
yum install -y wget docker python3-pip
```

**Critical:** `wget` is NOT pre-installed on Amazon Linux 2023 (though it is on AL2). Always install it explicitly.

### Installation Pattern
```typescript
instance.userData.addCommands(
  'yum update -y',
  'yum install -y wget docker python3-pip',  // Install all dependencies first
  // ... then proceed with CloudWatch Agent installation
);
```

### Other Distributions
- **Ubuntu/Debian:** `apt-get install -y wget docker.io python3-pip`
- **RHEL/CentOS:** `yum install -y wget docker python3-pip`

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

## Step 3: Install ADOT Python Auto-Instrumentation

Add this command to UserData to install the AWS Distro for OpenTelemetry Python package:

```typescript
instance.userData.addCommands(
  '# Install ADOT Python auto-instrumentation',
  'pip3 install aws-opentelemetry-distro',
);
```

## Step 4: Configure Environment Variables and Start Application

Choose the appropriate configuration based on your deployment type:

### Option A: Docker-based Deployment

If your application runs in a Docker container, set environment variables via `-e` flags in the docker run command:

```typescript
instance.userData.addCommands(
  '# Run container with Application Signals environment variables',
  `docker run -d --name {{APP_NAME}} \\`,
  `  -p {{PORT}}:{{PORT}} \\`,
  `  -e PORT={{PORT}} \\`,
  `  -e SERVICE_NAME={{SERVICE_NAME}} \\`,
  `  -e OTEL_METRICS_EXPORTER=none \\`,
  `  -e OTEL_LOGS_EXPORTER=none \\`,
  `  -e OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true \\`,
  `  -e OTEL_PYTHON_DISTRO=aws_distro \\`,
  `  -e OTEL_PYTHON_CONFIGURATOR=aws_configurator \\`,
  `  -e OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \\`,
  `  -e OTEL_TRACES_SAMPLER=xray \\`,
  `  -e OTEL_TRACES_SAMPLER_ARG=endpoint=http://localhost:2000 \\`,
  `  -e OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics \\`,
  `  -e OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4316/v1/traces \\`,
  `  -e OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}} \\`,
  `  --network host \\`,
  `  {{IMAGE_URI}}`,
);
```

**Important for Docker:** Use `--network host` to allow the container to communicate with the CloudWatch Agent running on the EC2 host at `localhost:4316` and `localhost:2000`. Without this, the container cannot reach the agent because `localhost` inside the container refers to the container's own network namespace, not the host.

### Option B: Non-Docker Deployment

If your application runs directly on EC2 (not in a container), set environment variables and start with the `opentelemetry-instrument` wrapper:

```typescript
instance.userData.addCommands(
  '# Set OpenTelemetry environment variables',
  'export OTEL_METRICS_EXPORTER=none',
  'export OTEL_LOGS_EXPORTER=none',
  'export OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true',
  'export OTEL_PYTHON_DISTRO=aws_distro',
  'export OTEL_PYTHON_CONFIGURATOR=aws_configurator',
  'export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf',
  'export OTEL_TRACES_SAMPLER=xray',
  'export OTEL_TRACES_SAMPLER_ARG=endpoint=http://localhost:2000',
  'export OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics',
  'export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4316/v1/traces',
  'export OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}}',
  '',
  '# Start application with ADOT instrumentation',
  'cd {{APP_DIR}}',
  'opentelemetry-instrument python {{ENTRY_POINT}}',
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
- `{{SERVICE_NAME}}`: The service name for Application Signals (e.g., `my-python-app`)
- `{{APP_DIR}}`: The directory containing the application code (e.g., `/opt/myapp`) - **Non-Docker only**
- `{{ENTRY_POINT}}`: The Python application entry point file (e.g., `app.py`)
- `{{APP_NAME}}`: The container name (e.g., `python-flask`) - **Docker only**
- `{{PORT}}`: The application port (e.g., `5000`) - **Docker only**
- `{{IMAGE_URI}}`: The Docker image URI - **Docker only**

## Important: User Review and Deployment

After modifying the IaC files, the user should:
1. Review all changes to ensure they are correct
2. Deploy the updated infrastructure using their standard deployment process (e.g., `cdk deploy`)
3. Verify Application Signals data appears in the CloudWatch console after deployment
