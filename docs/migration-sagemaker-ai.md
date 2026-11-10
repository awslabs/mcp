# Migration Guide: Amazon SageMaker AI MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.sagemaker-ai-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The Amazon SageMaker AI MCP server registered 4 tools, all for Amazon SageMaker HyperPod clusters. `manage_hyperpod_cluster_nodes` ran one of five operations, each a single SageMaker API call: `ListClusters`, `ListClusterNodes`, `DescribeClusterNode`, `UpdateClusterSoftware`, or `BatchDeleteClusterNodes`. `describe_hp_cluster` and `update_hp_cluster` called `DescribeCluster` and `UpdateCluster`. `manage_hyperpod_stacks` deployed, described, or deleted an AWS CloudFormation stack built from one of the two HyperPod templates that AWS publishes in Amazon S3, one for Amazon EKS orchestration and one for Slurm, with the stack parameters read from a JSON file on your machine. The server never ran `kubectl` or `helm`. The EKS template installs the HyperPod Helm chart itself, in a nested stack, from the `aws/sagemaker-hyperpod-cli` repository. The AWS MCP Server makes the same SageMaker and CloudFormation calls through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. It also reaches the rest of the HyperPod API, such as `BatchRebootClusterNodes`, `BatchReplaceClusterNodes`, `CreateCluster`, and `DeleteCluster`, which this server didn't have.

No Agent Skill covers HyperPod cluster or node management. The `aws-ai-ml` skill covers SageMaker training jobs, fine-tuning, and endpoints, and its training jobs reference lists HyperPod job submission and cluster lifecycle as out of scope. For the CloudFormation side of `manage_hyperpod_stacks`, the [`aws-cloudformation`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-cloudformation) skill covers checking a template before you deploy it and finding out why a stack failed. The AWS MCP Server serves it through its `retrieve_skill` tool, or you can install it with `npx skills add aws/agent-toolkit-for-aws/skills`.

## Installing the Replacement

### Configuration

```json
{
  "mcpServers": {
    "aws": {
      "command": "uvx",
      "args": [
        "mcp-proxy-for-aws-cli@latest",
        "https://aws-mcp.us-east-1.api.aws/mcp",
        "--metadata",
        "AWS_REGION=us-east-1"
      ]
    }
  }
}
```

Set `AWS_REGION` to the Region of your HyperPod clusters. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

Your identity needs the same permissions the old server needed:

- `sagemaker:ListClusters`, `sagemaker:ListClusterNodes`, `sagemaker:DescribeCluster`, and `sagemaker:DescribeClusterNode`
- `sagemaker:UpdateCluster`, `sagemaker:UpdateClusterSoftware`, and `sagemaker:BatchDeleteClusterNodes` for changes, and `iam:PassRole` on the instance group execution roles you pass to `UpdateCluster`
- `cloudformation:DescribeStacks`, `cloudformation:CreateStack`, `cloudformation:UpdateStack`, and `cloudformation:DeleteStack`
- Permissions for everything the HyperPod template creates, because CloudFormation uses your credentials unless you pass a service role in `RoleARN`. By default, the EKS template creates nested stacks for the VPC, security groups, EKS cluster, S3 bucket and endpoint, FSx for Lustre file system, IAM roles, lifecycle scripts, Helm chart, and the HyperPod cluster.

Add `cloudformation:GetTemplateSummary` to list a template's parameters and `cloudformation:DescribeEvents` to see why a stack failed. Add `sagemaker:BatchRebootClusterNodes`, `sagemaker:BatchReplaceClusterNodes`, or `sagemaker:DeleteCluster` if you use those operations.

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

With the AWS MCP Server, ask your agent to do the same job and it makes the equivalent call through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. The old tools wrapped results in their own snake_case objects, such as `{"clusters": [{"cluster_name": ...}]}`. `call_boto3` returns the API response itself, such as `{"ClusterSummaries": [{"ClusterName": ...}]}`, and pages list operations automatically.

For example, the agent might run this in place of `list_clusters`, `describe_hp_cluster`, and `list_nodes`:

```python
clusters = await call_boto3(
    service_name="sagemaker",
    operation_name="ListClusters",
    region_name="us-east-1",
    params={},
)
result = []
for c in clusters["ClusterSummaries"]:
    detail = await call_boto3(
        service_name="sagemaker",
        operation_name="DescribeCluster",
        region_name="us-east-1",
        params={"ClusterName": c["ClusterName"]},
    )
    nodes = await call_boto3(
        service_name="sagemaker",
        operation_name="ListClusterNodes",
        region_name="us-east-1",
        params={"ClusterName": c["ClusterName"]},
    )
    result.append({
        "name": c["ClusterName"],
        "status": c["ClusterStatus"],
        "instance_groups": [
            {"name": g["InstanceGroupName"], "type": g["InstanceType"], "current": g["CurrentCount"], "target": g["TargetCount"]}
            for g in detail["InstanceGroups"]
        ],
        "nodes": [
            {"id": n.get("InstanceId"), "group": n["InstanceGroupName"], "status": n["InstanceStatus"]["Status"]}
            for n in nodes["ClusterNodeSummaries"]
        ],
    })
result
```

### Clusters and nodes

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `manage_hyperpod_cluster_nodes(operation="list_clusters")` | Called `ListClusters` with `MaxResults` (default 10), `NextToken`, `NameContains`, `CreationTimeAfter`, `CreationTimeBefore`, `SortBy`, `SortOrder`, and `TrainingPlanArn`, and returned one page: each cluster's name, ARN, status, creation time, and training plan ARNs | `call_boto3(service_name="sagemaker", operation_name="ListClusters", params={"NameContains": ...})`. In testing, `ListClusters` with both `NameContains` and `SortBy="NAME"` returned `InternalFailure` through both servers and the AWS CLI, so send one of them and sort in the script. |
| `manage_hyperpod_cluster_nodes(operation="list_nodes")` | Called `ListClusterNodes` with `ClusterName`, the same paging, time, and sort filters, and `InstanceGroupNameContains`. Returned one page of nodes with the instance group, instance ID, status, type, launch time, and last software update time, and dropped `NodeLogicalId`, `PrivateDnsHostname`, and `ImageVersionStatus`. | `call_boto3(service_name="sagemaker", operation_name="ListClusterNodes", params={"ClusterName": ..., "InstanceGroupNameContains": ...})` |
| `manage_hyperpod_cluster_nodes(operation="describe_node")` | Called `DescribeClusterNode` with `ClusterName` and `NodeId`. Reported every EBS volume size as `null`, because it read `VolumeSizeInGb` where the API returns `VolumeSizeInGB`, and dropped fields such as `NodeLogicalId`, `CurrentImageId`, and `ImageVersionStatus`. It required `node_id`, so it couldn't look a node up by its logical ID. | `call_boto3(service_name="sagemaker", operation_name="DescribeClusterNode", params={"ClusterName": ..., "NodeId": ...})`, or `"NodeLogicalId": ...` in place of `NodeId` |
| `describe_hp_cluster(cluster_name, region_name)` | Called `DescribeCluster` and returned the response as it came. It didn't catch errors, so a missing cluster came back as `Error executing tool describe_hp_cluster` without the reason. | `call_boto3(service_name="sagemaker", operation_name="DescribeCluster", params={"ClusterName": ...})` |
| `manage_hyperpod_cluster_nodes(operation="update_software")` | Called `UpdateClusterSoftware` with `ClusterName`, the optional `DeploymentConfig` (rolling batch sizes, wait interval, and rollback alarms), and the optional `InstanceGroups` (names only). The update starts right away. | `call_boto3(service_name="sagemaker", operation_name="UpdateClusterSoftware", params={"ClusterName": ..., "DeploymentConfig": {...}, "InstanceGroups": [{"InstanceGroupName": ...}]})`, as in the second example. The API also takes `ImageId`, which the old tool didn't send. |
| `manage_hyperpod_cluster_nodes(operation="batch_delete")` | Called `BatchDeleteClusterNodes` with `ClusterName` and `NodeIds`, and returned the deleted node IDs and the failures | `call_boto3(service_name="sagemaker", operation_name="BatchDeleteClusterNodes", params={"ClusterName": ..., "NodeIds": [...]})`, or `"NodeLogicalIds": [...]` |
| `update_hp_cluster(cluster_name, instance_groups, region_name)` | Called `UpdateCluster` with `ClusterName` and the `InstanceGroups` list as given. Its instructions told the agent to call `describe_hp_cluster` first, copy each instance group's settings, set `InstanceCount` to the count you want, and add a `ScheduledUpdateConfig` with a cron `ScheduleExpression` for scheduled AMI updates. | `call_boto3(service_name="sagemaker", operation_name="UpdateCluster", params={"ClusterName": ..., "InstanceGroups": [...]})` after a `DescribeCluster` call. `UpdateCluster` also takes `InstanceGroupsToDelete`, `NodeRecovery`, and `RestrictedInstanceGroups`, which the old tool didn't send. |

To start a rolling software update on one instance group, the agent might run:

```python
resp = await call_boto3(
    service_name="sagemaker",
    operation_name="UpdateClusterSoftware",
    region_name="us-east-1",
    params={
        "ClusterName": "<cluster-name>",
        "InstanceGroups": [{"InstanceGroupName": "worker-group-1"}],
        "DeploymentConfig": {
            "RollingUpdatePolicy": {"MaximumBatchSize": {"Type": "INSTANCE_COUNT", "Value": 1}},
            "WaitIntervalInSeconds": 60,
        },
    },
)
result = {"cluster_arn": resp["ClusterArn"]}
result
```

Because `run_script` exposes the full SageMaker API, HyperPod operations the old server never had, such as `BatchRebootClusterNodes`, `BatchReplaceClusterNodes`, `ListClusterEvents`, `CreateCluster`, and `DeleteCluster`, are also available.

### CloudFormation stacks

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `manage_hyperpod_stacks(operation="deploy")` | Read the parameter list from the JSON file at `params_file`, picked the EKS or Slurm template URL from `cluster_orchestrator`, and called `CreateStack` with the capabilities `CAPABILITY_IAM`, `CAPABILITY_NAMED_IAM`, and `CAPABILITY_AUTO_EXPAND`, `OnFailure="DELETE"`, and the tag `CreatedBy=HyperPodMCPServer`. When a stack with that name already existed and carried the tag, it called `UpdateStack` with the same template and parameters. When the stack existed without the tag, it refused. It returned as soon as CloudFormation accepted the request. | `run_script` with `call_boto3(service_name="cloudformation", operation_name="CreateStack", ...)`, as in the third example, or `UpdateStack` with the same parameters. The agent reads your parameters file with its own file tools and puts the list in the script, because `run_script` runs on the AWS MCP Server and can't open files on your machine. |
| `manage_hyperpod_stacks(operation="describe")` | Called `DescribeStacks`. For a stack with the `CreatedBy=HyperPodMCPServer` tag, it returned the stack ID, creation time, status, and outputs. For any other stack, it returned an error with the ID, creation time, and status. | `call_boto3(service_name="cloudformation", operation_name="DescribeStacks", params={"StackName": ...})`, plus `DescribeEvents` to see why a stack failed, as in the fourth example |
| `manage_hyperpod_stacks(operation="delete")` | Called `DescribeStacks`, refused unless the stack carried the `CreatedBy=HyperPodMCPServer` tag, then called `DeleteStack` and returned without waiting | `run_script` that checks the tag with `DescribeStacks` and then calls `DeleteStack`, as in the fifth example. `DeleteStack` on a stack name that doesn't exist returns success without an error, so check the stack first. |

The old tool's instructions named each stack `<HyperPodClusterName>-stack`. To find the stacks it created, ask the agent to call `DescribeStacks` without a stack name and keep the stacks tagged `CreatedBy=HyperPodMCPServer`.

To create a cluster from the EKS template, the agent might run:

```python
cluster_name = "<hyperpod-cluster-name>"
template_url = "https://aws-sagemaker-hyperpod-cluster-setup-us-east-1-prod.s3.us-east-1.amazonaws.com/templates/main-stack-eks-based-template.yaml"
instance_groups = [{
    "InstanceCount": 1,
    "InstanceGroupName": "worker-group-1",
    "InstanceType": "ml.m5.xlarge",
    "TargetAvailabilityZoneId": "use1-az1",
    "InstanceStorageConfigs": [{"EbsVolumeConfig": {"VolumeSizeInGB": 500}}],
}]
params = [
    {"ParameterKey": "HyperPodClusterName", "ParameterValue": cluster_name},
    {"ParameterKey": "ResourceNamePrefix", "ParameterValue": f"hp-{cluster_name}-4f2a9c"},
    {"ParameterKey": "Stage", "ParameterValue": "prod"},
    {"ParameterKey": "AvailabilityZoneIds", "ParameterValue": "use1-az1,use1-az2,use1-az4,use1-az5"},
    {"ParameterKey": "FsxAvailabilityZoneId", "ParameterValue": "use1-az1"},
    {"ParameterKey": "NodeProvisioningMode", "ParameterValue": "Continuous"},
    {"ParameterKey": "InstanceGroupSettings1", "ParameterValue": json.dumps(instance_groups)},
]
stack = await call_boto3(
    service_name="cloudformation",
    operation_name="CreateStack",
    region_name="us-east-1",
    params={
        "StackName": f"{cluster_name}-stack",
        "TemplateURL": template_url,
        "Parameters": params,
        "Capabilities": ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
        "OnFailure": "DELETE",
        "Tags": [{"Key": "CreatedBy", "Value": "HyperPodMCPServer"}],
    },
)
result = {"stack_id": stack["StackId"]}
result
```

These are the parameters the old tool's instructions asked for. For a Slurm cluster, use `https://aws-sagemaker-hyperpod-cluster-setup-us-east-1-prod.s3.us-east-1.amazonaws.com/templates-slurm/main-stack-slurm-based-template.yaml` and give each instance group an `InstanceGroupType` of `Controller`, `Login`, or `Compute`, as the old tool's instructions did. The template's default for `InstanceGroupSettings1` shows the Slurm format. `GetTemplateSummary` with the template URL lists every parameter with its description and default: 156 for the EKS template and 92 for the Slurm template. Every one of them has a default, so a parameter you leave out takes the template's value. The old tool said a new stack typically takes about 30 minutes to finish.

To check on a stack and see why it failed, the agent might run:

```python
resp = await call_boto3(
    service_name="cloudformation",
    operation_name="DescribeStacks",
    region_name="us-east-1",
    params={"StackName": "<stack-name>"},
)
stack = resp["Stacks"][0]
events = await call_boto3(
    service_name="cloudformation",
    operation_name="DescribeEvents",
    region_name="us-east-1",
    params={"StackName": stack["StackId"], "Filters": {"FailedEvents": True}},
)
result = {
    "status": stack["StackStatus"],
    "reason": stack.get("StackStatusReason"),
    "created_by_old_server": {"Key": "CreatedBy", "Value": "HyperPodMCPServer"} in stack.get("Tags", []),
    "outputs": {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])},
    "failures": [
        {"resource": e.get("LogicalResourceId"), "status": e.get("ResourceStatus"), "reason": e.get("ResourceStatusReason")}
        for e in events["OperationEvents"]
    ],
}
result
```

And this in place of `delete`, keeping the old tool's ownership check:

```python
resp = await call_boto3(
    service_name="cloudformation",
    operation_name="DescribeStacks",
    region_name="us-east-1",
    params={"StackName": "<stack-name>"},
)
stack = resp["Stacks"][0]
if {"Key": "CreatedBy", "Value": "HyperPodMCPServer"} not in stack.get("Tags", []):
    raise ValueError(stack["StackName"] + " wasn't created by the SageMaker AI MCP server")
await call_boto3(
    service_name="cloudformation",
    operation_name="DeleteStack",
    region_name="us-east-1",
    params={"StackName": stack["StackId"]},
)
result = {"deleting": stack["StackId"]}
result
```

### Environment variables and flags

| Old variable or flag | Replacement |
|----------------------|-------------|
| `AWS_REGION` | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call. The old `manage_hyperpod_cluster_nodes` used `us-east-1` whenever the agent left out `region_name`, whatever `AWS_REGION` said. |
| `AWS_PROFILE`, and `profile_name` on each tool | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | Set them in the proxy's `env` block. The proxy signs requests with the standard AWS credential chain. |
| `FASTMCP_LOG_LEVEL` | Not needed. It set the old server's log level. |
| `--allow-write` | Not available. See Summary of Gaps. |
| `--allow-sensitive-data-access` | Not needed. The server stored the flag, but no tool checked it. |

## What Improves

- **Error reasons reach the agent.** When `describe_hp_cluster` hit a missing cluster, or `manage_hyperpod_cluster_nodes` or `manage_hyperpod_stacks` raised an error for an argument, such as a missing `cluster_name` or a relative `params_file` path, the agent got `Error executing tool <name>` and nothing else. `run_script` returns the service's error code and message, such as `ResourceNotFound` with "Cluster with name ... not found".
- **Full node details.** `describe_node` reported every EBS volume size as `null`, and both node operations dropped `NodeLogicalId` and `ImageVersionStatus`. `call_boto3` returns the full responses, and `DescribeClusterNode` and `BatchDeleteClusterNodes` accept logical node IDs (`NodeLogicalId` and `NodeLogicalIds`).
- **Every page.** `list_clusters` and `list_nodes` returned one page, 10 items unless the agent asked for more. `call_boto3` pages automatically.
- **Regions the old tools refused.** Every tool accepted only 17 Regions. A `list_clusters` call for `ap-northeast-2` failed validation, while `ListClusters` through `call_boto3` answered there.
- **Any stack, with its failure reasons.** `describe` returned only the stack ID, creation time, status, and outputs, and treated a stack without the `CreatedBy=HyperPodMCPServer` tag as an error. `DescribeStacks` returns any stack your credentials can read, with its parameters, tags, and `StackStatusReason`, and `DescribeEvents` lists the failed resources.
- **One profile for every call.** `profile_name` on the node tools changed `AWS_PROFILE` for the whole server process, and a client created for the same Region in the previous 30 minutes kept the earlier profile. `manage_hyperpod_stacks` accepted `profile_name` and never used it. The proxy signs every call with the profile you configure.

## Workflow Change

### Before (Amazon SageMaker AI Server)

1. Start the server with `--allow-write`. Without it, deploy, delete, `update_software`, `batch_delete`, and `update_hp_cluster` refuse to run.
2. To create a cluster, answer the agent's questions one at a time, as the tool's instructions directed, while it writes a parameters file on your machine. Then it calls `manage_hyperpod_stacks` with `operation="deploy"` and the file's absolute path.
3. Check progress with `operation="describe"`, which answers only for stacks the tool tagged.
4. Manage nodes with `manage_hyperpod_cluster_nodes`, and change instance groups with `describe_hp_cluster` and `update_hp_cluster`.

### After (AWS MCP Server)

1. Ask your agent for the HyperPod change. It runs the SageMaker or CloudFormation calls through `run_script` using your credentials.
2. To create a cluster, give the agent the cluster name, Region, Availability Zone IDs, and instance groups. It puts them in the `CreateStack` call, as in the third example.
3. Ask the agent to check the stack with `DescribeStacks` and `DescribeEvents`, and the cluster with `DescribeCluster` and `ListClusterNodes`.
4. Whether a call succeeds is decided by IAM: your identity-based policies, permissions boundaries, and service control policies (SCPs).

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Read-only mode by default (`--allow-write` needed for deploy, delete, `update_software`, `batch_delete`, and `update_hp_cluster`) | Not available | Run with credentials that allow only `sagemaker:ListClusters`, `sagemaker:ListClusterNodes`, `sagemaker:DescribeCluster`, `sagemaker:DescribeClusterNode`, and `cloudformation:DescribeStacks`, or deny `sagemaker:UpdateCluster`, `sagemaker:UpdateClusterSoftware`, `sagemaker:BatchDeleteClusterNodes`, `cloudformation:CreateStack`, `cloudformation:UpdateStack`, and `cloudformation:DeleteStack` with a permissions boundary or SCP |
| Stack ownership check: update, describe, and delete only stacks tagged `CreatedBy=HyperPodMCPServer` | Changed | The agent checks the tag with `DescribeStacks` before `UpdateStack` or `DeleteStack`, as in the fifth example. To enforce it, allow `cloudformation:UpdateStack` and `cloudformation:DeleteStack` only with the condition `aws:ResourceTag/CreatedBy` equal to `HyperPodMCPServer`. |
| Template URL picked from `cluster_orchestrator` | Changed | Use the EKS or Slurm template URL from this guide. To allow only those templates, use the `cloudformation:TemplateUrl` condition key on `cloudformation:CreateStack` and `cloudformation:UpdateStack`. |
| Parameters read from a JSON file on your machine | Changed | The agent reads the file with its own file tools and puts the parameter list in the `run_script` code |
| Path checks on `params_file` (an absolute path, outside `~/.aws`, `~/.ssh`, `~/.gnupg`, `~/.docker`, and `/proc`, and not a file such as `.env` or `credentials`) | Not needed | `run_script` can't read files on your machine. Your MCP client's approvals decide which files the agent reads. |
| Step-by-step parameter questions in the tool's instructions (cluster name, a random resource name prefix, four Availability Zone IDs, the FSx Availability Zone, instance groups, and Karpenter autoscaling) | Not available | Start from the third example, or ask the agent to list the template's parameters with `GetTemplateSummary` and fill in the ones you want |
| `OnFailure="DELETE"` and the `CreatedBy` tag on every new stack | Changed | Pass them in `CreateStack`, as in the third example. With `OnFailure="DELETE"`, CloudFormation removes a failed stack. Use `OnFailure="ROLLBACK"` to keep it for inspection. |
| Instructions for `update_hp_cluster` (describe the cluster first, copy each instance group, set `InstanceCount`, and add `ScheduledUpdateConfig` for scheduled updates) | Not available | `DescribeCluster` returns fields `UpdateCluster` doesn't accept, such as `CurrentCount`, `TargetCount`, and `Status`. Ask the agent to copy the other instance group settings into the `UpdateCluster` call and set `InstanceCount`. |
| Errors returned as a JSON object in the tool result | Changed | `run_script` reports the API's error code and message in its response |

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.sagemaker-ai-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.sagemaker-ai-mcp-server`
3. The old package will remain on PyPI but won't receive updates
