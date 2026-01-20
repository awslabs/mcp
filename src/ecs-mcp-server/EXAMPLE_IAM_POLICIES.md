# Example IAM Policies for ECS MCP Server

This document provides example IAM policies tailored for different ECS MCP Server use cases. Always follow the principle of least privilege when granting permissions.

## Table of Contents

1. [Read-Only Monitoring](#read-only-monitoring)
2. [Troubleshooting](#troubleshooting)
3. [Deployment and Management](#deployment-and-management)
4. [Service-Specific Access](#service-specific-access)
5. [Express Mode Operations](#express-mode-operations)

---

## Read-Only Monitoring

This policy grants read-only access to ECS resources for monitoring and observability purposes.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECSReadOnly",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeClusters",
        "ecs:ListClusters",
        "ecs:DescribeServices",
        "ecs:ListServices",
        "ecs:DescribeTasks",
        "ecs:ListTasks",
        "ecs:DescribeTaskDefinition",
        "ecs:ListTaskDefinitions",
        "ecs:DescribeContainerInstances",
        "ecs:ListContainerInstances",
        "ecs:DescribeCapacityProviders",
        "ecs:ListAttributes",
        "ecs:ListTagsForResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRReadOnly",
      "Effect": "Allow",
      "Action": [
        "ecr:DescribeRepositories",
        "ecr:ListImages",
        "ecr:DescribeImages"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Troubleshooting

This policy includes permissions needed for diagnosing ECS deployment issues, including CloudWatch logs, service events, and network configuration inspection.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECSReadAccess",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeClusters",
        "ecs:ListClusters",
        "ecs:DescribeServices",
        "ecs:ListServices",
        "ecs:DescribeTasks",
        "ecs:ListTasks",
        "ecs:DescribeTaskDefinition",
        "ecs:ListTaskDefinitions",
        "ecs:DescribeContainerInstances",
        "ecs:ListContainerInstances"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudFormationReadAccess",
      "Effect": "Allow",
      "Action": [
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:DescribeStackResources",
        "cloudformation:ListStacks"
      ],
      "Resource": "*"
    },
    {
      "Sid": "NetworkDiagnostics",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeNetworkInterfaces",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetHealth"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRImagePullDiagnostics",
      "Effect": "Allow",
      "Action": [
        "ecr:DescribeRepositories",
        "ecr:DescribeImages",
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Deployment and Management

This policy grants full permissions for deploying and managing ECS resources. Use this policy when `ALLOW_WRITE=true` is configured.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECSFullAccess",
      "Effect": "Allow",
      "Action": [
        "ecs:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRFullAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudFormationManagement",
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:DescribeStackResources",
        "cloudformation:ListStacks"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMPassRole",
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "ecs-tasks.amazonaws.com"
        }
      }
    },
    {
      "Sid": "IAMRoleManagement",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:GetRole",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    },
    {
      "Sid": "NetworkManagement",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:CreateSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "elasticloadbalancing:*"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Service-Specific Access

This policy demonstrates how to scope permissions to specific ECS clusters and services. Replace the placeholders with your actual AWS account ID, region, cluster name, and service name.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SpecificClusterAccess",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:ListServices",
        "ecs:DescribeTasks",
        "ecs:ListTasks",
        "ecs:DescribeTaskDefinition"
      ],
      "Resource": [
        "arn:aws:ecs:REGION:ACCOUNT_ID:cluster/CLUSTER_NAME",
        "arn:aws:ecs:REGION:ACCOUNT_ID:service/CLUSTER_NAME/*",
        "arn:aws:ecs:REGION:ACCOUNT_ID:task/CLUSTER_NAME/*",
        "arn:aws:ecs:REGION:ACCOUNT_ID:task-definition/*:*"
      ]
    },
    {
      "Sid": "SpecificServiceManagement",
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:StopTask",
        "ecs:StartTask"
      ],
      "Resource": [
        "arn:aws:ecs:REGION:ACCOUNT_ID:service/CLUSTER_NAME/SERVICE_NAME",
        "arn:aws:ecs:REGION:ACCOUNT_ID:task/CLUSTER_NAME/*"
      ],
      "Condition": {
        "StringEquals": {
          "ecs:cluster": "arn:aws:ecs:REGION:ACCOUNT_ID:cluster/CLUSTER_NAME"
        }
      }
    },
    {
      "Sid": "CloudWatchLogsForService",
      "Effect": "Allow",
      "Action": [
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource": "arn:aws:logs:REGION:ACCOUNT_ID:log-group:/ecs/SERVICE_NAME:*"
    }
  ]
}
```

---

## Express Mode Operations

This policy includes permissions specifically for ECS Express Mode deployment workflows, including the creation and management of Express Gateway Services.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ExpressGatewayServiceAccess",
      "Effect": "Allow",
      "Action": [
        "ecs-dev:CreateService",
        "ecs-dev:UpdateService",
        "ecs-dev:DeleteService",
        "ecs-dev:DescribeService",
        "ecs-dev:ListServices",
        "ecs:DescribeServices",
        "ecs:ListServices",
        "ecs:DescribeTasks",
        "ecs:ListTasks"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRForExpressMode",
      "Effect": "Allow",
      "Action": [
        "ecr:CreateRepository",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetAuthorizationToken",
        "ecr:DescribeRepositories",
        "ecr:ListImages"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudFormationForExpressMode",
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMForExpressMode",
      "Effect": "Allow",
      "Action": [
        "iam:GetRole",
        "iam:PassRole",
        "iam:CreateRole",
        "iam:AttachRolePolicy"
      ],
      "Resource": [
        "arn:aws:iam::*:role/ecsTaskExecutionRole",
        "arn:aws:iam::*:role/ecsInfrastructureRoleForExpressServices",
        "arn:aws:iam::*:role/ecr-*"
      ]
    },
    {
      "Sid": "PrerequisiteValidation",
      "Effect": "Allow",
      "Action": [
        "iam:GetRole",
        "ecr:DescribeImages"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Permission Boundary Example

To further restrict permissions, you can apply a permission boundary. This example limits ECS operations to a specific region and prevents deletion of production resources.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RegionRestriction",
      "Effect": "Deny",
      "Action": "ecs:*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    },
    {
      "Sid": "ProductionProtection",
      "Effect": "Deny",
      "Action": [
        "ecs:DeleteCluster",
        "ecs:DeleteService",
        "ecs:DeregisterTaskDefinition"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:ResourceTag/Environment": "production"
        }
      }
    }
  ]
}
```

---

## Best Practices

1. **Use Dedicated Roles**: Create separate IAM roles for different use cases (monitoring, troubleshooting, deployment)
2. **Apply Least Privilege**: Start with read-only access and add write permissions only when necessary
3. **Use Resource-Level Permissions**: Scope permissions to specific clusters, services, or resource ARNs whenever possible
4. **Implement Permission Boundaries**: Apply permission boundaries to limit the maximum permissions
5. **Enable CloudTrail**: Monitor API calls to understand what permissions are actually being used
6. **Use Tags**: Tag resources and use tag-based conditions to enforce access controls
7. **Regular Audits**: Periodically review and remove unused permissions

## Additional Resources

- [AWS ECS IAM Roles and Policies](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-iam.html)
- [IAM Policy Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [ECS Task Execution IAM Role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html)
- [IAM Policy Simulator](https://policysim.aws.amazon.com/)
