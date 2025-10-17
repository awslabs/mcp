# Enable AWS Application Signals for .NET on EC2

This guide provides instructions for modifying Infrastructure as Code (IaC) to enable Application Signals for a .NET application running on EC2. The examples use CDK TypeScript, but the concepts apply to CloudFormation and Terraform as well.

## Overview

To enable Application Signals, you need to modify the IaC to:
1. Add CloudWatchAgentServerPolicy to the EC2 instance role
2. Install and configure the CloudWatch Agent via UserData
3. Download and install ADOT .NET auto-instrumentation package via UserData
4. Configure OpenTelemetry and .NET profiler environment variables (Docker or non-Docker)

**Note:** This guide covers both Linux and Windows Server deployments, as well as Docker and non-Docker configurations.

## Prerequisites

### Linux

**IMPORTANT:** Install these system dependencies at the beginning of your UserData script, BEFORE any other Application Signals setup commands:

**Required Packages (Amazon Linux):**
```bash
yum install -y wget docker
```

**Critical:** `wget` is NOT pre-installed on Amazon Linux 2023 (though it is on AL2). Always install it explicitly.

**Installation Pattern:**
```typescript
instance.userData.addCommands(
  'yum update -y',
  'yum install -y wget docker',  // Install all dependencies first
  // ... then proceed with CloudWatch Agent installation
);
```

**Other Distributions:**
- **Ubuntu/Debian:** `apt-get install -y wget docker.io`
- **RHEL/CentOS:** `yum install -y wget docker`

### Windows Server

For Windows Server, PowerShell's `Invoke-WebRequest` is pre-installed, so no additional download tools are needed. Ensure Docker is installed if using container-based deployments.

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

### Linux

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

### Windows Server

For Windows Server instances, use PowerShell in UserData:

```typescript
const userData = ec2.UserData.forWindows();
userData.addCommands(
  '# Download and install CloudWatch Agent',
  '$agentUrl = "https://s3.amazonaws.com/amazoncloudwatch-agent/windows/amd64/latest/amazon-cloudwatch-agent.msi"',
  '$agentPath = Join-Path $env:TEMP "amazon-cloudwatch-agent.msi"',
  'Invoke-WebRequest -Uri $agentUrl -OutFile $agentPath',
  'Start-Process msiexec.exe -ArgumentList "/i $agentPath /quiet" -Wait',
  '',
  '# Create CloudWatch Agent configuration for Application Signals',
  '$configPath = "C:\\ProgramData\\Amazon\\AmazonCloudWatchAgent\\amazon-cloudwatch-agent.json"',
  '$config = @"',
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
  '"@',
  '$config | Out-File -FilePath $configPath -Encoding utf8',
  '',
  '# Start CloudWatch Agent with Application Signals configuration',
  '& "C:\\Program Files\\Amazon\\AmazonCloudWatchAgent\\amazon-cloudwatch-agent-ctl.ps1" -a fetch-config -m ec2 -s -c file:$configPath',
);
```

## Step 3: Download and Install ADOT .NET Auto-Instrumentation

### Linux

Add these commands to UserData to download and install the AWS Distro for OpenTelemetry .NET auto-instrumentation:

```typescript
instance.userData.addCommands(
  '# Download and install ADOT .NET auto-instrumentation',
  'curl -L -O https://github.com/aws-observability/aws-otel-dotnet-instrumentation/releases/latest/download/aws-otel-dotnet-install.sh',
  'chmod +x ./aws-otel-dotnet-install.sh',
  './aws-otel-dotnet-install.sh',
);
```

### Windows Server

For Windows Server instances, use the PowerShell installation script:

```typescript
userData.addCommands(
  '# Download and install ADOT .NET auto-instrumentation',
  '$moduleUrl = "https://github.com/aws-observability/aws-otel-dotnet-instrumentation/releases/latest/download/AWS.Otel.DotNet.Auto.psm1"',
  '$downloadPath = Join-Path $env:TEMP "AWS.Otel.DotNet.Auto.psm1"',
  'Invoke-WebRequest -Uri $moduleUrl -OutFile $downloadPath',
  'Import-Module $downloadPath',
  'Install-OpenTelemetryCore',
);
```

## Step 4: Configure Environment Variables and Start Application

Choose the appropriate configuration based on your OS and deployment type:

### Linux - Option A: Docker-based Deployment

If your application runs in a Docker container on Linux, mount the ADOT .NET instrumentation from the host and set environment variables via `-e` flags:

```typescript
instance.userData.addCommands(
  '# Run container with ADOT .NET instrumentation (mounted from host) and Application Signals environment variables',
  `docker run -d --name {{APP_NAME}} \\`,
  `  -p {{PORT}}:{{PORT}} \\`,
  `  -v $HOME/.otel-dotnet-auto:/otel-auto-instrumentation \\`,
  `  -e PORT={{PORT}} \\`,
  `  -e SERVICE_NAME={{SERVICE_NAME}} \\`,
  `  -e INSTALL_DIR=/otel-auto-instrumentation \\`,
  `  -e CORECLR_ENABLE_PROFILING=1 \\`,
  `  -e CORECLR_PROFILER={918728DD-259F-4A6A-AC2B-B85E1B658318} \\`,
  `  -e CORECLR_PROFILER_PATH=/otel-auto-instrumentation/linux-x64/OpenTelemetry.AutoInstrumentation.Native.so \\`,
  `  -e DOTNET_ADDITIONAL_DEPS=/otel-auto-instrumentation/AdditionalDeps \\`,
  `  -e DOTNET_SHARED_STORE=/otel-auto-instrumentation/store \\`,
  `  -e DOTNET_STARTUP_HOOKS=/otel-auto-instrumentation/net/OpenTelemetry.AutoInstrumentation.StartupHook.dll \\`,
  `  -e OTEL_DOTNET_AUTO_HOME=/otel-auto-instrumentation \\`,
  `  -e OTEL_DOTNET_AUTO_PLUGINS="AWS.Distro.OpenTelemetry.AutoInstrumentation.Plugin, AWS.Distro.OpenTelemetry.AutoInstrumentation" \\`,
  `  -e OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}} \\`,
  `  -e OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \\`,
  `  -e OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4316 \\`,
  `  -e OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics \\`,
  `  -e OTEL_METRICS_EXPORTER=none \\`,
  `  -e OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true \\`,
  `  -e OTEL_TRACES_SAMPLER=xray \\`,
  `  -e OTEL_TRACES_SAMPLER_ARG=http://localhost:2000 \\`,
  `  --network host \\`,
  `  {{IMAGE_URI}}`,
);
```

**Important for Docker:**
- Use `-v $HOME/.otel-dotnet-auto:/otel-auto-instrumentation` to mount the ADOT .NET instrumentation files from the EC2 host into the container. This is installed by the script in Step 3.
- Use `--network host` to allow the container to communicate with the CloudWatch Agent running on the EC2 host at `localhost:4316` and `localhost:2000`. Without this, the container cannot reach the agent because `localhost` inside the container refers to the container's own network namespace, not the host.

### Linux - Option B: Non-Docker Deployment

If your application runs directly on EC2 Linux (not in a container), source the instrument script and set environment variables:

```typescript
instance.userData.addCommands(
  '# Source ADOT .NET instrumentation script and set environment variables',
  '. $HOME/.otel-dotnet-auto/instrument.sh',
  'export OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}}',
  'export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf',
  'export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4316',
  'export OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics',
  'export OTEL_METRICS_EXPORTER=none',
  'export OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true',
  'export OTEL_TRACES_SAMPLER=xray',
  'export OTEL_TRACES_SAMPLER_ARG=http://localhost:2000',
  '',
  '# Start .NET application',
  'cd {{APP_DIR}}',
  'dotnet {{DLL_FILE}}',
);
```

### Windows Server - Non-Docker Deployment

If your application runs directly on Windows Server EC2 (not in a container), use the PowerShell module to register instrumentation:

```typescript
userData.addCommands(
  '# Import ADOT .NET module and register instrumentation',
  '$downloadPath = Join-Path $env:TEMP "AWS.Otel.DotNet.Auto.psm1"',
  'Import-Module $downloadPath',
  'Register-OpenTelemetryForCurrentSession -OTelServiceName "{{SERVICE_NAME}}"',
  '',
  '# Set additional Application Signals environment variables',
  '$env:OTEL_EXPORTER_OTLP_PROTOCOL = "http/protobuf"',
  '$env:OTEL_EXPORTER_OTLP_ENDPOINT = "http://127.0.0.1:4316"',
  '$env:OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT = "http://127.0.0.1:4316/v1/metrics"',
  '$env:OTEL_METRICS_EXPORTER = "none"',
  '$env:OTEL_AWS_APPLICATION_SIGNALS_ENABLED = "true"',
  '$env:OTEL_TRACES_SAMPLER = "xray"',
  '$env:OTEL_TRACES_SAMPLER_ARG = "http://127.0.0.1:2000"',
  '',
  '# Start .NET application',
  'cd {{APP_DIR}}',
  'dotnet {{DLL_FILE}}',
);
```

**Note for IIS Deployments:** If deploying to IIS on Windows Server, use `Register-OpenTelemetryForIIS` instead of `Register-OpenTelemetryForCurrentSession`.

### Windows Server - Docker-based Deployment

If your application runs in a Windows container on Windows Server, set environment variables via `-e` flags:

```typescript
userData.addCommands(
  '# Run Windows container with ADOT .NET instrumentation and Application Signals environment variables',
  `docker run -d --name {{APP_NAME}} \`,
  `  -p {{PORT}}:{{PORT}} \`,
  `  -e PORT={{PORT}} \`,
  `  -e SERVICE_NAME={{SERVICE_NAME}} \`,
  `  -e INSTALL_DIR=C:\\otel-auto-instrumentation \`,
  `  -e CORECLR_ENABLE_PROFILING=1 \`,
  `  -e CORECLR_PROFILER={918728DD-259F-4A6A-AC2B-B85E1B658318} \`,
  `  -e CORECLR_PROFILER_PATH=C:\\otel-auto-instrumentation\\win-x64\\OpenTelemetry.AutoInstrumentation.Native.dll \`,
  `  -e DOTNET_ADDITIONAL_DEPS=C:\\otel-auto-instrumentation\\AdditionalDeps \`,
  `  -e DOTNET_SHARED_STORE=C:\\otel-auto-instrumentation\\store \`,
  `  -e DOTNET_STARTUP_HOOKS=C:\\otel-auto-instrumentation\\net\\OpenTelemetry.AutoInstrumentation.StartupHook.dll \`,
  `  -e OTEL_DOTNET_AUTO_HOME=C:\\otel-auto-instrumentation \`,
  `  -e OTEL_DOTNET_AUTO_PLUGINS="AWS.Distro.OpenTelemetry.AutoInstrumentation.Plugin, AWS.Distro.OpenTelemetry.AutoInstrumentation" \`,
  `  -e OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}} \`,
  `  -e OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \`,
  `  -e OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4316 \`,
  `  -e OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://host.docker.internal:4316/v1/metrics \`,
  `  -e OTEL_METRICS_EXPORTER=none \`,
  `  -e OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true \`,
  `  -e OTEL_TRACES_SAMPLER=xray \`,
  `  -e OTEL_TRACES_SAMPLER_ARG=http://host.docker.internal:2000 \`,
  `  {{IMAGE_URI}}`,
);
```

**Important for Windows Docker:**
- The ADOT .NET instrumentation files must be included in your Windows Docker image at `C:\otel-auto-instrumentation`.
- Windows containers use `host.docker.internal` to reach the host, rather than `--network host` (which is Linux-only).

## Translation Notes for Other IaC Tools

**CloudFormation (YAML):**
- IAM role: Add `CloudWatchAgentServerPolicy` to `ManagedPolicyArns`
- UserData: Add commands to `AWS::EC2::Instance` `UserData` property using `Fn::Base64` and `Fn::Sub`
- For Windows: Use `<powershell>` tags in UserData

**Terraform:**
- IAM role: Add `arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy` to `aws_iam_role_policy_attachment`
- UserData: Add commands to `aws_instance` `user_data` property
- For Windows: Ensure UserData uses PowerShell syntax

## Placeholders

The following placeholders should be replaced with actual values from the customer's environment:

**Common (all deployments):**
- `{{SERVICE_NAME}}`: The service name for Application Signals (e.g., `my-dotnet-app`)

**Linux non-Docker only:**
- `{{APP_DIR}}`: The directory containing the application code (e.g., `/opt/myapp`)
- `{{DLL_FILE}}`: The .NET application DLL file (e.g., `MyApp.dll`)

**Windows non-Docker only:**
- `{{APP_DIR}}`: The directory containing the application code (e.g., `C:\myapp`)
- `{{DLL_FILE}}`: The .NET application DLL file (e.g., `MyApp.dll`)

**Docker only (Linux and Windows):**
- `{{APP_NAME}}`: The container name (e.g., `dotnet-aspnetcore`)
- `{{PORT}}`: The application port (e.g., `8080`)
- `{{IMAGE_URI}}`: The Docker image URI

## Important: User Review and Deployment

After modifying the IaC files, the user should:
1. Review all changes to ensure they are correct
2. For Docker deployments, ensure the ADOT .NET instrumentation is installed in the Docker image
3. Deploy the updated infrastructure using their standard deployment process (e.g., `cdk deploy`)
4. Verify Application Signals data appears in the CloudWatch console after deployment
