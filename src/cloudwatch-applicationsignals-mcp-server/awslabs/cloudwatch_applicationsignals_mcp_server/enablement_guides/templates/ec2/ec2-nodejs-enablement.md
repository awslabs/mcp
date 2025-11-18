# Task: Enable AWS Application Signals for Node.js on EC2

Your task is to modify Infrastructure as Code (IaC) files to enable AWS Application Signals for a Node.js application running on EC2 instances. You will update IAM permissions, install monitoring agents, and configure OpenTelemetry instrumentation through UserData scripts.

## What You Will Accomplish

After completing this task:
- The EC2 instance will have permissions to send telemetry data to CloudWatch
- The CloudWatch Agent will be installed and configured for Application Signals
- The Node.js application will be automatically instrumented with AWS Distro for OpenTelemetry (ADOT)
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
- `node`, `npm start`, `yarn start`, or similar → Non-Docker deployment

**If unclear:**
- Ask the user: "Is your Node.js application running in a Docker container or directly on the EC2 instance?" DO NOT GUESS

**Critical distinction:** Where does the Node.js process run?
- **Docker:** Node.js runs inside a container → Modify Dockerfile
- **Non-Docker:** Node.js runs directly on EC2 → Modify UserData

### Step 2: Extract Placeholder Values

Analyze the existing IaC to determine these values for Application Signals enablement:

- `{{SERVICE_NAME}}`
    - **Why It Matters:** Sets the service name displayed in Application Signals console via `OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}}`
    - **How to Find It:** Use the application name, stack name, or construct ID. Look for service/app names in the IaC.
    - **Example Value:** `my-nodejs-app`
    - **Required For:** Both Docker and non-Docker
- `{{ENTRY_POINT}}`
    - **Why It Matters:** Used to start the application with OpenTelemetry instrumentation: `node --require ... {{ENTRY_POINT}}`
    - **How to Find It:** Find the JavaScript file that starts the application (look for `node` commands in UserData)
    - **Example Value:** `server.js`, `index.js`, or `app.js`
    - **Required For:** Non-Docker
- `{{APP_DIR}}`
    - **Why It Matters:** Node.js needs to run from the correct directory to find application files and dependencies
    - **How to Find It:** Find where the application code is deployed (look for `cd`, `git clone`, or file copy commands in UserData)
    - **Example Value:** `/opt/myapp`
    - **Required For:** Non-Docker

For Docker-based deployments you will also need to find these additional values:

- `{{PORT}}`
    - **Why It Matters:** Docker port mapping that ensures the container is accessible on the correct port
    - **How to Find It:** Find port mappings in `docker run -p` commands or security group ingress rules
    - **Example Value:** `3000`
    - **Required For:** Docker
- `{{APP_NAME}}`
    - **Why It Matters:** Used to reference the container for operations like `docker logs {{APP_NAME}}`, `docker exec`, health checks, etc.
    - **How to Find It:** Find container name in `docker run --name` or use `{{SERVICE_NAME}}-container`
    - **Example Value:** `nodejs-express-app`
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

### Step 4: Determine Module Format

Determine if the Node.js application uses CommonJS or ESM module format. This affects which ADOT dependencies to install and which node flags to use.

**Check the application's package.json file:**

- Look for `"type": "module"` → **ESM format**
- Look for `"type": "commonjs"` or no type field → **CommonJS format** (default)

**Alternative checks:**

- If the main application file has `.mjs` extension → **ESM format**
- If the main application file has `.cjs` extension → **CommonJS format**
- If `.js` extension → Depends on package.json type field

**If unclear:**
- Ask the user: "Does your Node.js application use ESM module format (type: module in package.json)?" DO NOT GUESS
- Default to CommonJS if package.json doesn't specify type

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

### Step 6: Install ADOT Node.js Auto-Instrumentation SDK

Choose based on deployment type AND module format identified in "Before You Start".

#### Option A: Docker Deployment - Modify Dockerfile

For Docker deployments, modify the `Dockerfile` in the application directory.

Add the ADOT Node.js SDK installation AFTER any existing `npm install` or dependency installation commands:

**For CommonJS applications:**
```dockerfile
# Install ADOT Node.js auto-instrumentation
RUN npm install @aws/aws-distro-opentelemetry-node-autoinstrumentation
```

**For ESM applications:**
```dockerfile
# Install ADOT Node.js auto-instrumentation with ESM support
RUN npm install @aws/aws-distro-opentelemetry-node-autoinstrumentation @opentelemetry/instrumentation@0.54.0
```

**Why modify Dockerfile, not UserData:** The ADOT package must be installed inside the container image, not on the EC2 host. UserData commands run on the host and won't affect the containerized application.

#### Option B: Non-Docker Deployment - Modify UserData

For non-Docker deployments, add to UserData AFTER CloudWatch Agent configuration:

**For CommonJS applications:**
```typescript
instance.userData.addCommands(
  '# Install ADOT Node.js auto-instrumentation',
  'npm install @aws/aws-distro-opentelemetry-node-autoinstrumentation',
);
```

**For ESM applications:**
```typescript
instance.userData.addCommands(
  '# Install ADOT Node.js auto-instrumentation with ESM support',
  'npm install @aws/aws-distro-opentelemetry-node-autoinstrumentation @opentelemetry/instrumentation@0.54.0',
);
```

### Step 7: Modify Application Startup to Load ADOT Agent

Choose based on deployment type AND module format identified in "Before You Start".

#### Option A: Docker Deployment

For Docker deployments, you need to modify both the Dockerfile CMD and the UserData docker run command.

**1. Modify Dockerfile CMD to load ADOT agent:**

Find the `CMD` line in your Dockerfile and modify it based on module format:

**For CommonJS applications:**
```dockerfile
# Before:
CMD ["node", "app.js"]

# After:
CMD ["node", "--require", "@aws/aws-distro-opentelemetry-node-autoinstrumentation/register", "app.js"]
```

**For ESM applications:**
```dockerfile
# Before:
CMD ["node", "app.js"]

# After:
CMD ["node", "--import", "@aws/aws-distro-opentelemetry-node-autoinstrumentation/register", "--experimental-loader=@opentelemetry/instrumentation/hook.mjs", "app.js"]
```

**2. Add environment variables to docker run command in UserData:**

**Critical Docker configuration:** The `--network host` flag is REQUIRED for all Docker deployments. Without it, the container cannot reach the CloudWatch Agent at `localhost:4316` because `localhost` inside a container refers to the container's network namespace, not the EC2 host.

Find the existing `docker run` command in UserData. Replace it with:

```typescript
instance.userData.addCommands(
  '# Run container with Application Signals environment variables',
  `docker run -d --name {{APP_NAME}} \\`,
  `  -p {{PORT}}:{{PORT}} \\`,
  `  -e OTEL_METRICS_EXPORTER=none \\`,
  `  -e OTEL_LOGS_EXPORTER=none \\`,
  `  -e OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true \\`,
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

#### Option B: Non-Docker Deployment

For non-Docker deployments, set environment variables and modify the node startup command based on module format.

Find the existing command that starts the Node.js application. Add the environment variables BEFORE it and modify the startup command:

**For CommonJS applications:**
```typescript
instance.userData.addCommands(
  '# Set OpenTelemetry environment variables',
  'export OTEL_METRICS_EXPORTER=none',
  'export OTEL_LOGS_EXPORTER=none',
  'export OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true',
  'export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf',
  'export OTEL_TRACES_SAMPLER=xray',
  'export OTEL_TRACES_SAMPLER_ARG=endpoint=http://localhost:2000',
  'export OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics',
  'export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4316/v1/traces',
  'export OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}}',
  '',
  '# Start application with ADOT agent',
  'cd {{APP_DIR}}',
  'node --require "@aws/aws-distro-opentelemetry-node-autoinstrumentation/register" {{ENTRY_POINT}}',
);
```

**For ESM applications:**
```typescript
instance.userData.addCommands(
  '# Set OpenTelemetry environment variables',
  'export OTEL_METRICS_EXPORTER=none',
  'export OTEL_LOGS_EXPORTER=none',
  'export OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true',
  'export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf',
  'export OTEL_TRACES_SAMPLER=xray',
  'export OTEL_TRACES_SAMPLER_ARG=endpoint=http://localhost:2000',
  'export OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics',
  'export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4316/v1/traces',
  'export OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}}',
  '',
  '# Start application with ADOT agent (ESM)',
  'cd {{APP_DIR}}',
  'node --import "@aws/aws-distro-opentelemetry-node-autoinstrumentation/register" \\',
  '  --experimental-loader=@opentelemetry/instrumentation/hook.mjs \\',
  '  {{ENTRY_POINT}}',
);
```

**Note for systemd services:** If the application uses systemd (look for `.service` files or `systemctl` commands in UserData), translate the `export` statements to `Environment=` directives in the service file, set `WorkingDirectory={{APP_DIR}}`, and update `ExecStart=` to use the appropriate node flags. After modifying the service file, add `systemctl daemon-reload` and `systemctl restart <service>` to UserData

## Completion

**Tell the user:**

"I've completed the Application Signals enablement for your Node.js application. Here's what I modified:

**Files Changed:**
- IAM role: Added CloudWatchAgentServerPolicy
- UserData: Installed and configured CloudWatch Agent
- UserData: Installed ADOT Node.js SDK
- UserData/Service file: Added OpenTelemetry environment variables and node startup flags
- Dockerfile: Installed ADOT Node.js SDK and modified CMD with node flags (if using Docker)

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
