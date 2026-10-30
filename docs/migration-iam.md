# Migration Guide: IAM MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.iam-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The IAM MCP Server wrapped 29 individual IAM API operations as separate MCP tools. The AWS MCP Server covers all of them, and the rest of the IAM API, through a single `run_script` tool. `run_script` executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. IAM-specific guidance comes from the `aws-iam` Agent Skill, which covers trust policy pitfalls, confused deputy protection, service role creation, condition operator safety, and least-privilege policy generation. You no longer need a separate server for each AWS service.

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
        "AWS_REGION=us-west-2"
      ]
    }
  }
}
```

To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

### Installing the Agent Skills

```bash
npx skills add aws/agent-toolkit-for-aws/skills
```

This installs the [`aws-iam`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-iam) skill along with the other core skills.

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

Every tool in the IAM server was a wrapper around one or more IAM API calls. With the AWS MCP Server, ask your agent to perform the same operation and it will make the equivalent call through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. For example, the agent might run:

```python
resp = await call_boto3(
    service_name="iam",
    operation_name="ListUsers",
)
result = {"users": [{"name": u["UserName"], "arn": u["Arn"]} for u in resp["Users"]]}
result
```

`call_boto3` paginates automatically, so each list operation needs only one call.

### Users

| IAM server tool | IAM API call(s) | How to do it now |
|-----------------|-----------------|------------------|
| `list_users` | `ListUsers` | `run_script` with `call_boto3(service_name="iam", operation_name="ListUsers", params={"PathPrefix": ...})` |
| `get_user` | `GetUser`, `ListAttachedUserPolicies`, `ListUserPolicies`, `ListGroupsForUser`, `ListAccessKeys` | `run_script` combining the same calls |
| `create_user` | `CreateUser` | `run_script` with `call_boto3(service_name="iam", operation_name="CreateUser", params={"UserName": ..., "Path": ..., "PermissionsBoundary": ...})` |
| `delete_user` | `DeleteUser` (with `force=True`: also `RemoveUserFromGroup`, `DetachUserPolicy`, `DeleteUserPolicy`, `DeleteAccessKey` first) | `run_script` that removes group memberships, attached and inline policies, and access keys, then calls `call_boto3(service_name="iam", operation_name="DeleteUser", params={"UserName": ...})` |

### Roles

| IAM server tool | IAM API call(s) | How to do it now |
|-----------------|-----------------|------------------|
| `list_roles` | `ListRoles` | `run_script` with `call_boto3(service_name="iam", operation_name="ListRoles", params={"PathPrefix": ...})` |
| `create_role` | `CreateRole` | `run_script` with `call_boto3(service_name="iam", operation_name="CreateRole", params={"RoleName": ..., "AssumeRolePolicyDocument": ..., "PermissionsBoundary": ...})`. The `aws-iam` skill covers trust policy and confused deputy guidance. |

### Managed policies

| IAM server tool | IAM API call(s) | How to do it now |
|-----------------|-----------------|------------------|
| `list_policies` | `ListPolicies` | `run_script` with `call_boto3(service_name="iam", operation_name="ListPolicies", params={"Scope": ..., "OnlyAttached": ...})` |
| `get_managed_policy_document` | `GetPolicyVersion` | `run_script` with `call_boto3(service_name="iam", operation_name="GetPolicy", params={"PolicyArn": ...})` to find `DefaultVersionId`, then `call_boto3(service_name="iam", operation_name="GetPolicyVersion", params={"PolicyArn": ..., "VersionId": ...})` |
| `attach_user_policy` | `AttachUserPolicy` | `run_script` with `call_boto3(service_name="iam", operation_name="AttachUserPolicy", params={"UserName": ..., "PolicyArn": ...})` |
| `detach_user_policy` | `DetachUserPolicy` | `run_script` with `call_boto3(service_name="iam", operation_name="DetachUserPolicy", params={"UserName": ..., "PolicyArn": ...})` |
| `attach_group_policy` | `AttachGroupPolicy` | `run_script` with `call_boto3(service_name="iam", operation_name="AttachGroupPolicy", params={"GroupName": ..., "PolicyArn": ...})` |
| `detach_group_policy` | `DetachGroupPolicy` | `run_script` with `call_boto3(service_name="iam", operation_name="DetachGroupPolicy", params={"GroupName": ..., "PolicyArn": ...})` |

### Inline policies

| IAM server tool | IAM API call(s) | How to do it now |
|-----------------|-----------------|------------------|
| `put_user_policy` | `PutUserPolicy` | `run_script` with `call_boto3(service_name="iam", operation_name="PutUserPolicy", params={"UserName": ..., "PolicyName": ..., "PolicyDocument": ...})` |
| `get_user_policy` | `GetUserPolicy` | `run_script` with `call_boto3(service_name="iam", operation_name="GetUserPolicy", params={"UserName": ..., "PolicyName": ...})` |
| `delete_user_policy` | `DeleteUserPolicy` | `run_script` with `call_boto3(service_name="iam", operation_name="DeleteUserPolicy", params={"UserName": ..., "PolicyName": ...})` |
| `list_user_policies` | `ListUserPolicies` | `run_script` with `call_boto3(service_name="iam", operation_name="ListUserPolicies", params={"UserName": ...})` |
| `put_role_policy` | `PutRolePolicy` | `run_script` with `call_boto3(service_name="iam", operation_name="PutRolePolicy", params={"RoleName": ..., "PolicyName": ..., "PolicyDocument": ...})` |
| `get_role_policy` | `GetRolePolicy` | `run_script` with `call_boto3(service_name="iam", operation_name="GetRolePolicy", params={"RoleName": ..., "PolicyName": ...})` |
| `delete_role_policy` | `DeleteRolePolicy` | `run_script` with `call_boto3(service_name="iam", operation_name="DeleteRolePolicy", params={"RoleName": ..., "PolicyName": ...})` |
| `list_role_policies` | `ListRolePolicies` | `run_script` with `call_boto3(service_name="iam", operation_name="ListRolePolicies", params={"RoleName": ...})` |

### Groups

| IAM server tool | IAM API call(s) | How to do it now |
|-----------------|-----------------|------------------|
| `list_groups` | `ListGroups` | `run_script` with `call_boto3(service_name="iam", operation_name="ListGroups", params={"PathPrefix": ...})` |
| `get_group` | `GetGroup`, `ListAttachedGroupPolicies`, `ListGroupPolicies` | `run_script` combining the same calls |
| `create_group` | `CreateGroup` | `run_script` with `call_boto3(service_name="iam", operation_name="CreateGroup", params={"GroupName": ..., "Path": ...})` |
| `delete_group` | `DeleteGroup` (with `force=True`: also `RemoveUserFromGroup`, `DetachGroupPolicy`, `DeleteGroupPolicy` first) | `run_script` that removes members, attached and inline policies, then calls `call_boto3(service_name="iam", operation_name="DeleteGroup", params={"GroupName": ...})` |
| `add_user_to_group` | `AddUserToGroup` | `run_script` with `call_boto3(service_name="iam", operation_name="AddUserToGroup", params={"GroupName": ..., "UserName": ...})` |
| `remove_user_from_group` | `RemoveUserFromGroup` | `run_script` with `call_boto3(service_name="iam", operation_name="RemoveUserFromGroup", params={"GroupName": ..., "UserName": ...})` |

### Access keys

| IAM server tool | IAM API call(s) | How to do it now |
|-----------------|-----------------|------------------|
| `create_access_key` | `CreateAccessKey` | `run_script` with `call_boto3(service_name="iam", operation_name="CreateAccessKey", params={"UserName": ...})`. Prefer IAM roles and temporary credentials over long-term access keys. |
| `delete_access_key` | `DeleteAccessKey` | `run_script` with `call_boto3(service_name="iam", operation_name="DeleteAccessKey", params={"UserName": ..., "AccessKeyId": ...})` |

### Policy simulation

| IAM server tool | IAM API call(s) | How to do it now |
|-----------------|-----------------|------------------|
| `simulate_principal_policy` | `SimulatePrincipalPolicy` | `run_script` with `call_boto3(service_name="iam", operation_name="SimulatePrincipalPolicy", params={"PolicySourceArn": ..., "ActionNames": [...], "ResourceArns": [...], "ContextEntries": [...]})` |

Because `run_script` exposes the full IAM API, operations the IAM server never had (for example `AttachRolePolicy`, `UpdateAssumeRolePolicy`, `CreatePolicy`, or `ListAccessKeys`) are also available.

## Workflow Change

### Before (IAM Server)

1. Start the server with `--allow-write`, or every mutating tool fails because the server defaults to read-only mode
2. Call a write tool, which first returns `CONFIRMATION REQUIRED` unless `confirmed=True` is passed
3. After the user approves, call the tool again with `confirmed=True`
4. The server rejects denylisted managed policies, overly broad policy documents, and `Principal: *` trust policies before calling IAM

### After (AWS MCP Server)

1. Ask your agent for the IAM change. The `aws-iam` skill guides it on trust policies, least privilege, and policy generation.
2. The agent runs the IAM API call through `run_script` using your credentials.
3. Whether the call succeeds is decided by IAM itself: your identity-based policies, permissions boundaries, and service control policies (SCPs).

The AWS MCP Server does not re-implement the IAM server's client-side guardrails. Enforce those limits in IAM, as described in the next section.

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Read-only mode by default (writes required `--allow-write`) | Not available | Run with credentials that only grant IAM read actions (for example a role with the `IAMReadOnlyAccess` managed policy), or deny IAM write actions with a permissions boundary or SCP |
| Denylist blocking attachment of `AdministratorAccess`, `IAMFullAccess`, and `PowerUserAccess` (in `attach_user_policy` and `attach_group_policy`) | Not available | Deny `iam:AttachUserPolicy`, `iam:AttachGroupPolicy`, and `iam:AttachRolePolicy` with an `iam:PolicyARN` condition key in a permissions boundary or SCP |
| Rejection of inline policies combining a broad Action (`*`, `service:*`, or `NotAction`) with a broad Resource (`*`, `arn:*`, an ARN ending in `:*`, or `NotResource`), and of privilege-escalation IAM actions on broad resources (in `put_user_policy` and `put_role_policy`) | Not available | Constrain what principals can grant with permissions boundaries and SCPs. Use the `aws-iam` skill to generate least-privilege policies, and validate documents with IAM Access Analyzer policy validation before applying them. |
| Rejection of trust policies with `Principal: "*"` or `Principal: {"AWS": "*"}` (in `create_role`) | Not available | Restrict `iam:CreateRole` and `iam:UpdateAssumeRolePolicy` with SCPs or permissions boundaries, and use the `aws-iam` skill's trust policy and confused deputy guidance (`aws:SourceAccount` / `aws:SourceArn` conditions) |
| Two-phase `confirmed=True` handshake for write operations (disable with `--no-confirmation`) | Not available | Use your MCP client's per-tool approval for `run_script`, and rely on IAM permissions boundaries and SCPs as the enforcement layer |
| Automatic cleanup when deleting users and groups (`force=True`) | Not available | Ask the agent to remove group memberships, policies, and access keys before the delete call in the same `run_script` |

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.iam-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.iam-mcp-server`
3. The old package will remain on PyPI but will not receive updates
