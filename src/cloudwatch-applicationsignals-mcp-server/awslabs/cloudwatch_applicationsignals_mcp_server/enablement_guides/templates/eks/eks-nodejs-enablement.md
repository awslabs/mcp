# Enable Application Signals for Node.js Applications on Amazon EKS

This guide shows how to modify the existing CDK and Terraform infrastructure code to enable AWS Application Signals for Node.js applications running on Amazon EKS.

## Prerequisites

- Application Signals enabled in your AWS account (see [Enable Application Signals in your account](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable.html))
- Existing EKS cluster deployed using the provided CDK or Terraform code
- Node.js application containerized and pushed to ECR
- AWS CLI configured with appropriate permissions

## CDK Implementation

### 1. Enable Application Signals Discovery (Optional)

The Application Signals discovery resource creates the service-linked role for Application Signals. This is typically created automatically when you first enable Application Signals in your account, but you can explicitly create it in CDK:

```typescript
import { aws_applicationsignals as applicationsignals } from 'aws-cdk-lib';

// Optional: Create Application Signals service-linked role
// Skip this if Application Signals is already enabled in your account
const cfnDiscovery = new applicationsignals.CfnDiscovery(this,
  'ApplicationSignalsServiceRole', { }
);
```

**Note:** This step can be skipped if Application Signals is already enabled in your AWS account.

### 2. Install CloudWatch Observability Add-on

Create an IAM role and install the CloudWatch Observability add-on:

```typescript
import * as eks from 'aws-cdk-lib/aws-eks';
import * as iam from 'aws-cdk-lib/aws-iam';

// Create IAM role for CloudWatch agent
const cloudwatchRole = new iam.Role(this, 'CloudWatchAgentAddOnRole', {
  assumedBy: new iam.OpenIdConnectPrincipal(cluster.openIdConnectProvider),
  managedPolicies: [
    iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
    iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayWriteOnlyAccess')
  ],
});

// Install the CloudWatch Observability add-on
new eks.CfnAddon(this, 'CloudWatchAddon', {
  addonName: 'amazon-cloudwatch-observability',
  clusterName: cluster.clusterName,
  serviceAccountRoleArn: cloudwatchRole.roleArn
});
```

### 3. Add Node.js Instrumentation Annotation

Modify your deployment manifest to include the Node.js instrumentation annotation:

```typescript
const deployment = {
  apiVersion: 'apps/v1',
  kind: 'Deployment',
  metadata: { 
    name: config.appName
  },
  spec: {
    replicas: 1,
    selector: { matchLabels: { app: config.appName } },
    template: {
      metadata: { 
        labels: { app: config.appName },
        annotations: {
          'instrumentation.opentelemetry.io/inject-nodejs': 'true'
        }
      },
      spec: {
        containers: [{
          name: config.appName,
          image: ecrImageUri,
          ports: [{ containerPort: config.port }],
          env: [
            { name: 'PORT', value: config.port.toString() },
            { name: 'AWS_REGION', value: this.region }
          ],
          lifecycle: {
            postStart: {
              exec: {
                command: ['sh', '-c', 'nohup bash /app/generate-traffic.sh > /dev/null 2>&1 &']
              }
            }
          }
        }]
      }
    }
  }
};
```

## Terraform Implementation

### 1. Add CloudWatch Agent IAM Permissions

Update the node role to include CloudWatch permissions:

```hcl
resource "aws_iam_role_policy_attachment" "node_policy" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
    "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
    "arn:aws:iam::aws:policy/AWSXRayWriteOnlyAccess"
  ])
  policy_arn = each.value
  role       = aws_iam_role.node_role.name
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

### 3. Add Node.js Instrumentation Annotation

Update the Kubernetes deployment to include the Node.js instrumentation annotation:

```hcl
# Kubernetes Deployment with Application Signals
resource "kubernetes_deployment" "app" {
  metadata {
    name = var.app_name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = var.app_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.app_name
        }
        annotations = {
          "instrumentation.opentelemetry.io/inject-nodejs" = "true"
        }
      }

      spec {
        container {
          image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${var.image_name}:latest"
          name  = var.app_name

          port {
            container_port = var.port
          }

          env {
            name  = "PORT"
            value = tostring(var.port)
          }

          env {
            name  = "AWS_REGION"
            value = data.aws_region.current.name
          }

          lifecycle {
            post_start {
              exec {
                command = ["sh", "-c", "nohup bash /app/generate-traffic.sh > /dev/null 2>&1 &"]
              }
            }
          }
        }
      }
    }
  }

  depends_on = [
    aws_eks_node_group.app_nodes,
    aws_eks_addon.cloudwatch_observability
  ]
}
```

## Deployment Steps

### For CDK:
1. Update your CDK stack with the changes above
2. Deploy the updated stack:
   ```bash
   cd infrastructure/eks/cdk
   cdk deploy
   ```

### For Terraform:
1. Update your `main.tf` with the changes above
2. Apply the changes:
   ```bash
   cd infrastructure/eks/terraform
   terraform plan -var-file="config/nodejs-express.tfvars"
   terraform apply -var-file="config/nodejs-express.tfvars"
   ```

## Verification

After deployment, verify Application Signals is working:

1. Check that pods are running with instrumentation:
   ```bash
   kubectl get pods
   kubectl describe pod <pod-name>
   ```

2. Look for the OpenTelemetry sidecar containers and annotations

3. Navigate to CloudWatch Application Signals in the AWS Console to view metrics and traces

## Important Notes

- The Node.js instrumentation annotation will cause pods to restart automatically
- For Node.js applications with ESM module format, see [special configuration requirements](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable-EKS.html#EKS-NodeJs-ESM) in the AWS documentation
- It may take a few minutes for data to appear in the Application Signals console after deployment