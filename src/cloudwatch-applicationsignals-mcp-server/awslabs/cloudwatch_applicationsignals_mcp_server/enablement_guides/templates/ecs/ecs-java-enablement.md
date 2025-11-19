# Task: Enable AWS Application Signals for Java on ECS

## Overview
This guide provides complete steps to enable AWS Application Signals for ECS Fargate services, distributed tracing, performance monitoring, and service mapping.

## Prerequisites
- Services running on ECS both the ec2 and Fargate launch types.
- Applications using Java language

## Implementation Steps

**Constraints:**
You must strictly follow the steps in the order below, do not skip or combine steps.

### Step 1: Setup CloudWatch Agent Task
When running in ECS, the CloudWatch Agent is deployed as a sidecar container next to the application container.
Proper permissions, a CWAgentConfig configuration file, and the target log group must be set up to enable logging and metrics collection.

#### 1.1 Add CloudWatch Agent Permissions to ECS Task Role

Update ECS task role to add CloudWatchAgentServerPolicy:

```typescript
// Update existing taskRole or create new one
const taskRole = new iam.Role(this, 'EcsTaskRole', {
  assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
  managedPolicies: [
    iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess'),
    iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
  ],
  inlinePolicies: {
    // Your existing inline policies...
  },
});
```

#### 1.2 Create CloudWatch Agent Log Group
```typescript
const cwAgentLogGroup = new logs.LogGroup(this, 'CwAgentLogGroup', {
  logGroupName: '/ecs/ecs-cwagent',
  removalPolicy: cdk.RemovalPolicy.DESTROY,
  retention: logs.RetentionDays.ONE_WEEK,
});
```

#### 1.3 Add CloudWatch Agent Container to Each Task Definition
```typescript
// Add CloudWatch Agent sidecar to each task definition
const cwAgentContainer = taskDefinition.addContainer('ecs-cwagent-{SERVICE_NAME}', {
  image: ecs.ContainerImage.fromRegistry('public.ecr.aws/cloudwatch-agent/cloudwatch-agent:latest'),
  essential: false,
  memoryReservationMiB: 128,
  cpu: 64,
  environment: {
    CW_CONFIG_CONTENT: JSON.stringify({
      "traces": {
        "traces_collected": {
          "application_signals": {}
        }
      },
      "logs": {
        "metrics_collected": {
          "application_signals": {}
        }
      }
    }),
  },
  logging: ecs.LogDrivers.awsLogs({
    streamPrefix: 'ecs',
    logGroup: cwAgentLogGroup,
  }),
});
```

### Step 2: Add AWS Distro of OpenTelemetry Zero-Code Instrumentation to Main Service

#### 2.1 Add Bind Mount Volumes to Task Definition
```typescript
const taskDefinition = new ecs.FargateTaskDefinition(this, '{SERVICE_NAME}TaskDefinition', {
  // Existing configuration...
  volumes: [
    {
      name: "opentelemetry-auto-instrumentation-java"
    }
  ],
});
```

#### 2.2 Add ADOT Auto-instrumentation Init Container
```typescript
const initContainer = taskDefinition.addContainer('init', {
  image: ecs.ContainerImage.fromRegistry('public.ecr.aws/aws-observability/adot-autoinstrumentation-java:v2.20.0'),
  essential: false,
  memoryReservationMiB: 64,
  cpu: 32,
  command: ['cp', '-a', '/javaagent.jar', '/otel-auto-instrumentation-java/javaagent.jar'],
  logging: ecs.LogDrivers.awsLogs({
    streamPrefix: 'init-{SERVICE_NAME}',
    logGroup: serviceLogGroup,
  }),
});

// Add mount point to init container
initContainer.addMountPoints({
  sourceVolume: 'opentelemetry-auto-instrumentation-java',
  containerPath: '/otel-auto-instrumentation-java',
  readOnly: false,
});
```

#### 2.3 Configure Main Application Container OpenTelemetry Environment Variables

##### Java Application Configuration:
```typescript
const mainContainer = taskDefinition.addContainer('{SERVICE_NAME}-container', {
  // Existing configuration...
  environment: {
    // Existing environment variables...

    // ADOT Configuration for Application Signals
    OTEL_RESOURCE_ATTRIBUTES: 'service.name={SERVICE_NAME}', // SERVICE_NAME is defined by user
    OTEL_METRICS_EXPORTER: 'none',
    OTEL_LOGS_EXPORTER: 'none',
    JAVA_TOOL_OPTIONS: ' -javaagent:/otel-auto-instrumentation-java/javaagent.jar',
    OTEL_TRACES_EXPORTER: 'otlp',
    OTEL_EXPORTER_OTLP_PROTOCOL: 'http/protobuf',
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: 'http://localhost:4316/v1/traces',
    OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT: 'http://localhost:4316/v1/metrics',
    OTEL_AWS_APPLICATION_SIGNALS_ENABLED: 'true',
  },
});
```

#### 2.4 Add Mount Point to Main Container
```typescript
// Add mount point to main application container
mainContainer.addMountPoints({
  sourceVolume: 'opentelemetry-auto-instrumentation-java',
  containerPath: '/otel-auto-instrumentation-java',
  readOnly: false,
});
```

#### 2.5 Configure Container Dependencies
```typescript
// Ensure containers start in correct order
mainContainer.addContainerDependencies({
  container: initContainer,
  condition: ecs.ContainerDependencyCondition.SUCCESS,
});

mainContainer.addContainerDependencies({
  container: cwAgentContainer,
  condition: ecs.ContainerDependencyCondition.START,
});
```

## Completion

**Tell the user:**

"I've completed the Application Signals enablement for your application. Here's what I modified:

**Files Changed:**
- IAM role: Added CloudWatchAgentServerPolicy
- ECS container: Installed and configured CloudWatch Agent as sidecar
- ADOT SDK container: Mounted ADOT SDK dependencies into Application container
- Applicaiton container: Enabled zero-code instrumentation for Application

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
