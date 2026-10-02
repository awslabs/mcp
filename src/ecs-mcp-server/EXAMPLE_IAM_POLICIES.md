# Example IAM Policies for ECS MCP Server

This document provides example IAM policies for common ECS MCP Server use cases. Each
policy is grounded in the actual AWS API calls the server makes (see the tool
implementations under `awslabs/ecs_mcp_server/api/`) so you can copy, paste, and adapt them
to your environment.

> **Important:** These are starting points, not turnkey policies. Always replace the
> placeholder account IDs (`123456789012`), regions (`us-east-1`), and resource names
> (`my-app`, `my-cluster`) with your own values, and review each statement against your
> organization's security requirements before attaching it to a role.

Policies are cumulative by scenario:

| Scenario | `ALLOW_WRITE` | `ALLOW_SENSITIVE_DATA` | Adds on top of |
|---|---|---|---|
| [1. Read-only / monitoring](#1-read-only--monitoring-access) | `false` | either | — |
| [2. Troubleshooting](#2-troubleshooting-access) | `false` | `true` recommended | (1) |
| [3. Full deployment](#3-full-deployment-access-allow_writetrue) | `true` | either | (1) + (2) |
| [4. Single-cluster scoped](#4-optional-single-cluster-scoped-example) | `false` | either | (1), resource-scoped |

## 1. Read-Only / Monitoring Access

Covers everything the server can do with `ALLOW_WRITE=false` (the default): the `List*`
and `Describe*` actions used by `ecs_resource_management`, ECR image/repository lookups
used by the troubleshooting and Express Mode tools, and the CloudWatch Logs / networking
reads used to inspect running services. Suitable for dashboards, chatbots, and read-only
assistants.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECSReadOnly",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeCapacityProviders",
        "ecs:DescribeClusters",
        "ecs:DescribeContainerInstances",
        "ecs:DescribeExpressGatewayService",
        "ecs:DescribeServiceDeployments",
        "ecs:DescribeServiceRevisions",
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:DescribeTasks",
        "ecs:DescribeTaskSets",
        "ecs:ListAccountSettings",
        "ecs:ListAttributes",
        "ecs:ListClusters",
        "ecs:ListContainerInstances",
        "ecs:ListExpressGatewayServices",
        "ecs:ListServiceDeployments",
        "ecs:ListServices",
        "ecs:ListServicesByNamespace",
        "ecs:ListTagsForResource",
        "ecs:ListTaskDefinitionFamilies",
        "ecs:ListTaskDefinitions",
        "ecs:ListTasks"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRReadOnly",
      "Effect": "Allow",
      "Action": [
        "ecr:DescribeImages",
        "ecr:DescribeRepositories",
        "ecr:GetAuthorizationToken",
        "ecr:ListImages"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudFormationReadOnly",
      "Effect": "Allow",
      "Action": [
        "cloudformation:DescribeStacks",
        "cloudformation:ListStacks"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogsReadOnly",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/ecs/*"
    },
    {
      "Sid": "NetworkingReadOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInternetGateways",
        "ec2:DescribeNatGateways",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeRouteTables",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSubnets",
        "ec2:DescribeVpcs",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetHealth"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMRoleValidationReadOnly",
      "Effect": "Allow",
      "Action": "iam:GetRole",
      "Resource": [
        "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
        "arn:aws:iam::123456789012:role/ecsInfrastructureRoleForExpressServices"
      ]
    }
  ]
}
```

`ec2:Describe*` and `elasticloadbalancing:Describe*` do not support resource-level
permissions, so they must use `"Resource": "*"`; the `fetch_network_configuration` action
also scans every VPC/load balancer in the account/region to discover which ones belong to
your ECS workloads.

## 2. Troubleshooting Access

Adds the CloudFormation stack introspection and detailed log filtering used by
`ecs_troubleshooting_tool` (`fetch_cloudformation_status`, `fetch_task_logs`,
`fetch_service_events`, `fetch_task_failures`, `detect_image_pull_failures`). Still fully
read-only, so it is safe to use with `ALLOW_WRITE=false`. Set `ALLOW_SENSITIVE_DATA=true`
only if the operator is trusted to see log contents, environment variables, and other
potentially sensitive task details.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudFormationStackInspection",
      "Effect": "Allow",
      "Action": [
        "cloudformation:DescribeStackEvents",
        "cloudformation:DescribeStackResources",
        "cloudformation:DescribeStacks",
        "cloudformation:GetTemplate",
        "cloudformation:ListStackResources",
        "cloudformation:ListStacks"
      ],
      "Resource": "arn:aws:cloudformation:us-east-1:123456789012:stack/my-app-*/*"
    },
    {
      "Sid": "CloudWatchLogsTroubleshooting",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:FilterLogEvents",
        "logs:GetLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/ecs/*"
    }
  ]
}
```

Combine this with the `ECSReadOnly`, `ECRReadOnly`, and `NetworkingReadOnly` statements
from section 1 — the troubleshooting tool relies on all of them to correlate service
events, task failures, and network misconfigurations.

## 3. Full Deployment Access (`ALLOW_WRITE=true`)

Required for the Express Mode deployment tools (`build_and_push_image_to_ecr`,
`validate_ecs_express_mode_prerequisites`, `wait_for_service_ready`, `delete_app`) and for
write operations on `ecs_resource_management` (any action that is not `List*`/`Describe*`,
for example `CreateCluster`, `CreateService`, `RegisterTaskDefinition`, `RunTask`,
`UpdateService`, `DeleteService`). This is a curated subset of
`SUPPORTED_ECS_OPERATIONS`: it intentionally excludes account-wide settings
(`PutAccountSetting`, `PutAccountSettingDefault`, `DeleteAccountSetting`) and
container-agent-internal operations (`DiscoverPollEndpoint`,
`SubmitAttachmentStateChanges`, `SubmitContainerStateChange`, `SubmitTaskStateChange`,
`UpdateContainerAgent`, `UpdateContainerInstancesState`) that the ECS agent calls on your
behalf rather than a deploying user or CLI — add them explicitly if your workflow needs
them. Include everything from sections 1 and 2, plus:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECSWriteOperations",
      "Effect": "Allow",
      "Action": [
        "ecs:CreateCapacityProvider",
        "ecs:CreateCluster",
        "ecs:CreateExpressGatewayService",
        "ecs:CreateService",
        "ecs:CreateTaskSet",
        "ecs:DeleteCapacityProvider",
        "ecs:DeleteCluster",
        "ecs:DeleteExpressGatewayService",
        "ecs:DeleteService",
        "ecs:DeleteTaskDefinitions",
        "ecs:DeleteTaskSet",
        "ecs:DeleteAttributes",
        "ecs:DeregisterContainerInstance",
        "ecs:DeregisterTaskDefinition",
        "ecs:ExecuteCommand",
        "ecs:GetTaskProtection",
        "ecs:PutAttributes",
        "ecs:PutClusterCapacityProviders",
        "ecs:RegisterContainerInstance",
        "ecs:RegisterTaskDefinition",
        "ecs:RunTask",
        "ecs:StartTask",
        "ecs:StopServiceDeployment",
        "ecs:StopTask",
        "ecs:TagResource",
        "ecs:UntagResource",
        "ecs:UpdateCapacityProvider",
        "ecs:UpdateCluster",
        "ecs:UpdateClusterSettings",
        "ecs:UpdateExpressGatewayService",
        "ecs:UpdateService",
        "ecs:UpdateServicePrimaryTaskSet",
        "ecs:UpdateTaskProtection",
        "ecs:UpdateTaskSet"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRRepositoryLifecycle",
      "Effect": "Allow",
      "Action": [
        "ecr:CreateRepository",
        "ecr:DeleteLifecyclePolicy",
        "ecr:DeleteRepository",
        "ecr:DeleteRepositoryPolicy",
        "ecr:DescribeRepositories",
        "ecr:PutImageScanningConfiguration",
        "ecr:PutImageTagMutability",
        "ecr:PutLifecyclePolicy",
        "ecr:SetRepositoryPolicy",
        "ecr:TagResource"
      ],
      "Resource": "arn:aws:ecr:us-east-1:123456789012:repository/*-repo"
    },
    {
      "Sid": "KMSKeyForECRRepositoryEncryption",
      "Effect": "Allow",
      "Action": [
        "kms:CreateAlias",
        "kms:CreateKey",
        "kms:DeleteAlias",
        "kms:DescribeKey",
        "kms:EnableKeyRotation",
        "kms:PutKeyPolicy",
        "kms:ScheduleKeyDeletion",
        "kms:TagResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudFormationECRInfrastructureStack",
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:DeleteStack",
        "cloudformation:UpdateStack"
      ],
      "Resource": "arn:aws:cloudformation:us-east-1:123456789012:stack/*-ecr-infrastructure/*"
    },
    {
      "Sid": "IAMRoleLifecycleForECRPushPullRole",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:DeleteRolePolicy",
        "iam:GetRole",
        "iam:PutRolePolicy",
        "iam:TagRole"
      ],
      "Resource": "arn:aws:iam::123456789012:role/*-ecr-role"
    },
    {
      "Sid": "IAMPassRoleForECSTaskExecutionRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "ecs-tasks.amazonaws.com"
        }
      }
    },
    {
      "Sid": "IAMPassRoleForExpressModeInfrastructureRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::123456789012:role/ecsInfrastructureRoleForExpressServices",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "ecs.amazonaws.com"
        }
      }
    },
    {
      "Sid": "STSAssumeECRPushPullRole",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::123456789012:role/*-ecr-role"
    }
  ]
}
```

`ECRRepositoryLifecycle` and `KMSKeyForECRRepositoryEncryption` are what
`build_and_push_image_to_ecr` needs to create/update/delete the `templates/ecr_infrastructure.json`
CloudFormation stack (an `AWS::ECR::Repository` with a repository policy, lifecycle
policy, image scanning, and tag-immutability settings, encrypted with a customer-managed
`AWS::KMS::Key`) — CloudFormation executes these calls under your own credentials, since no
CloudFormation service role is configured, so the deploying identity needs them directly.
The actual image push/pull rights (`ecr:PutImage`, `ecr:UploadLayerPart`, etc.) are granted
by the repository's own resource policy to the assumed `*-ecr-role`, not to the caller
directly, which is why only `sts:AssumeRole` is needed here.

`IAMPassRoleForECSTaskExecutionRole` and `IAMPassRoleForExpressModeInfrastructureRole` cover
the two roles `validate_ecs_express_mode_prerequisites` checks and `CreateExpressGatewayService`
passes to ECS: the task execution role (trusted by `ecs-tasks.amazonaws.com`) and the
infrastructure role (trusted by `ecs.amazonaws.com`) that ECS uses to provision the
Application Load Balancer, target groups, and security groups behind an Express Gateway
Service. These conditions must stay in separate statements because each role trusts a
different service principal — replace the role names if you pass custom
`execution_role_arn`/`infrastructure_role_arn` values.

## 4. (Optional) Single-Cluster Scoped Example

Restricts the read-only policy from section 1 to a single named ECS cluster using resource
ARNs, for cases where one IAM role/identity should only ever see or touch one cluster.
Replace `my-cluster` with your cluster name.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECSSingleClusterReadOnly",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeContainerInstances",
        "ecs:DescribeServiceDeployments",
        "ecs:DescribeServiceRevisions",
        "ecs:DescribeServices",
        "ecs:DescribeTaskSets",
        "ecs:DescribeTasks",
        "ecs:ListContainerInstances",
        "ecs:ListServiceDeployments",
        "ecs:ListTagsForResource",
        "ecs:ListTasks"
      ],
      "Resource": [
        "arn:aws:ecs:us-east-1:123456789012:cluster/my-cluster",
        "arn:aws:ecs:us-east-1:123456789012:service/my-cluster/*",
        "arn:aws:ecs:us-east-1:123456789012:task/my-cluster/*",
        "arn:aws:ecs:us-east-1:123456789012:task-set/my-cluster/*/*",
        "arn:aws:ecs:us-east-1:123456789012:container-instance/my-cluster/*"
      ]
    },
    {
      "Sid": "ECSDescribeClustersScoped",
      "Effect": "Allow",
      "Action": "ecs:DescribeClusters",
      "Resource": "arn:aws:ecs:us-east-1:123456789012:cluster/my-cluster"
    },
    {
      "Sid": "ECSCapacityProvidersScoped",
      "Effect": "Allow",
      "Action": "ecs:DescribeCapacityProviders",
      "Resource": "arn:aws:ecs:us-east-1:123456789012:capacity-provider/*"
    },
    {
      "Sid": "ECSAccountWideReadOnlyActionsWithoutResourceSupport",
      "Effect": "Allow",
      "Action": [
        "ecs:ListClusters",
        "ecs:ListServices",
        "ecs:ListTaskDefinitionFamilies",
        "ecs:ListTaskDefinitions",
        "ecs:DescribeTaskDefinition"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogsSingleClusterScoped",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/ecs/my-cluster*"
    }
  ]
}
```

`ecs:ListClusters`, `ecs:ListServices`, `ecs:ListTaskDefinitions`,
`ecs:ListTaskDefinitionFamilies`, and `ecs:DescribeTaskDefinition` do not support
resource-level scoping (task definitions are not cluster-scoped resources in IAM, and
`ecs:ListServices` has no resource-level permission support at all), so those actions
remain on `"Resource": "*"` even in this narrowly-scoped example. `ecs:DescribeCapacityProviders`
does support resource-level permissions, but only against the `capacity-provider` resource
type — not the cluster/service/task ARNs used above — so it gets its own statement scoped
to `capacity-provider/*`.
