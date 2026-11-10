# Migration Guide: AWS Well-Architected Security Assessment Tool MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.well-architected-security-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The Well-Architected Security server registered 6 tools and 3 prompts, and every tool only read from AWS. `CheckSecurityServices` and `GetSecurityFindings` read the status and findings of Amazon GuardDuty, AWS Security Hub CSPM, Amazon Inspector, IAM Access Analyzer, Amazon Macie, and AWS Trusted Advisor (through the AWS Support API). `CheckStorageEncryption` and `CheckNetworkSecurity` listed resources in Amazon S3, Amazon EBS, Amazon RDS, Amazon DynamoDB, Amazon EFS, Amazon ElastiCache, Elastic Load Balancing, Amazon VPC, Amazon API Gateway, and Amazon CloudFront, read their encryption and TLS settings, and marked each resource compliant or non-compliant. `ListServicesInRegion` counted resources by service with an AWS Resource Explorer search. `GetStoredSecurityContext` returned an earlier `CheckSecurityServices` result from the server's memory without calling AWS. The AWS MCP Server makes the same read calls through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials.

Two Agent Skills in the Agent Toolkit for AWS cover parts of this server's job:

- [`aws-security`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-security) covers the security services. It has read-only configuration and findings procedures for GuardDuty, Inspector, Security Hub and Security Hub CSPM, Macie, Amazon Detective, and Amazon Security Lake, an IAM Access Analyzer check in its coverage review, and rules such as listing GuardDuty attack sequence findings first.
- [`aws-well-architected-review`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-well-architected-review) runs a Well-Architected Framework review, including the Security pillar, from a workload's code, infrastructure as code, and configuration files, and cites a framework best practice for each finding. It doesn't call AWS APIs to read resource settings, so the storage and network checks move to `run_script` calls.

Neither skill covers Trusted Advisor.

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

Set `AWS_REGION` to the Region you want to check. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

### Installing the Agent Skills

```bash
npx skills add aws/agent-toolkit-for-aws/skills
```

This installs the `aws-security` and `aws-well-architected-review` skills along with the other core skills. An agent connected to the AWS MCP Server can also load either one with the server's `retrieve_skill` tool.

### Permissions

Your identity needs the read permissions the old server used:

- GuardDuty: `guardduty:ListDetectors`, `guardduty:GetDetector`, `guardduty:ListFindings`, and `guardduty:GetFindings`
- Security Hub CSPM: `securityhub:DescribeHub`, `securityhub:GetEnabledStandards`, and `securityhub:GetFindings`
- Inspector: `inspector2:BatchGetAccountStatus` and `inspector2:ListFindings`
- IAM Access Analyzer: `access-analyzer:ListAnalyzers` and `access-analyzer:ListFindings`
- Macie: `macie2:GetMacieSession`, `macie2:ListFindings`, and `macie2:GetFindings`
- Trusted Advisor: `support:DescribeTrustedAdvisorChecks` and `support:DescribeTrustedAdvisorCheckResult`, which also need a Business Support plan or higher
- Storage: `s3:ListAllMyBuckets`, `s3:GetBucketLocation`, `s3:GetEncryptionConfiguration`, `s3:GetBucketPublicAccessBlock`, `ec2:DescribeVolumes`, `rds:DescribeDBInstances`, `dynamodb:ListTables`, `dynamodb:DescribeTable`, `elasticfilesystem:DescribeFileSystems`, and `elasticache:DescribeCacheClusters`
- Network: `elasticloadbalancing:DescribeLoadBalancers`, `elasticloadbalancing:DescribeLoadBalancerPolicies`, `elasticloadbalancing:DescribeListeners`, `ec2:DescribeVpcEndpoints`, `ec2:DescribeSecurityGroups`, `apigateway:GET`, `cloudfront:ListDistributions`, and `cloudfront:GetDistribution`
- Resource Explorer: `resource-explorer-2:ListViews`, `resource-explorer-2:ListResources`, and `resource-explorer-2:Search`

The examples below also use `kms:DescribeKey`, `ec2:GetEbsEncryptionByDefault`, and `s3:GetAccountPublicAccessBlock`. The AWS managed policy `SecurityAudit` grants all of these except `macie2:GetMacieSession`, `macie2:GetFindings`, and the `resource-explorer-2` actions.

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

With the AWS MCP Server, ask your agent for the same check and it makes the equivalent calls through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. `call_boto3` pages list operations automatically.

For example, the agent might run this in place of `CheckSecurityServices`:

```python
async def read(service, operation, params=None):
    try:
        return await call_boto3(service_name=service, operation_name=operation, region_name="us-east-1", params=params or {})
    except Exception as e:
        return {"error": e.response["Error"]["Code"]}

detectors = await read("guardduty", "ListDetectors")
hub = await read("securityhub", "DescribeHub")
inspector = await read("inspector2", "BatchGetAccountStatus")
analyzers = await read("accessanalyzer", "ListAnalyzers")
macie = await read("macie2", "GetMacieSession")
advisor = await read("support", "DescribeTrustedAdvisorChecks", {"language": "en"})
result = {
    "guardduty": "enabled" if detectors.get("DetectorIds") else "not enabled",
    "securityhub": "enabled" if "HubArn" in hub else hub["error"],
    "inspector": inspector["accounts"][0]["resourceState"] if "accounts" in inspector else inspector["error"],
    "accessanalyzer": [(a["name"], a["type"], a["status"]) for a in analyzers.get("analyzers", [])],
    "macie": macie.get("status", macie.get("error")),
    "trustedadvisor": len(advisor["checks"]) if "checks" in advisor else advisor["error"],
}
result
```

### Security service status and findings

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `CheckSecurityServices(region, services, account_id, aws_profile, store_in_context, debug)` | For each service in `services` (all six by default): GuardDuty `ListDetectors` and `GetDetector` on the first detector; Inspector `BatchGetAccountStatus`, after a `get_status` call that always failed because the Inspector client has no such operation; IAM Access Analyzer `ListAnalyzers` and one `ListFindings` page per analyzer for a count; Security Hub `DescribeHub` and `GetEnabledStandards`; Trusted Advisor `DescribeTrustedAdvisorChecks` in `us-east-1`; Macie `GetMacieSession`. Returned an `enabled` flag per service and a summary line, plus timings while `debug` was on (the default). Ignored `account_id`. With `store_in_context` on (the default), kept the result in server memory. | `run_script` with the same calls, as in the example above. Inspector's status is `accounts[0].state.status` in the `BatchGetAccountStatus` response, and each scan type's is under `resourceState`. |
| `GetSecurityFindings(service="guardduty")` | Ran the GuardDuty status check, then called `ListFindings` with `MaxResults` set to `max_findings` (default 100) and, with no `severity_filter`, the criteria severity equal to 5, 7, or 8 and updated in the last 30 days. Then `GetFindings` on the IDs, with counts by severity, type, and resource type. A `severity_filter` replaced those criteria with severity equal to 1, 2, or 3 (`LOW`), 4, 5, or 6 (`MEDIUM`), 7 or 8 (`HIGH`), or 8 (`CRITICAL`), and dropped the 30-day window. GuardDuty's `ListFindings` takes at most 50 results, so the call failed with `BadRequestException` unless you passed `max_findings` of 50 or less. | `ListFindings` with a `GreaterThanOrEqual` severity criterion, `service.archived` set to `false`, and `MaxResults` up to 50, then `GetFindings`, as in the example below |
| `GetSecurityFindings(service="securityhub")` | Ran the Security Hub status check, then called `GetFindings` with `MaxResults` set to `max_findings` and, with no `severity_filter`, the filters `RecordState` `ACTIVE`, `WorkflowStatus` `NEW`, `UpdatedAt` in the last 30 days, and `SeverityLabel` `HIGH` or `CRITICAL`. A `severity_filter` replaced all four with one `SeverityLabel` filter. Added counts by severity, product, and resource type. | `call_boto3(service_name="securityhub", operation_name="GetFindings", params={"Filters": {"RecordState": [...], "WorkflowStatus": [...], "SeverityLabel": [...]}, "MaxResults": 100})` |
| `GetSecurityFindings(service="inspector")` | Ran the Inspector status check, then called `ListFindings` with a `filterCriteria` key named `severities`. The API's key is `severity`, so botocore rejected every call with a parameter validation error. | `call_boto3(service_name="inspector2", operation_name="ListFindings", params={"filterCriteria": {"severity": [{"comparison": "EQUALS", "value": "HIGH"}, {"comparison": "EQUALS", "value": "CRITICAL"}], "findingStatus": [{"comparison": "EQUALS", "value": "ACTIVE"}]}, "maxResults": 100})` |
| `GetSecurityFindings(service="accessanalyzer")` | Ran the Access Analyzer status check, then looked up each analyzer's ARN in the status summary it had just built. That summary doesn't keep ARNs, so the tool skipped every analyzer and returned "No IAM Access Analyzer findings found" whether or not findings existed. Ignored `max_findings` and `severity_filter`. | `call_boto3(service_name="accessanalyzer", operation_name="ListFindingsV2", params={"analyzerArn": ..., "filter": {"status": {"eq": ["ACTIVE"]}}})` for each analyzer from `ListAnalyzers` |
| `GetSecurityFindings(service="trustedadvisor")` | Called `DescribeTrustedAdvisorChecks`, kept the checks in the `security` category, called `DescribeTrustedAdvisorCheckResult` for up to `max_findings` of them, and returned the ones with status `error` or `warning` (or the `severity_filter` value) with their flagged resources. Without a Business Support plan or higher, the status check failed with an `AttributeError` naming `SubscriptionRequiredException`, and the tool reported Trusted Advisor as not enabled. | `run_script` combining `call_boto3(service_name="support", operation_name="DescribeTrustedAdvisorChecks", region_name="us-east-1", params={"language": "en"})` and `DescribeTrustedAdvisorCheckResult` with each security check's `checkId` |
| `GetSecurityFindings(service="macie")` | Ran the Macie status check, then called `ListFindings` with `maxResults` set to `max_findings` (default 100) and the criterion `severity.score` greater than 7, then `GetFindings`. Macie takes at most 50 results and doesn't accept `severity.score` as a criterion, so every call failed with `ValidationException`. `severity_filter` had no effect. | `call_boto3(service_name="macie2", operation_name="ListFindings", params={"findingCriteria": {"criterion": {"severity.description": {"eq": ["High"]}}}, "maxResults": 50})`, then `GetFindings` with the IDs |
| `GetStoredSecurityContext(region, detailed)` | Returned the `CheckSecurityServices` result kept in server memory for the Region, without calling AWS. The memory was lost when the server restarted. | No equivalent. The agent keeps earlier `run_script` results in the conversation, or runs the status script again. |

Before querying, `GetSecurityFindings` read the stored `CheckSecurityServices` result (`check_enabled`, on by default) and answered "not enabled" for a service marked disabled there. Each finding path then ran its service's status check again.

To list active High and Critical GuardDuty findings, most severe first, the agent might run:

```python
detector = (await call_boto3(service_name="guardduty", operation_name="ListDetectors", region_name="us-east-1"))["DetectorIds"][0]
listed = await call_boto3(
    service_name="guardduty",
    operation_name="ListFindings",
    region_name="us-east-1",
    params={
        "DetectorId": detector,
        "FindingCriteria": {"Criterion": {
            "severity": {"GreaterThanOrEqual": 7},
            "service.archived": {"Eq": ["false"]},
        }},
        "SortCriteria": {"AttributeName": "severity", "OrderBy": "DESC"},
        "MaxResults": 50,
    },
)
findings = []
if listed["FindingIds"]:
    got = await call_boto3(
        service_name="guardduty",
        operation_name="GetFindings",
        region_name="us-east-1",
        params={
            "DetectorId": detector,
            "FindingIds": listed["FindingIds"][:50],
            "SortCriteria": {"AttributeName": "severity", "OrderBy": "DESC"},
        },
    )
    findings = [{"severity": f["Severity"], "type": f["Type"], "resource": f["Resource"]["ResourceType"], "updated": f["UpdatedAt"]} for f in got["Findings"]]
result = findings
result
```

GuardDuty's Critical range is 9.0 to 10.0 and its High range starts at 7.0 (see [Severity levels of GuardDuty findings](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings-severity.html)), so a range criterion catches both. The `service.archived` criterion keeps only active findings, as the `aws-security` skill's GuardDuty findings procedure does.

The example has no `updatedAt` window. The old tool's 30-day window hides active findings that haven't been updated in that time. In testing, this query returned 9 findings with the 9.0 `AttackSequence:EC2/CompromisedInstanceGroup` finding first, and with a 30-day `updatedAt` criterion it returned 8 and missed that finding, which was last updated 53 days earlier.

### Storage encryption

`CheckStorageEncryption(region, services, include_unencrypted_only, aws_profile, store_in_context)` started with Resource Explorer `ListViews`, looking for a default view. `ListViews` returns view ARNs as strings, and the tool read each one as a dictionary, so in any Region with a Resource Explorer view the whole tool failed with `'str' object has no attribute 'get'`. In a Region with no view, it read each service in `services` (all six by default) directly, as below, and returned counts, per-resource details, and a fixed list of recommendations.

| `services` entry | What it did | Replacement |
|------------------|-------------|-------------|
| `s3` | `ListBuckets`, then `GetBucketLocation` on every bucket in the account to keep the ones in the Region, then `GetBucketEncryption` and `GetPublicAccessBlock` on each. A bucket with no bucket-level public access block configuration was marked non-compliant ("Public access block status unknown"), and the account-level setting wasn't read. | `call_boto3(service_name="s3", operation_name="ListBuckets", region_name=<region>, params={"BucketRegion": <region>})`, then `GetBucketEncryption` and `GetPublicAccessBlock` on each bucket, and `call_boto3(service_name="s3control", operation_name="GetPublicAccessBlock", params={"AccountId": ...})` for the account-level setting |
| `ebs` | `DescribeVolumes`, marking unencrypted volumes non-compliant. Its `using_cmk` check compared the key ARN with the literal prefix `arn:aws:kms:region:aws:`, so every encrypted volume showed `using_cmk: true`, including volumes on the AWS managed `aws/ebs` key. | `DescribeVolumes`, `kms` `DescribeKey` on each `KmsKeyId` (`KeyManager` is `AWS` or `CUSTOMER`), and `GetEbsEncryptionByDefault`, as in the example below |
| `rds` | `DescribeDBInstances`, then `DescribeDBInstances` for each instance, marking instances with `StorageEncrypted` set to false non-compliant. Used the same `using_cmk` check as `ebs`. | `call_boto3(service_name="rds", operation_name="DescribeDBInstances")`, and `DescribeKey` on each `KmsKeyId` |
| `dynamodb` | `ListTables`, then `DescribeTable` twice for each table. A table on the default AWS owned key has no `SSEDescription`, and the tool marked it "DynamoDB table is not encrypted". DynamoDB encrypts every table at rest. | `ListTables` and `DescribeTable`, where a missing `SSEDescription` means the AWS owned key, as in the example below |
| `efs` | `DescribeFileSystems`, marking unencrypted file systems non-compliant. Used the same `using_cmk` check as `ebs`, so file systems on the AWS managed `aws/elasticfilesystem` key showed `using_cmk: true`. | `call_boto3(service_name="efs", operation_name="DescribeFileSystems")`, and `DescribeKey` on each `KmsKeyId` |
| `elasticache` | `DescribeCacheClusters`. Checked at-rest encryption, in-transit encryption, and AUTH for Redis OSS clusters, and marked every Memcached cluster non-compliant ("Memcached does not support encryption") even with in-transit encryption on. Valkey clusters got no checks and counted as compliant. Serverless caches weren't listed. | `DescribeCacheClusters` and `DescribeReplicationGroups` (`AtRestEncryptionEnabled`, `TransitEncryptionEnabled`), and `DescribeServerlessCaches` |

To read EBS and DynamoDB encryption the way AWS reports it, the agent might run:

```python
region = "us-east-1"
key_managers = {}

async def key_manager(key_id):
    if key_id not in key_managers:
        key = await call_boto3(service_name="kms", operation_name="DescribeKey", region_name=region, params={"KeyId": key_id})
        key_managers[key_id] = key["KeyMetadata"]["KeyManager"]
    return key_managers[key_id]

volumes = (await call_boto3(service_name="ec2", operation_name="DescribeVolumes", region_name=region))["Volumes"]
default = await call_boto3(service_name="ec2", operation_name="GetEbsEncryptionByDefault", region_name=region)
result = {"ebs_encryption_by_default": default["EbsEncryptionByDefault"], "ebs": [], "dynamodb": {}}
for v in volumes:
    result["ebs"].append({"id": v["VolumeId"], "encrypted": v["Encrypted"], "key": (await key_manager(v["KmsKeyId"])) if v.get("KmsKeyId") else None})
for name in (await call_boto3(service_name="dynamodb", operation_name="ListTables", region_name=region))["TableNames"]:
    table = (await call_boto3(service_name="dynamodb", operation_name="DescribeTable", region_name=region, params={"TableName": name}))["Table"]
    sse = table.get("SSEDescription")
    result["dynamodb"][name] = "AWS owned key" if sse is None else sse["SSEType"]
result
```

### Network security

`CheckNetworkSecurity(region, services, include_non_compliant_only, aws_profile, store_in_context)` started with the same `ListViews` lookup and failed the same way in any Region with a Resource Explorer view. In a Region with no view, it read each service in `services` (all four by default) directly, as below.

| `services` entry | What it did | Replacement |
|------------------|-------------|-------------|
| `elb` | Classic Load Balancers: one page of `DescribeLoadBalancers`, then `DescribeLoadBalancers` and `DescribeLoadBalancerPolicies` for each, marking any HTTP or TCP listener non-compliant and flagging policies that enabled TLS 1.1 or SSLv3. It looked for a `TLSv1.0` protocol attribute, and the attribute for TLS 1.0 is `Protocol-TLSv1`, so TLS 1.0 wasn't flagged. Application and Network Load Balancers: one page of `DescribeLoadBalancers` and `DescribeListeners` for each. An Application Load Balancer with any HTTP listener was non-compliant, including one that only redirects to HTTPS, and any HTTPS or TLS listener whose policy name didn't start with `ELBSecurityPolicy-TLS-1-2` or `ELBSecurityPolicy-FS-1-2` was flagged as potentially insecure. That flagged every `ELBSecurityPolicy-TLS13-*` policy. | `call_boto3(service_name="elb", operation_name="DescribeLoadBalancers")` with `DescribeLoadBalancerPolicies`, and `call_boto3(service_name="elbv2", operation_name="DescribeLoadBalancers")` with `DescribeListeners`. Check each listener's `DefaultActions` for a redirect, and compare `SslPolicy` with [Security policies for your Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/describe-ssl-policies.html). |
| `vpc` | `DescribeVpcEndpoints`, then `DescribeVpcEndpoints` for each endpoint, marking interface endpoints without private DNS non-compliant. Then `DescribeSecurityGroups`, and `DescribeSecurityGroups` for each group, marking a group non-compliant when a rule opened port 20, 21, 23, 25, 69, 80, 110, or 143 to `0.0.0.0/0`. It skipped rules with no port range, so an all-traffic rule (`IpProtocol` `-1`) open to `0.0.0.0/0` counted as compliant, and it didn't read IPv6 ranges such as `::/0`. | `call_boto3(service_name="ec2", operation_name="DescribeVpcEndpoints")`, and `DescribeSecurityGroups` with every rule checked, as in the example below |
| `apigateway` | One page of `GetRestApis` (25 APIs by default), then `GetRestApi`, `GetStages`, `GetDomainNames`, and `GetBasePathMappings`. Marked every stage "HTTPS not enforced" unless its `*/*` method settings had `requireHttps`, a field API Gateway doesn't have; API Gateway exposes HTTPS endpoints only. Flagged any custom domain whose security policy wasn't exactly `TLS_1_2`, including TLS 1.3 policies. Didn't check HTTP or WebSocket APIs. | `call_boto3(service_name="apigateway", operation_name="GetRestApis", params={"limit": 500})`, `GetStages`, and `GetDomainNames` (`securityPolicy`), and `call_boto3(service_name="apigatewayv2", operation_name="GetApis")` for HTTP and WebSocket APIs |
| `cloudfront` | Ran only when `region` was `us-east-1`. One page of `ListDistributions`, then `GetDistribution` for each. Checked the default cache behavior's viewer protocol policy but not the other cache behaviors, flagged any minimum protocol version other than `TLSv1.2_2018`, `TLSv1.2_2019`, and `TLSv1.2_2021` (so `TLSv1.2_2025` and `TLSv1.3_2025` were flagged), and checked S3 origins for an OAI or OAC. The OAC check passed whenever the origin had an `OriginAccessControlId` key, and CloudFront returns that key as an empty string when no OAC is set. | `call_boto3(service_name="cloudfront", operation_name="ListDistributions", region_name="us-east-1")` and `GetDistribution`. Check `ViewerProtocolPolicy` on the default and every other cache behavior, `ViewerCertificate.MinimumProtocolVersion`, and a non-empty `OriginAccessControlId` or `OriginAccessIdentity` on each S3 origin. |

To find security group rules open to the internet over IPv4 or IPv6, the agent might run:

```python
groups = (await call_boto3(service_name="ec2", operation_name="DescribeSecurityGroups", region_name="us-east-1"))["SecurityGroups"]
open_rules = []
for group in groups:
    for rule in group["IpPermissions"]:
        sources = [r["CidrIp"] for r in rule.get("IpRanges", []) if r["CidrIp"] == "0.0.0.0/0"]
        sources += [r["CidrIpv6"] for r in rule.get("Ipv6Ranges", []) if r["CidrIpv6"] == "::/0"]
        if sources:
            open_rules.append({
                "group": group["GroupId"],
                "protocol": "all" if rule["IpProtocol"] == "-1" else rule["IpProtocol"],
                "ports": "all" if rule.get("FromPort", -1) == -1 else str(rule["FromPort"]) + "-" + str(rule["ToPort"]),
                "sources": sources,
            })
result = open_rules
result
```

Security Hub CSPM controls evaluate many of the same settings continuously, with a pass or fail result for each resource. To read the failed ones, the agent might run:

```python
controls = ["S3.1", "EC2.7", "EFS.1", "RDS.3", "ELB.17", "CloudFront.3", "APIGateway.11", "EC2.19"]
found = await call_boto3(
    service_name="securityhub",
    operation_name="GetFindings",
    region_name="us-east-1",
    params={
        "Filters": {
            "ComplianceSecurityControlId": [{"Comparison": "EQUALS", "Value": c} for c in controls],
            "ComplianceStatus": [{"Comparison": "EQUALS", "Value": "FAILED"}],
            "RecordState": [{"Comparison": "EQUALS", "Value": "ACTIVE"}],
        },
        "MaxResults": 100,
    },
)
result = [{"control": f["Compliance"]["SecurityControlId"], "resource": f["Resources"][0]["Id"], "title": f["Title"]} for f in found["Findings"]]
result
```

A control reports findings only when it's enabled in Security Hub CSPM.

### Resource discovery

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `ListServicesInRegion(region, aws_profile, store_in_context)` | Resource Explorer `Search` with `QueryString="*"`, then every page of the same search, counting resources by the service named in each ARN. A search returns at most 1,000 resources, so the total stopped at 1,000 without saying so. Called from a Region that holds an aggregator index, the search covered every Region: in testing, 499 of the 1,000 resources it counted for `us-east-1` were in `us-east-1`. | `Search` with a `region:` query, as in the example below. `Count.Complete` is `false` when more than 1,000 resources match; a narrower query such as `region:us-east-1 service:ec2` counts one service. |

```python
found = await call_boto3(
    service_name="resource-explorer-2",
    operation_name="Search",
    region_name="us-east-1",
    params={"QueryString": "region:us-east-1", "MaxResults": 1000},
)
services = {}
for r in found["Resources"]:
    services[r["Service"]] = services.get(r["Service"], 0) + 1
result = {"count": found["Count"], "services": services}
result
```

### Prompts

| Old prompt | What it did | Replacement |
|------------|-------------|-------------|
| `wa-sec-check-findings` | Returned text on calling `CheckSecurityServices` and then `GetSecurityFindings` for each enabled service | The `aws-security` skill's configuration and findings procedures |
| `wa-sec-check-storage` | Returned text on listing services with `ListServicesInRegion` or `ListResourceTypes`, then calling `CheckStorageEncryption` | The storage example above, the Security Hub CSPM controls example, or `aws-well-architected-review` for a review of the workload's code |
| `wa-sec-check-network` | The same steps, with `CheckNetworkSecurity` | The security group and Security Hub CSPM controls examples above, or `aws-well-architected-review` |

The server's instructions also described `GetResourceComplianceStatus` and `ExploreAwsResources`, and the storage and network prompts called `ListResourceTypes`. The server didn't register any of the three.

### Environment variables

| Old variable | Replacement |
|--------------|-------------|
| `AWS_REGION` (default `us-east-1`) | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call |
| `AWS_PROFILE` (default `default`) | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |
| `FASTMCP_LOG_LEVEL` | Not needed; it set the old server's log level |
| `--sse` and `--port` command-line options | Not needed; the proxy runs over stdio and reaches the AWS MCP Server over HTTPS |

## What Improves

- **A configuration that starts.** The server README's JSON configuration runs `uvx --from awslabs.well-architected-security-mcp-server well-architected-security-mcp-server`, and the package's only executable is `awslabs.well-architected-security-mcp-server`, so the server never started from that block. In testing, the client reported "Connection closed" and no tools. The proxy configuration above runs `mcp-proxy-for-aws-cli`, the executable its package provides.
- **Credentials from the default chain.** Every tool opened its AWS session with the profile named `default` when `aws_profile` wasn't set, including when it was passed as `null`. With no `[default]` profile, as on an EC2 instance role, in a container, or with only named profiles, every AWS call failed with "The config profile (default) could not be found". The proxy uses the standard AWS credential chain, or the profile in `AWS_MCP_PROXY_PROFILES`.
- **Storage and network checks in Regions with a Resource Explorer view.** `CheckStorageEncryption` and `CheckNetworkSecurity` failed with `'str' object has no attribute 'get'` in any Region with a Resource Explorer view. In testing, `us-east-1` had one, so neither tool returned a result there, and `CheckNetworkSecurity` reads CloudFront only from `us-east-1`. `run_script` reads each service's own API and doesn't need Resource Explorer.
- **GuardDuty findings, including Critical ones.** With the default `max_findings` of 100, every GuardDuty request failed with `BadRequestException` ("The request is rejected because the parameter maxResults is out-of-bounds."). The severity filters matched exact values (5, 7, or 8 by default, and 8 for `CRITICAL`), so no filter matched a Critical finding. In testing, `severity_filter="HIGH"` returned 8 findings and missed a 9.0 `AttackSequence:EC2/CompromisedInstanceGroup` finding that a `GreaterThanOrEqual: 7` criterion returned.
- **Macie, Inspector, and IAM Access Analyzer findings.** Every Macie request failed with `ValidationException`, and every Inspector request failed parameter validation. `CheckSecurityServices` reported Inspector as enabled in an account where `BatchGetAccountStatus` reported `DISABLED`, and the Access Analyzer path never queried an analyzer. Through `call_boto3`, a Macie `ListFindings` call on `severity.description` returned 5 High findings in testing, and `BatchGetAccountStatus` shows Inspector's state for the account and for each scan type.
- **Encryption reported as AWS reports it.** The old tool marked a DynamoDB table on the default AWS owned key as not encrypted, reported EBS volumes and EFS file systems on the AWS managed `aws/ebs` and `aws/elasticfilesystem` keys as using a customer managed key, and marked every API Gateway REST API stage "HTTPS not enforced". With `DescribeTable` and `kms` `DescribeKey`, the agent sees which key protects each resource.
- **TLS 1.3 policies and every security group rule.** The old checks flagged the `ELBSecurityPolicy-TLS13-*` load balancer policies, CloudFront's `TLSv1.2_2025` and `TLSv1.3_2025`, and API Gateway's TLS 1.3 domain policies as insecure. They passed security group rules that allow all traffic from `0.0.0.0/0` or open a port to `::/0`, and they didn't read CloudFront cache behaviors other than the default, which skipped an `allow-all` behavior on a distribution in testing. The agent reads the policy names and every rule and behavior as AWS returns them.
- **Error messages reach the agent.** `GetSecurityFindings` re-raised errors, so the client saw only "Error executing tool GetSecurityFindings", and a missing support plan came back as an `AttributeError`. `run_script` returns the service's error code and message, such as `SubscriptionRequiredException: Amazon Web Services Premium Support Subscription is required to use this service.`
- **A clean stdio channel.** The old server printed debug lines to standard output, which carries the MCP messages for a stdio server, and the test client logged "Failed to parse JSONRPC message from server" in each session.

## Workflow Change

### Before (AWS Well-Architected Security Assessment Tool Server)

1. Set up a `[default]` AWS profile, or pass `aws_profile` on every call.
2. Call `CheckSecurityServices`, then `GetSecurityFindings` for each enabled service. The server kept the first result in memory for the second.
3. Call `CheckStorageEncryption` and `CheckNetworkSecurity` in a Region without a Resource Explorer view, and read the server's compliant and non-compliant verdicts and fixed recommendations.

### After (AWS MCP Server)

1. Ask your agent for the security service status or findings. It runs the calls through `run_script` with your credentials, and the `aws-security` skill guides which calls to make and how to order the findings.
2. For storage and network settings, the agent reads them with each service's API and reports them as AWS returns them. For continuous pass and fail results, read the Security Hub CSPM control findings.
3. For a review of a workload against the Well-Architected Framework, use the `aws-well-architected-review` skill on the workload's code and infrastructure as code.

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Read-only by design (the server had no tools that change resources) | Not available | Run with credentials that only read, such as the `SecurityAudit` managed policy plus `macie2:GetMacieSession`, `macie2:GetFindings`, and the `resource-explorer-2` read actions, or deny write actions with a permissions boundary or SCP |
| Compliant and non-compliant verdicts, with fixed remediation text, for storage and network resources | Not available | Security Hub CSPM controls such as `S3.1`, `S3.8`, `EC2.3`, `EC2.7`, `RDS.3`, `EFS.1`, `ElastiCache.4`, `ElastiCache.5`, `ELB.1`, `ELB.3`, `ELB.17`, `ELB.18`, `CloudFront.3`, `CloudFront.13`, `CloudFront.15`, `APIGateway.11`, `EC2.18`, `EC2.19`, `EC2.53`, and `EC2.54` evaluate the same settings; read their findings as in the example above. Or ask the agent to apply your own criteria to the settings it reads. |
| All six service statuses in one tool call | Changed | One `run_script`, as in the first example |
| Results kept in server memory (`store_in_context`, `GetStoredSecurityContext`, and `check_enabled` in `GetSecurityFindings`) | Not available | The agent keeps earlier results in the conversation, or runs the status script again |
| Default finding filters (30 days, High and Critical, and `ACTIVE` and `NEW` for Security Hub) | Changed | The agent sets the filters in each call; the tables above list the old defaults |
| Counts by severity, finding type, and resource type | Changed | Ask the agent to count in the same `run_script` |
| Setup instructions for services that aren't enabled | Not available | The `aws-security` skill and each service's documentation |
| Trusted Advisor security checks | Changed | No Agent Skill covers Trusted Advisor; the agent calls the same AWS Support API operations through `run_script`, and they still need a Business Support plan or higher |

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.well-architected-security-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.well-architected-security-mcp-server`
3. The old package will remain on PyPI but won't receive updates
