---
id: "SEC04-BP02"
title: "Capture logs, findings, and metrics in standardized locations"
framework: "WAF"
domain: "Security"
capability: "How do you detect and investigate security events?"
risk_level: "Medium"
---

# SEC04-BP02 Capture logs, findings, and metrics in standardized locations

## Desired Outcome
You have a standardized approach to collect, analyze, and visualize log data, findings, and metrics. Security teams can efficiently correlate, analyze, and visualize security data across disparate systems to discover potential security events and identify anomalies. Security information and event management (SIEM) systems or other mechanisms are integrated to query and analyze log data for timely responses, tracking, and escalation of security events.

## Anti-Patterns
- Teams independently own and manage logging and metrics collection that is inconsistent to the organization's logging strategy.
- Teams don't have adequate access controls to restrict visibility and alteration of the data collected.
- Teams don't govern their security logs, findings, and metrics as part of their data classification policy.
- Teams neglect data sovereignty and localization requirements when configuring data collections.

## Implementation Guidance
 Growth in AWS usage within an organization results in a growing number of distributed workloads and environments. As each of these workloads and environments generate data about the activity within them, capturing and storing this data locally presents a challenge for security operations. Security teams use tools such as security information and event management (SIEM) systems to collect data from distributed sources and undergo correlation, analysis, and response workflows. This requires managing a complex set of permissions for accessing the various data sources and additional overhead in operating the extraction, transformation, and loading (ETL) processes.

 To overcome these challenges, consider aggregating all relevant sources of security log data into a Log Archive account as described in [Organizing Your AWS Environment Using Multiple Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/security-ou-and-accounts.html#log-archive-account). This includes all security-related data from your workload and logs that AWS services generate, such as [AWS CloudTrail](https://aws.amazon.com/cloudtrail/), [AWS WAF](https://aws.amazon.com/waf/), [Elastic Load Balancing](https://aws.amazon.com/elasticloadbalancing/), and [Amazon Route 53](https://aws.amazon.com/route53/). There are several benefits to capturing this data in standardized locations in a separate AWS account with proper cross-account permissions. This practice helps prevent log tampering within compromised workloads and environments, provides a single integration point for additional tools, and offers a more simplified model for configuring data retention and lifecycle.  Evaluate the impacts of data sovereignty, compliance scopes, and other regulations to determine if multiple security data storage locations and retention periods are required.

 To ease capturing and standardizing logs and findings, evaluate [Amazon Security Lake](https://docs.aws.amazon.com/security-lake/latest/userguide/what-is-security-lake.html) in your Log Archive account. You can configure Security Lake to automatically ingest data from common sources such as CloudTrail, Route 53, [Amazon EKS](https://aws.amazon.com/eks/), and [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html). You can also configure AWS Security Hub as a data source into Security Lake, allowing you to correlate findings from other AWS services, such as [Amazon GuardDuty](https://aws.amazon.com/guardduty/) and [Amazon Inspector](https://aws.amazon.com/inspector/), with your log data.  You can also use third-party data source integrations, or configure custom data sources. All integrations standardize your data into the [Open Cybersecurity Schema Framework](https://github.com/ocsf) (OCSF) format, and are stored in [Amazon S3](https://aws.amazon.com/s3/) buckets as Parquet files, eliminating the need for ETL processing.

 Storing security data in standardized locations provides advanced analytics capabilities.  AWS recommends you deploy tools for security analytics that operate in an AWS environment into a [Security Tooling](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/security-ou-and-accounts.html#security-tooling-accounts) account that is separate from your Log Archive account. This approach allows you to implement controls at depth to protect the integrity and availability of the logs and log management process, distinct from the tools that access them.  Consider using services, such as [Amazon Athena](https://aws.amazon.com/athena/), to run on-demand queries that correlate multiple data sources. You can also integrate visualization tools, such as [Quick Suite](https://aws.amazon.com/quicksight/). AI-powered solutions are becoming increasingly available and can perform functions such as translating findings into human-readable summaries and natural language interaction. These solutions are often more readily integrated by having a standardized data storage location for querying.

## Implementation Steps
1.  **Create the Log Archive and Security Tooling accounts**

   1.  Using AWS Organizations, [create the Log Archive and Security Tooling accounts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_create.html) under a security organizational unit. If you are using AWS Control Tower to manage your organization, the Log Archive and Security Tooling accounts are created for you automatically. Configure roles and permissions for accessing and administering these accounts as required.

1.  **Configure your standardized security data locations**

   1.  Determine your strategy for creating standardized security data locations.  You can achieve this through options like common data lake architecture approaches, third-party data products, or [ Amazon Security Lake](https://docs.aws.amazon.com/security-lake/latest/userguide/getting-started.html).  AWS recommends that you capture security data from AWS Regions that are [opted-in](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-regions.html) for your accounts, even when not actively in use.

1.  **Configure data source publication to your standardized locations**

   1.  Identify the sources for your security data and configure them to publish into your standardized locations. Evaluate options to automatically export data in the desired format as opposed to those where ETL processes need to be developed. With Amazon Security Lake, you can [collect data](https://docs.aws.amazon.com/security-lake/latest/userguide/source-management.html) from supported AWS sources and integrated third-party systems.

1.  **Configure tools to access your standardized locations**

   1.  Configure tools such as Amazon Athena, Quick Suite, or third-party solutions to have the access required to your standardized locations.  Configure these tools to operate out of the Security Tooling account with cross-account read access to the Log Archive account where applicable. [Create subscribers in Amazon Security Lake](https://docs.aws.amazon.com/security-lake/latest/userguide/subscriber-management.html) to provide these tools access to your data.

## Resources
### Related Best Practices
- [ SEC01-BP01 Separate workloads using accounts ](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_multi_accounts.html)
- [SEC07-BP04 Define data lifecycle management](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_data_classification_lifecycle_management.html)
- [SEC08-BP04 Enforce access control](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_protect_data_rest_access_control.html)
- [OPS08-BP02 Analyze workload logs](https://docs.aws.amazon.com/wellarchitected/latest/framework/ops_workload_observability_analyze_workload_logs.html)
### Related Documents
- [AWS Whitepapers: Organizing Your AWS Environment Using Multiple Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/organizing-your-aws-environment.html)
- [AWS Prescriptive Guidance: AWS Security Reference Architecture (AWS SRA)](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/welcome.html)
- [AWS Prescriptive Guidance: Logging and monitoring guide for application owners](https://docs.aws.amazon.com/prescriptive-guidance/latest/logging-monitoring-for-application-owners/introduction.html)
### Related Examples
- [Aggregating, searching, and visualizing log data from distributed sources with Amazon Athena and Quick Suite](https://aws.amazon.com/blogs/security/aggregating-searching-and-visualizing-log-data-from-distributed-sources-with-amazon-athena-and-amazon-quicksight/)
- [How to visualize Amazon Security Lake findings with Quick Suite](https://aws.amazon.com/blogs/security/how-to-visualize-amazon-security-lake-findings-with-amazon-quicksight/)
- [Generate AI powered insights for Amazon Security Lake using Amazon SageMaker AI Studio and Amazon Bedrock](https://aws.amazon.com/blogs/security/generate-ai-powered-insights-for-amazon-security-lake-using-amazon-sagemaker-studio-and-amazon-bedrock/)
- [Identify cybersecurity anomalies in your Amazon Security Lake data using Amazon SageMaker AI](https://aws.amazon.com/blogs/machine-learning/identify-cybersecurity-anomalies-in-your-amazon-security-lake-data-using-amazon-sagemaker/)
- [Ingest, transform, and deliver events published by Amazon Security Lake to Amazon OpenSearch Service](https://aws.amazon.com/blogs/big-data/ingest-transform-and-deliver-events-published-by-amazon-security-lake-to-amazon-opensearch-service/)
- [Simplify AWS CloudTrail log analysis with natural language query generation in CloudTrail Lake](https://aws.amazon.com/blogs/aws/simplify-aws-cloudtrail-log-analysis-with-natural-language-query-generation-in-cloudtrail-lake-preview/)
### Related Tools
- [Amazon Security Lake](https://docs.aws.amazon.com/security-lake/latest/userguide/what-is-security-lake.html)
- [Amazon Security Lake Partner Integrations](https://aws.amazon.com/security-lake/partners/)
- [Open Cybersecurity Schema Framework (OCSF)](https://github.com/ocsf)
- [Amazon Athena](https://aws.amazon.com/athena/)
- [Quick Suite](https://aws.amazon.com/quicksight/)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
