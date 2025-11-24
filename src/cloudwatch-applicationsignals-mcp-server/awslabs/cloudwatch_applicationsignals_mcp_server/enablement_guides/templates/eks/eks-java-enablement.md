# Task: Enable AWS Application Signals for Java Applications on Amazon EKS

This guide shows how to modify the existing CDK and Terraform infrastructure code to enable AWS Application Signals for Java applications running on Amazon EKS.

## Prerequisites

- Application Signals enabled in your AWS account (see [Enable Application Signals in your account](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable.html))
- Existing EKS cluster deployed using the provided CDK or Terraform code
- Java application containerized and pushed to ECR
- AWS CLI configured with appropriate permissions

## Critical Requirements

**Error Handling:**
- If you cannot determine required values from the IaC, STOP and ask the user
- For multiple EC2 instances, ask which one(s) to modify
- Preserve all existing UserData commands; add new ones in sequence

**Do NOT:**
- Run deployment commands automatically (`cdk deploy`, `terraform apply`, etc.)
- Remove existing application startup logic
- Skip the user approval step before deployment

## CDK Implementation

### 1. Install CloudWatch Observability Add-on

Create an IAM role and install the CloudWatch Observability add-on:

```typescript
import * as eks from 'aws-cdk-lib/aws-eks';
import * as iam from 'aws-cdk-lib/aws-iam';

// Create IAM role for CloudWatch agent
const cloudwatchRole = new iam.Role(this, 'CloudWatchAgentAddOnRole', {
  assumedBy: new iam.OpenIdConnectPrincipal(cluster.openIdConnectProvider),
  managedPolicies: [
    iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy')
  ],
});

// Install the CloudWatch Observability add-on
new eks.CfnAddon(this, 'CloudWatchAddon', {
  addonName: 'amazon-cloudwatch-observability',
  clusterName: cluster.clusterName,
  serviceAccountRoleArn: cloudwatchRole.roleArn
});
```

### 2. Add Java Instrumentation Annotation

Update your deployment template metadata to include the Java instrumentation annotation:

```typescript
template: {
  metadata: {
    labels: { app: config.appName },
    annotations: {
      'instrumentation.opentelemetry.io/inject-java': 'true'
    }
  },
  // ... rest of your template configuration
}
```

## Terraform Implementation

### 1. Add CloudWatch Agent IAM Permissions

Add the CloudWatch policy to the node role:

```hcl
# Additional IAM policies for Application Signals
resource "aws_iam_role_policy_attachment" "cloudwatch_agent_policy" {
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
  role       = aws_iam_role.node_role.name
}
```

**Important:** Add this policy attachment to your node group's `depends_on` block:

```hcl
resource "aws_eks_node_group" "app_nodes" {
  # ... existing configuration ...

  depends_on = [
    aws_iam_role_policy_attachment.node_policy,
    aws_iam_role_policy_attachment.cloudwatch_agent_policy
  ]
}
```

### 2. Install CloudWatch Observability Add-on

Add the CloudWatch Observability EKS add-on:

```hcl
# CloudWatch Observability Add-on
resource "aws_eks_addon" "cloudwatch_observability" {
  cluster_name = aws_eks_cluster.app_cluster.name
  addon_name   = "amazon-cloudwatch-observability"

  depends_on = [
    aws_eks_node_group.app_nodes
  ]
}
```

### 3. Add Java Instrumentation Annotation

Update your Kubernetes deployment template to include the Java instrumentation annotation:

```hcl
template {
  metadata {
    labels = {
      app = var.app_name
    }
    annotations = {
      "instrumentation.opentelemetry.io/inject-java" = "true"
    }
  }
  # ... rest of your template configuration
}
```

## Important Notes

- The Java instrumentation annotation will cause pods to restart automatically
- Java applications typically have faster startup times with Application Signals compared to other languages
- It may take a few minutes for data to appear in the Application Signals console after deployment

## Completion

**Tell the user:**

"I've completed the Application Signals enablement for your Java application. Here's what I modified:

**Files Changed:**
- IAM role: Added CloudWatchAgentServerPolicy
- CloudWatch Observability EKS add-on: Added to the EKS Cluster
- Kubernetes Deployment: Instrumentation annotation added with inject-java set to true

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
