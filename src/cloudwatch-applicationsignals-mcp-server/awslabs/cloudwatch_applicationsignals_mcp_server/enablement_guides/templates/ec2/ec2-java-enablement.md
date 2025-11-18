# Task: Enable AWS Application Signals for Java on EC2

Your task is to modify Infrastructure as Code (IaC) files to enable AWS Application Signals for a Java application running on EC2 instances. You will update IAM permissions, install monitoring agents, and configure OpenTelemetry instrumentation through UserData scripts.

## What You Will Accomplish

After completing this task:
- The EC2 instance will have permissions to send telemetry data to CloudWatch
- The CloudWatch Agent will be installed and configured for Application Signals
- The Java application will be automatically instrumented with AWS Distro for OpenTelemetry (ADOT)
- Traces, metrics, and performance data will appear in the CloudWatch Application Signals console
- The user will be able to see service maps, SLOs, and application performance metrics without manual code instrumentation

## Critical Requirements

**Error Handling:**
- If you cannot determine required values from the IaC, STOP and ask the user
- For multiple EC2 instances, ask which one(s) to modify
- Preserve all existing UserData commands; add new ones in sequence

**Do NOT:**
- Run deployment commands automatically (`cdk deploy`, `terraform apply`, etc.)
- Remove existing application startup logic
- Skip the user approval step before deployment

## IaC Tool Support

**Code examples use CDK TypeScript syntax.** If you are working with Terraform or CloudFormation, translate the CDK syntax to the appropriate format while keeping all bash commands identical. The UserData bash commands (CloudWatch Agent installation, ADOT installation, environment variables) are universal across all IaC tools - only the wrapper syntax differs.

## Before You Start: Gather Required Information

Execute these steps to collect the information needed for configuration:

### Step 1: Determine Deployment Type

Read the UserData script and look for the application startup command. This is typically one of the last commands in UserData.

**If you see:**
- `docker run` or `docker start` → Docker deployment
- `java -jar`, `mvn spring-boot:run`, `gradle bootRun`, or similar → Non-Docker deployment

**If unclear:**
- Ask the user: "Is your Java application running in a Docker container or directly on the EC2 instance?" DO NOT GUESS

**Critical distinction:** Where does the Java process run?
- **Docker:** Java runs inside a container → Modify Dockerfile
- **Non-Docker:** Java runs directly on EC2 → Modify UserData

### Step 2: Extract Placeholder Values

Analyze the existing IaC to determine these values for Application Signals enablement:

- `{{SERVICE_NAME}}`
    - **Why It Matters:** Sets the service name displayed in Application Signals console via `OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}}`
    - **How to Find It:** Use the application name, stack name, or construct ID. Look for service/app names in the IaC.
    - **Example Value:** `my-java-app`
    - **Required For:** Both Docker and non-Docker

For Docker-based deployments you will also need to find these additional values:

- `{{PORT}}`
    - **Why It Matters:** Docker port mapping that ensures the container is accessible on the correct port
    - **How to Find It:** Find port mappings in `docker run -p` commands or security group ingress rules
    - **Example Value:** `8080`
    - **Required For:** Docker
- `{{APP_NAME}}`
    - **Why It Matters:** Used to reference the container for operations like `docker logs {{APP_NAME}}`, `docker exec`, health checks, etc.
    - **How to Find It:** Find container name in `docker run --name` or use `{{SERVICE_NAME}}-container`
    - **Example Value:** `java-springboot-app`
    - **Required For:** Docker
- `{{IMAGE_URI}}`
    - **Why It Matters:** This is the identifier for the application that Docker will run
    - **How to Find It:** Find the Docker image in `docker run` or `docker pull` commands
    - **Example Value:** `123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest`
    - **Required For:** Docker

**If you cannot determine a value:** Ask the user for clarification before proceeding. Do not guess or make up values.

### Step 3: Identify Instance OS

Determine the operating system to use the correct package manager and installation commands.

**Amazon Linux**
- **Amazon Linux 2:** Use `yum` package manager
- **Amazon Linux 2023:** Use `dnf` package manager
- **How to detect:** Look for existing package install commands in UserData (check for `yum` or `dnf`), or look for AMI references containing `al2` or `al2023`

**Other Linux distributions:**
- **Ubuntu/Debian:** Use `apt` package manager
- **Fedora/RHEL/CentOS:** Use `dnf` or `yum` package manager

**If unclear:** Look for AMI name/ID in the IaC or ask the user which OS the EC2 instance is running. Do not guess or make up values.

## Instructions

Follow these steps in sequence:

### Step 1: Locate the IaC Files

**Search for EC2 instance definitions** using these patterns:

**CDK:**
```
new ec2.Instance(
ec2.Instance(
CfnInstance(
```

**Terraform:**
```
resource "aws_instance"
```

**CloudFormation:**
```
AWS::EC2::Instance
```

**Read the file(s)** containing the EC2 instance definition. You need to identify:
1. The instance resource/construct
2. The IAM role attached to the instance
3. The UserData script or property

### Step 2: Locate the IAM Role

Find the IAM role attached to the EC2 instance

**CDK:**
```typescript
role: someRole
new iam.Role(this, 'RoleName'
```

### Step 3: Update the IAM Role

Add the CloudWatch Agent Server Policy to the IAM role's managed policies.

**CDK:**
```typescript
const role = new iam.Role(this, 'AppRole', {
  assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
  managedPolicies: [
    iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
    // ... keep existing policies
  ],
});
```

### Step 4: Modify UserData - Add Prerequisites

Add a CloudWatch Agent installation command to the UserData script.

**CRITICAL for Terraform Users:** When modifying Terraform `user_data` heredocs, you MUST preserve the EXACT indentation of existing lines. Terraform's `<<-EOF` syntax strips leading whitespace, but only if indentation is consistent. When adding new bash commands:
- Count the leading spaces/tabs on existing lines in the heredoc
- Apply the SAME amount of leading whitespace to all new lines you add
- Do NOT modify the indentation of any existing lines

If indentation is inconsistent, Terraform will NOT strip the whitespace, causing the deployed script to have leading spaces before `#!/bin/bash`, which will cause cloud-init to fail.

**CDK TypeScript example:**
```typescript
instance.userData.addCommands(
  'dnf install -y amazon-cloudwatch-agent',  // Use dnf for AL2023, yum for AL2
  // ... rest of UserData follows
);
```

**Placement:** Add this command early in the UserData script:
- If system update commands exist (like `dnf update -y`, `apt-get update`), add it immediately after those
- If no system update commands exist, add it at the very beginning of UserData
- This should come before any application dependency installations or application setup commands

**For other Linux distributions:** CloudWatch Agent may not be available via the OS package manager. Refer to [AWS CloudWatch Agent installation docs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/manual-installation.html) for distribution-specific instructions.

### Step 5: Modify UserData - Configure CloudWatch Agent

The CloudWatch Agent was installed in Step 4. Now configure it for Application Signals:

**CDK TypeScript example:**
```typescript
instance.userData.addCommands(
  '# Create CloudWatch Agent configuration for Application Signals',
  "cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'",
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

### Step 6: Install ADOT Java Auto-Instrumentation SDK

Choose based on deployment type identified in "Before You Start".

#### Option A: Docker Deployment - Modify Dockerfile

For Docker deployments, modify the `Dockerfile` in the application directory.

Add these lines to download the ADOT Java agent JAR file. Place this AFTER any `RUN` commands that install dependencies, but BEFORE the `CMD` line:

```dockerfile
RUN curl -Lo /opt/aws-opentelemetry-agent.jar \
    https://github.com/aws-observability/aws-otel-java-instrumentation/releases/latest/download/aws-opentelemetry-agent.jar
```

**Why modify Dockerfile, not UserData:** The ADOT agent JAR must be available inside the container image, not on the EC2 host. UserData commands run on the host and won't affect the containerized application.

#### Option B: Non-Docker Deployment - Modify UserData

For non-Docker deployments, add to UserData AFTER CloudWatch Agent configuration:

```typescript
instance.userData.addCommands(
  '# Download ADOT Java agent',
  'curl -Lo /opt/aws-opentelemetry-agent.jar \\',
  '  https://github.com/aws-observability/aws-otel-java-instrumentation/releases/latest/download/aws-opentelemetry-agent.jar',
);
```

### Step 7: Modify UserData - Configure Application

Choose based on deployment type identified in "Before You Start".

#### Option A: Docker Deployment

**Critical Docker configuration:** The `--network host` flag is REQUIRED for all Docker deployments. Without it, the container cannot reach the CloudWatch Agent at `localhost:4316` because `localhost` inside a container refers to the container's network namespace, not the EC2 host.

Find the existing `docker run` command in UserData. Replace it with:

```typescript
instance.userData.addCommands(
  '# Run container with Application Signals environment variables',
  `docker run -d --name {{APP_NAME}} \\`,
  `  -p {{PORT}}:{{PORT}} \\`,
  `  -e JAVA_TOOL_OPTIONS=-javaagent:/opt/aws-opentelemetry-agent.jar \\`,
  `  -e OTEL_METRICS_EXPORTER=none \\`,
  `  -e OTEL_LOGS_EXPORTER=none \\`,
  `  -e OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true \\`,
  `  -e OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \\`,
  `  -e OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics \\`,
  `  -e OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4316/v1/traces \\`,
  `  -e OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}} \\`,
  `  --network host \\`,
  `  {{IMAGE_URI}}`,
);
```

#### Option B: Non-Docker Deployment

Find the existing command that starts the Java application. Add the environment variables BEFORE it:

```typescript
instance.userData.addCommands(
  '# Set OpenTelemetry environment variables',
  'export JAVA_TOOL_OPTIONS=-javaagent:/opt/aws-opentelemetry-agent.jar',
  'export OTEL_METRICS_EXPORTER=none',
  'export OTEL_LOGS_EXPORTER=none',
  'export OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true',
  'export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf',
  'export OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics',
  'export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4316/v1/traces',
  'export OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}}',
  '',
  '# Start application (existing command remains unchanged)',
  '# Example: java -jar app.jar',
  '# The JAVA_TOOL_OPTIONS will automatically attach the agent',
);
```

## Completion

**Tell the user:**

"I've completed the Application Signals enablement for your Java application. Here's what I modified:

**Files Changed:**
- IAM role: Added CloudWatchAgentServerPolicy
- UserData: Installed and configured CloudWatch Agent
- UserData: Downloaded ADOT Java agent JAR
- UserData/Service file: Added OpenTelemetry environment variables (`JAVA_TOOL_OPTIONS`)
- Dockerfile: Downloaded ADOT Java agent JAR (if using Docker)

**Next Steps:**
1. Review the changes I made using `git diff`
2. Deploy your infrastructure:
   - For CDK: `cdk deploy`
   - For Terraform: `terraform apply`
   - For CloudFormation: Deploy your stack
3. After deployment, wait 5-10 minutes for telemetry data to start flowing

**Verification:**
Once deployed, you can verify Application Signals is working by:
- Opening the AWS CloudWatch Console
- Navigating to Application Signals → Services
- Looking for your service (named: {{SERVICE_NAME}})
- Checking that traces and metrics are being collected

**Monitor Application Health:**
After enablement, you can monitor your application's operational health using Application Signals dashboards. For more information, see [Monitor the operational health of your applications with Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Services.html).

Let me know if you'd like me to make any adjustments before you deploy!"
