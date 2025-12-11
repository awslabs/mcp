# Task: Enable AWS Application Signals for Python on EC2

Your task is to modify Infrastructure as Code (IaC) files to enable AWS Application Signals for a Python application running on EC2 instances. You will update IAM permissions, install monitoring agents, and configure OpenTelemetry instrumentation through UserData scripts.

## What You Will Accomplish

After completing this task:
- The EC2 instance will have permissions to send telemetry data to CloudWatch
- The CloudWatch Agent will be installed and configured for Application Signals
- The Python application will be automatically instrumented with AWS Distro for OpenTelemetry (ADOT)
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

**Code examples use CDK TypeScript syntax**. If you are working with Terraform or CloudFormation, translate the CDK syntax to the appropriate format while keeping all bash commands identical. The UserData bash commands (CloudWatch Agent installation, ADOT installation, environment variables) are universal across all IaC tools - only the wrapper syntax differs.

## Before You Start: Gather Required Information

Execute these steps to collect the information needed for configuration:

### Step 1: Determine Deployment Type

Read the UserData script and look for the application startup command. This is typically one of the last commands in UserData.

**If you see:**
- `docker run` or `docker start` → **Docker deployment**
- `python`, `gunicorn`, `uvicorn`, `flask run`, or similar → **Non-Docker deployment**

**If unclear:**
- Ask the user: "Is your Python application running in a Docker container or directly on the EC2 instance?" DO NOT GUESS

**Critical distinction:** Where does the Python process run?
- **Docker:** Python runs inside a container → Modify Dockerfile
- **Non-Docker:** Python runs directly on EC2 → Modify UserData

### Step 2: Extract Placeholder Values

Analyze the existing IaC to determine these values for Application Signals enablement:

- `{{SERVICE_NAME}}`:
    - **Why It Matters:** Sets the service name displayed in Application Signals console via `OTEL_RESOURCE_ATTRIBUTES=service.name={{SERVICE_NAME}}`
    - **How to Find It:** Use the application name, stack name, or construct ID. Look for service/app names in the IaC.
    - **Example Value:** `my-python-app`
    - **Required For:** Both Docker and non-Docker
- `{{ENTRY_POINT}}`
    - **Why It Matters:** Used to wrap the application startup with OpenTelemetry instrumentation: `opentelemetry-instrument python {{ENTRY_POINT}}`
    - **How to Find It:** Find the Python file that starts the application (look for `python` commands in UserData)
    - **Example Value:** `app.py` or `main.py`
    - **Required For:** non-Docker
- `{{APP_DIR}}`
    - **Why It Matters:** Python needs to run from the correct directory to find application files and dependencies
    - **How to Find It:** Find where the application code is deployed (look for `cd`, `git clone`, or file copy commands in UserData)
    - **Example Value:** `/opt/myapp`
    - **Required For:** non-Docker


For Docker-based deployments you will also need to find these additional values:

- `{{PORT}}`
    - **Why It Matters:** Docker port mapping that ensures the container is accessible on the correct port
    - **How to Find It:** Find port mappings in `docker run -p` commands or security group ingress rules
    - **Example Value:** `5000`
    - **Required For:** Docker
- `{{APP_NAME}}`
    - **Why It Matters:** Used to reference the container for operations like `docker logs {{APP_NAME}}`, `docker exec`, health checks, etc.
    - **How to Find It:** Find container name in `docker run --name` or use `{{SERVICE_NAME}}-container`
    - **Example Value:** `python-flask-app`
    - **Required For:** Docker
- `{{IMAGE_URI}}`
    - **Why It Matters:** This is the identifier for the application that Docker will run
    - **How to Find It:** Find the Docker image in `docker run` or `docker pull` commands
    - **Example Value:** `123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest`
    - **Required For:** Docker

**If you cannot determine a value:** Ask the user for clarification before proceeding. Do not guess or make up values.

### Step 3: Identify Python Framework

Search the IaC UserData and application files for framework indicators:

- **Django:** `django`, `manage.py`, `DJANGO_SETTINGS_MODULE`, `settings.py`
- **Flask:** `flask`, `Flask(`, `@app.route`
- **FastAPI:** `fastapi`, `FastAPI(`, `uvicorn`
- **WSGI Server:** `gunicorn`, `uwsgi` in startup commands or `requirements.txt`
- **Other:** Generic Python application

**If you cannot determine a value:** Ask the user for clarification before proceeding. Do not guess or make up values.

### Step 4: Framework-Specific Requirements

Only complete the relevant subsections based on what you identified in Step 3.

#### 4a. Django Applications

If you identified Django in Step 3, extract the Django settings module path:

- `{{DJANGO_SETTINGS_MODULE}}`: The Python module path to `settings.py`
    - **How to Find:** Look for existing `DJANGO_SETTINGS_MODULE` in UserData/Dockerfile, or search for `settings.py` location
    - **Common Patterns:** `myproject.settings` (if `settings.py` at `myproject/settings.py`)
    - **If not found:** Ask the user for the Django settings module path

#### 4b. WSGI Server Applications (Gunicorn/uWSGI)

If you identified a WSGI server in Step 3, note that additional worker instrumentation is required:

- Gunicorn requires a `post_fork` hook in `gunicorn.conf.py`
- uWSGI requires `import` directive in `uwsgi.ini`
- Both require `OTEL_AWS_PYTHON_DEFER_TO_WORKERS_ENABLED=true` environment variable
- Implementation details are covered in the Docker/non-Docker configuration sections below

### Step 5: Identify Instance OS

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

Find the IAM role attached to the EC2 instance.

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

### Step 6: Install ADOT Python Auto-Instrumentation SDK

Choose based on deployment type identified in "Before You Start".

#### Option A: Docker Deployment - Modify Dockerfile

For Docker deployments, modify the `Dockerfile` in the application directory.

**1. Install aws-opentelemetry-distro:**

Find the line that installs Python dependencies (usually `RUN pip install ` or `RUN pip install -r requirements.txt`). Add ADOT installation AFTER it:

```dockerfile
# Add this line after the existing pip install command
RUN pip install --no-cache-dir aws-opentelemetry-distro
```

**2. Wrap the CMD with opentelemetry-instrument:**

Find the `CMD` line at the end of the `Dockerfile` and wrap the command with `opentelemetry-instrument`:

```dockerfile
# Before (Flask):
CMD ["flask", "run"]

# After:
CMD ["opentelemetry-instrument", "flask", "run"]

# Before (any Python app):
CMD ["python", "app.py"]

# After:
CMD ["opentelemetry-instrument", "python", "app.py"]
```

**Django-specific examples:**

For Django with Gunicorn (production):
```dockerfile
# Before:
CMD ["gunicorn", "-c", "gunicorn.conf.py", "djangoapp.wsgi:application"]

# After:
CMD ["opentelemetry-instrument", "gunicorn", "-c", "gunicorn.conf.py", "djangoapp.wsgi:application"]
```

For Django development server, add the `--noreload` flag to prevent auto-reloader conflicts with OpenTelemetry:
```dockerfile
# Before:
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# After:
CMD ["opentelemetry-instrument", "python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload"]
```

**Why modify Dockerfile, not UserData:** The ADOT package must be installed inside the container image, not on the EC2 host. UserData commands run on the host and won't affect the containerized application.

#### Option B: Non-Docker Deployment - Modify UserData

For non-Docker deployments, add to UserData AFTER CloudWatch Agent installation:

```typescript
instance.userData.addCommands(
  '# Install ADOT Python auto-instrumentation',
  'pip3 install aws-opentelemetry-distro',
);
```

### Step 7: Modify UserData - Configure Application (Docker Deployment)

**Only follow this step if you identified Docker deployment in "Before You Start".**

**Critical Docker configuration:** The `--network host` flag is REQUIRED for all Docker deployments. Without it, the container cannot reach the CloudWatch Agent at `localhost:4316` because `localhost` inside a container refers to the container's network namespace, not the EC2 host.

#### Step 7A: Base Framework Configuration

Choose the appropriate option based on the framework you identified in Step 3.

##### Option 1: Standard Python (Flask, FastAPI, Other)

**Use this for Flask, FastAPI, or other Python frameworks NOT using Django.**

Find the existing `docker run` command in UserData. Replace it with:

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

##### Option 2: Django Applications

**Use this if you identified Django in Step 3.**

Find the existing `docker run` command in UserData. Replace it with:

```typescript
instance.userData.addCommands(
  `docker run -d --name {{APP_NAME}} \\`,
  `  -p {{PORT}}:{{PORT}} \\`,
  `  -e PORT={{PORT}} \\`,
  `  -e SERVICE_NAME={{SERVICE_NAME}} \\`,
  `  -e DJANGO_SETTINGS_MODULE={{DJANGO_SETTINGS_MODULE}} \\`,
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

#### Step 7B: WSGI Additional Configuration

**Only complete this section if you identified a WSGI server (Gunicorn/uWSGI) in Step 3.**

If you are using a WSGI server, you must add additional worker instrumentation on top of the configuration from Step 7A.

**1. Ensure WSGI configuration file is in the Docker image.**

Your `Dockerfile` must include the appropriate configuration file:

For **Gunicorn** - Create `gunicorn.conf.py`:

```python
def post_fork(server, worker):
    from opentelemetry.instrumentation.auto_instrumentation import sitecustomize
```

For **uWSGI** - Create or modify `uwsgi.ini`:
```ini
[uwsgi]
enable-threads = true
lazy-apps = true
import = opentelemetry.instrumentation.auto_instrumentation.sitecustomize
```

**2. Add WSGI-specific environment variable to your docker run command.**

Go back to the `docker run` command you configured in Step 7A and add this environment variable:

```typescript
`  -e OTEL_AWS_PYTHON_DEFER_TO_WORKERS_ENABLED=true \\`,
```

Add it right after the `OTEL_RESOURCE_ATTRIBUTES` line and before `--network host`.

**WSGI requirements:**
- `OTEL_AWS_PYTHON_DEFER_TO_WORKERS_ENABLED=true` is REQUIRED for all WSGI servers
- The `gunicorn.conf.py` or `uwsgi.ini` file with worker instrumentation is REQUIRED

### Step 8: Modify UserData - Configure Application (Non-Docker Deployment)

**Only follow this step if you identified non-Docker deployment in "Before You Start".**

#### Step 8A: Base Framework Configuration

Choose the appropriate option based on the framework you identified in Step 3.

##### Option 1: Standard Python (Flask, FastAPI, Other)

**Use this for Flask, FastAPI, or other Python frameworks NOT using Django.**

Find the existing command that starts the Python application. Replace it with:

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

##### Option 2: Django Applications

**Use this if you identified Django in Step 3.**

Find the existing command that starts the Django application. Replace it with:

```typescript
instance.userData.addCommands(
  'export DJANGO_SETTINGS_MODULE={{DJANGO_SETTINGS_MODULE}}',
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
  '# Start Django application with ADOT instrumentation',
  'cd {{APP_DIR}}',
  'opentelemetry-instrument python manage.py runserver 0.0.0.0:{{PORT}} --noreload',
);
```

**Django-specific notes:**
- `--noreload` flag is REQUIRED to prevent auto-reloader conflicts with OpenTelemetry

#### Step 8B: WSGI Additional Configuration

**Only complete this section if you identified a WSGI server (Gunicorn/uWSGI) in Step 3.**

If you are using a WSGI server, you must add additional worker instrumentation on top of the configuration from Step 8A.

**1. Ensure WSGI configuration file exists on the EC2 instance.**

Your application directory must include the appropriate configuration file:

For **Gunicorn** - Create `gunicorn.conf.py`:

```python
def post_fork(server, worker):
    from opentelemetry.instrumentation.auto_instrumentation import sitecustomize
```

For **uWSGI** - Create or modify `uwsgi.ini`:
```ini
[uwsgi]
enable-threads = true
lazy-apps = true
import = opentelemetry.instrumentation.auto_instrumentation.sitecustomize
```

**2. Add WSGI-specific environment variable to your configuration.**

Go back to the commands you configured in Step 8A and add this environment variable:

```typescript
'export OTEL_AWS_PYTHON_DEFER_TO_WORKERS_ENABLED=true',
```

Add it right after the `export OTEL_RESOURCE_ATTRIBUTES` line.

**3. Update the application startup command.**

Replace the application startup command with the WSGI server command wrapped with OpenTelemetry instrumentation.

**General examples (Flask, FastAPI, etc.):**
```typescript
// Flask with Gunicorn
'opentelemetry-instrument gunicorn -c gunicorn.conf.py app:app',

// Generic Python app with uWSGI
'opentelemetry-instrument uwsgi --ini uwsgi.ini',
```

**Django-specific examples:**

For Django with Gunicorn:
```typescript
// The cd command is from Step 8A, this replaces the startup command
'opentelemetry-instrument gunicorn -c gunicorn.conf.py myproject.wsgi:application',
```

For Django with uWSGI:
```typescript
'opentelemetry-instrument uwsgi --ini uwsgi.ini --module myproject.wsgi:application',
```

**WSGI requirements:**
- `OTEL_AWS_PYTHON_DEFER_TO_WORKERS_ENABLED=true` is REQUIRED for all WSGI servers
- The `gunicorn.conf.py` or `uwsgi.ini` file with worker instrumentation is REQUIRED
- The startup command must use `opentelemetry-instrument` wrapper with your WSGI server

## Completion

**Tell the user:**

"I've completed the Application Signals enablement for your Python application. Here's what I modified:

**Files Changed:**
- IAM role: Added CloudWatchAgentServerPolicy
- UserData: Installed and configured CloudWatch Agent
- UserData: Installed ADOT Python SDK
- UserData/Service file: Added OpenTelemetry environment variables and instrumentation wrapper
- Dockerfile: Installed ADOT Python SDK and modified CMD with instrumentation wrapper (if using Docker)
- WSGI configuration: Added worker instrumentation (if using Gunicorn/uWSGI)

**Next Steps:**
1. Ensure that [Application Signals is enabled in AWS account](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable.html).
2. Review the changes I made using `git diff`
3. Deploy your infrastructure:
   - For CDK: `cdk deploy`
   - For Terraform: `terraform apply`
   - For CloudFormation: Deploy your stack
4. After deployment, wait 5-10 minutes for telemetry data to start flowing

**Verification:**
Once deployed, you can verify Application Signals is working by:
- Opening the AWS CloudWatch Console
- Navigating to Application Signals → Services
- Looking for your service (named: {{SERVICE_NAME}})
- Checking that traces and metrics are being collected

**Monitor Application Health:**
After enablement, you can monitor your application's operational health using Application Signals dashboards. For more information, see [Monitor the operational health of your applications with Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Services.html).

**Troubleshooting**
If you encounter any other issues, refer to the [CloudWatch APM troubleshooting guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable-Troubleshoot.html).

Let me know if you'd like me to make any adjustments before you deploy!"
