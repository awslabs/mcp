# Task: Enable AWS Application Signals for .NET on EC2

Your task is to modify Infrastructure as Code (IaC) files to enable AWS Application Signals for a .NET application running on EC2 instances. You will update IAM permissions, install monitoring agents, and configure OpenTelemetry instrumentation through UserData scripts.

## What You Will Accomplish

After completing this task:
- The EC2 instance will have permissions to send telemetry data to CloudWatch
- The CloudWatch Agent will be installed and configured for Application Signals
- The .NET application will be automatically instrumented with AWS Distro for OpenTelemetry (ADOT)
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
- `dotnet run`, `dotnet myapp.dll`, or similar → Non-Docker deployment

**If unclear:**
- Ask the user: "Is your .NET application running in a Docker container or directly on the EC2 instance?" DO NOT GUESS

**Critical distinction:** Where does the .NET process run?
- **Docker:** .NET runs inside a container → Modify Dockerfile
- **Non-Docker:** .NET runs directly on EC2 → Modify UserData

### Step 2: Extract Placeholder Values

Analyze the existing IaC to determine these values for Application Signals enablement:

- `{{SERVICE_NAME}}`
    - **Why It Matters:** Sets the service name displayed in Application Signals console via `OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}}`
    - **How to Find It:** Use the application name, stack name, or construct ID. Look for service/app names in the IaC.
    - **Example Value:** `my-dotnet-app`
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
    - **Example Value:** `dotnet-api-app`
    - **Required For:** Docker
- `{{IMAGE_URI}}`
    - **Why It Matters:** This is the identifier for the application that Docker will run
    - **How to Find It:** Find the Docker image in `docker run` or `docker pull` commands
    - **Example Value:** `123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest`
    - **Required For:** Docker

**If you cannot determine a value:** Ask the user for clarification before proceeding. Do not guess or make up values.

### Step 3: Identify Instance OS

Determine the operating system to use the correct installation commands.

**Linux:**
- **Amazon Linux 2:** Use `yum` package manager
- **Amazon Linux 2023:** Use `dnf` package manager
- **Ubuntu/Debian:** Use `apt` package manager
- **How to detect:** Look for existing package install commands in UserData (check for `yum`, `dnf`, or `apt`), or look for AMI references containing `al2`, `al2023`, `ubuntu`, etc.

**Windows Server:**
- **Not supported yet.** If the customer is using Windows Server-based EC2 instances, inform them that automated enablement is not available yet. Provide them with this link to enable Application Signals manually: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable-EC2Main.html

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

**For Linux instances:**

**CDK TypeScript example:**
```typescript
instance.userData.addCommands(
  'dnf install -y amazon-cloudwatch-agent',  // Use dnf for AL2023, yum for AL2, apt-get for Ubuntu
  // ... rest of UserData follows
);
```

**Placement:** Add this command early in the UserData script:
- If system update commands exist (like `dnf update -y`, `apt-get update`), add it immediately after those
- If no system update commands exist, add it at the very beginning of UserData
- This should come before any application dependency installations or application setup commands

**For Windows instances:**

**CDK TypeScript example:**
```typescript
instance.userData.addCommands(
  '# Download and install CloudWatch Agent',
  'Invoke-WebRequest -Uri "https://amazoncloudwatch-agent.s3.amazonaws.com/windows/amd64/latest/amazon-cloudwatch-agent.msi" -OutFile "C:\\amazon-cloudwatch-agent.msi"',
  'Start-Process msiexec.exe -Wait -ArgumentList "/i C:\\amazon-cloudwatch-agent.msi /quiet"',
  'Remove-Item "C:\\amazon-cloudwatch-agent.msi"',
  // ... rest of UserData follows
);
```

**Placement:** Add these commands early in the UserData script, before any application setup commands.

**For other Linux distributions:** CloudWatch Agent may not be available via the OS package manager. Refer to [AWS CloudWatch Agent installation docs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/manual-installation.html) for distribution-specific instructions.

### Step 5: Modify UserData - Configure CloudWatch Agent

The CloudWatch Agent was installed in Step 4. Now configure it for Application Signals:

**For Linux instances:**

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

**For Windows instances:**

**CDK TypeScript example:**
```typescript
instance.userData.addCommands(
  '# Create CloudWatch Agent configuration for Application Signals',
  '@"',
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
  '"@ | Out-File -FilePath "C:\\ProgramData\\Amazon\\AmazonCloudWatchAgent\\amazon-cloudwatch-agent.json" -Encoding ASCII',
  '',
  '# Start CloudWatch Agent with Application Signals configuration',
  '& "C:\\Program Files\\Amazon\\AmazonCloudWatchAgent\\amazon-cloudwatch-agent-ctl.ps1" -a fetch-config -m ec2 -s -c file:"C:\\ProgramData\\Amazon\\AmazonCloudWatchAgent\\amazon-cloudwatch-agent.json"',
);
```

### Step 6: Install ADOT .NET Auto-Instrumentation

Choose based on deployment type and OS identified in "Before You Start".

#### Option A: Docker Deployment - Modify Dockerfile

For Docker deployments, modify the `Dockerfile` in the application directory.

**For Linux-based containers:**

Add these lines to install the ADOT .NET auto-instrumentation. Place this AFTER any `RUN` commands that install dependencies, but BEFORE the `CMD` line:

```dockerfile
# Install unzip (required by ADOT installation script)
# Use the appropriate package manager for your base image:
# - For Amazon Linux 2: RUN yum install -y unzip
# - For Amazon Linux 2023: RUN dnf install -y unzip
# - For Ubuntu/Debian: RUN apt-get update && apt-get install -y unzip
RUN dnf install -y unzip  # Adjust package manager as needed

# Download and install ADOT .NET auto-instrumentation to /opt (accessible by all users)
RUN curl -L -O https://github.com/aws-observability/aws-otel-dotnet-instrumentation/releases/latest/download/aws-otel-dotnet-install.sh \
    && chmod +x ./aws-otel-dotnet-install.sh \
    && OTEL_DOTNET_AUTO_HOME="/opt/otel-dotnet-auto" ./aws-otel-dotnet-install.sh \
    && chmod -R 755 /opt/otel-dotnet-auto
```

**Why modify Dockerfile, not UserData:** The ADOT instrumentation must be available inside the container image, not on the EC2 host. UserData commands run on the host and won't affect the containerized application.

#### Option B: Non-Docker Deployment - Modify UserData

**For Linux instances:**

For non-Docker deployments, add to UserData AFTER CloudWatch Agent configuration:

```typescript
instance.userData.addCommands(
  '# Install unzip (required by ADOT installation script)',
  'dnf install -y unzip',  // Use dnf for AL2023, yum for AL2, apt-get for Ubuntu
  '',
  '# Download and install ADOT .NET auto-instrumentation to /opt',
  'curl -L -O https://github.com/aws-observability/aws-otel-dotnet-instrumentation/releases/latest/download/aws-otel-dotnet-install.sh',
  'chmod +x ./aws-otel-dotnet-install.sh',
  'OTEL_DOTNET_AUTO_HOME="/opt/otel-dotnet-auto" ./aws-otel-dotnet-install.sh',
  'chmod -R 755 /opt/otel-dotnet-auto',
);
```

**For Windows instances:**

For non-Docker deployments, add to UserData AFTER CloudWatch Agent configuration:

```typescript
instance.userData.addCommands(
  '# Download and install ADOT .NET auto-instrumentation',
  '$module_url = "https://github.com/aws-observability/aws-otel-dotnet-instrumentation/releases/latest/download/AWS.Otel.DotNet.Auto.psm1"',
  '$download_path = Join-Path $env:temp "AWS.Otel.DotNet.Auto.psm1"',
  'Invoke-WebRequest -Uri $module_url -OutFile $download_path',
  'Import-Module $download_path',
  'Install-OpenTelemetryCore',
);
```

### Step 7: Modify UserData - Configure Application

Choose based on deployment type and OS identified in "Before You Start".

#### Option A: Docker Deployment

**Critical Docker configuration:** The `--network host` flag is REQUIRED for all Docker deployments on Linux. Without it, the container cannot reach the CloudWatch Agent at `localhost:4316` because `localhost` inside a container refers to the container's network namespace, not the EC2 host.

**For Linux-based containers:**

Find the existing `docker run` command in UserData. Replace it with:

```typescript
instance.userData.addCommands(
  '# Run container with Application Signals environment variables',
  `docker run -d --name {{APP_NAME}} \\`,
  `  -p {{PORT}}:{{PORT}} \\`,
  `  -e OTEL_DOTNET_AUTO_HOME=/opt/otel-dotnet-auto \\`,
  `  -e DOTNET_STARTUP_HOOKS=/opt/otel-dotnet-auto/net/OpenTelemetry.AutoInstrumentation.StartupHook.dll \\`,
  `  -e DOTNET_SHARED_STORE=/opt/otel-dotnet-auto/store \\`,
  `  -e DOTNET_ADDITIONAL_DEPS=/opt/otel-dotnet-auto/AdditionalDeps \\`,
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

Find the existing command that starts the .NET application. Add the environment variables BEFORE it:

**For Linux instances:**

```typescript
instance.userData.addCommands(
  '# Set OpenTelemetry environment variables',
  '. /opt/otel-dotnet-auto/instrument.sh',
  'export OTEL_METRICS_EXPORTER=none',
  'export OTEL_LOGS_EXPORTER=none',
  'export OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true',
  'export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf',
  'export OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics',
  'export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4316/v1/traces',
  'export OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}}',
  '',
  '# Start application (existing command remains unchanged)',
  '# Example: dotnet run --urls http://0.0.0.0:8080',
  '# The OTEL environment variables will automatically enable instrumentation',
);
```

**For Windows instances:**

```typescript
instance.userData.addCommands(
  '# Set OpenTelemetry environment variables at machine level',
  '$env:INSTALL_DIR = "C:\\Program Files\\AWS Distro for OpenTelemetry AutoInstrumentation"',
  '[Environment]::SetEnvironmentVariable("CORECLR_ENABLE_PROFILING", "1", "Machine")',
  '[Environment]::SetEnvironmentVariable("CORECLR_PROFILER", "{918728DD-259F-4A6A-AC2B-B85E1B658318}", "Machine")',
  '[Environment]::SetEnvironmentVariable("CORECLR_PROFILER_PATH_64", (Join-Path $env:INSTALL_DIR "win-x64/OpenTelemetry.AutoInstrumentation.Native.dll"), "Machine")',
  '[Environment]::SetEnvironmentVariable("CORECLR_PROFILER_PATH_32", (Join-Path $env:INSTALL_DIR "win-x86/OpenTelemetry.AutoInstrumentation.Native.dll"), "Machine")',
  '[Environment]::SetEnvironmentVariable("COR_ENABLE_PROFILING", "1", "Machine")',
  '[Environment]::SetEnvironmentVariable("COR_PROFILER", "{918728DD-259F-4A6A-AC2B-B85E1B658318}", "Machine")',
  '[Environment]::SetEnvironmentVariable("COR_PROFILER_PATH_64", (Join-Path $env:INSTALL_DIR "win-x64/OpenTelemetry.AutoInstrumentation.Native.dll"), "Machine")',
  '[Environment]::SetEnvironmentVariable("COR_PROFILER_PATH_32", (Join-Path $env:INSTALL_DIR "win-x86/OpenTelemetry.AutoInstrumentation.Native.dll"), "Machine")',
  '[Environment]::SetEnvironmentVariable("DOTNET_ADDITIONAL_DEPS", (Join-Path $env:INSTALL_DIR "AdditionalDeps"), "Machine")',
  '[Environment]::SetEnvironmentVariable("DOTNET_SHARED_STORE", (Join-Path $env:INSTALL_DIR "store"), "Machine")',
  '[Environment]::SetEnvironmentVariable("DOTNET_STARTUP_HOOKS", (Join-Path $env:INSTALL_DIR "net/OpenTelemetry.AutoInstrumentation.StartupHook.dll"), "Machine")',
  '[Environment]::SetEnvironmentVariable("OTEL_DOTNET_AUTO_HOME", $env:INSTALL_DIR, "Machine")',
  '[Environment]::SetEnvironmentVariable("OTEL_DOTNET_AUTO_PLUGINS", "AWS.Distro.OpenTelemetry.AutoInstrumentation.Plugin, AWS.Distro.OpenTelemetry.AutoInstrumentation", "Machine")',
  '[Environment]::SetEnvironmentVariable("OTEL_RESOURCE_ATTRIBUTES", "service.name={{SERVICE_NAME}}", "Machine")',
  '[Environment]::SetEnvironmentVariable("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf", "Machine")',
  '[Environment]::SetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4316", "Machine")',
  '[Environment]::SetEnvironmentVariable("OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT", "http://127.0.0.1:4316/v1/metrics", "Machine")',
  '[Environment]::SetEnvironmentVariable("OTEL_METRICS_EXPORTER", "none", "Machine")',
  '[Environment]::SetEnvironmentVariable("OTEL_AWS_APPLICATION_SIGNALS_ENABLED", "true", "Machine")',
  '[Environment]::SetEnvironmentVariable("OTEL_TRACES_SAMPLER", "xray", "Machine")',
  '[Environment]::SetEnvironmentVariable("OTEL_TRACES_SAMPLER_ARG", "http://127.0.0.1:2000", "Machine")',
  '# The command below is optional. It registers Application signals in IIS after starting the IIS/W3SVC service and starting the WebAppPool if they exist',
  'Register-OpenTelemetryForIIS',
);
```

## Completion

**Tell the user:**

"I've completed the Application Signals enablement for your .NET application. Here's what I modified:

**Files Changed:**
- IAM role: Added CloudWatchAgentServerPolicy
- UserData: Installed and configured CloudWatch Agent
- UserData: Downloaded and installed ADOT .NET auto-instrumentation
- UserData/Dockerfile: Added OpenTelemetry environment variables
- Dockerfile: Installed ADOT .NET auto-instrumentation (if using Docker)

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
