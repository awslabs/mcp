---
id: "SEC04-BP01"
title: "Configure service and application logging"
framework: "WAF"
domain: "Security"
capability: "How do you detect and investigate security events?"
risk_level: "High"
---

# SEC04-BP01 Configure service and application logging

## Desired Outcome
An organization should be able to reliably and consistently retrieve security event logs from AWS services and applications in a timely manner when required to fulfill an internal process or obligation, such as a security incident response. Consider centralizing logs for better operational results.

## Anti-Patterns
- Logs are stored in perpetuity or deleted too soon.
- Everybody can access logs.
- Relying entirely on manual processes for log governance and use.
- Storing every single type of log just in case it is needed.
- Checking log integrity only when necessary.

## Implementation Guidance
 During a security investigation or other use cases based on your requirements, you need to be able to review relevant logs to record and understand the full scope and timeline of the incident. Logs are also required for alert generation, indicating that certain actions of interest have happened. It is critical to select, turn on, store, and set up querying and retrieval mechanisms and alerting.

## Implementation Steps
- **Select and use log sources.** Ahead of a security investigation, you need to capture relevant logs to retroactively reconstruct activity in an AWS account. Select log sources relevant to your workloads.

   The log source selection criteria should be based on the use cases required by your business. Establish a trail for each AWS account using AWS CloudTrail or an AWS Organizations trail, and configure an Amazon S3 bucket for it.

   AWS CloudTrail is a logging service that tracks API calls made against an AWS account capturing AWS service activity. It’s turned on by default with a 90-day retention of management events that can be [retrieved through CloudTrail Event history](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html) using the AWS Management Console, the AWS CLI, or an AWS SDK. For longer retention and visibility of data events, [create a CloudTrail trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-create-and-update-a-trail.html) and associate it with an Amazon S3 bucket, and optionally with a Amazon CloudWatch log group. Alternatively, you can create a [CloudTrail Lake](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html), which retains CloudTrail logs for up to seven years and provides a SQL-based querying facility

   AWS recommends that customers using a VPC turn on network traﬃc and DNS logs using [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html) and [Amazon Route 53 resolver query logs](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-query-logs.html), respectively, and streaming them to either an Amazon S3 bucket or a CloudWatch log group. You can create a VPC ﬂow log for a VPC, a subnet, or a network interface. For VPC Flow Logs, you can be selective on how and where you use Flow Logs to reduce cost.

   AWS CloudTrail Logs, VPC Flow Logs, and Route 53 resolver query logs are the basic logging sources to support security investigations in AWS. You can also use [Amazon Security Lake](https://docs.aws.amazon.com/security-lake/latest/userguide/what-is-security-lake.html) to collect, normalize, and store this log data in Apache Parquet format and Open Cybersecurity Schema Framework (OCSF), which is ready for querying. Security Lake also supports other AWS logs and logs from third-party sources.

   AWS services can generate logs not captured by the basic log sources, such as Elastic Load Balancing logs, AWS WAF logs, AWS Config recorder logs, Amazon GuardDuty ﬁndings, Amazon Elastic Kubernetes Service (Amazon EKS) audit logs, and Amazon EC2 instance operating system and application logs. For a full list of logging and monitoring options, see [Appendix A: Cloud capability deﬁnitions – Logging and Events](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/logging-and-events.html) of the [AWS Security Incident Response Guide](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/detection.html).
- **Research logging capabilities for each AWS service and application:** Each AWS service and application provides you with options for log storage, each of which with its own retention and life-cycle capabilities. The two most common log storage services are Amazon Simple Storage Service (Amazon S3) and Amazon CloudWatch. For long retention periods, it is recommended to use Amazon S3 for its cost effectiveness and flexible lifecycle capabilities. If the primary logging option is Amazon CloudWatch Logs, as an option, you should consider archiving less frequently accessed logs to Amazon S3.
- **Select log storage:** The choice of log storage is generally related to which querying tool you use, retention capabilities, familiarity, and cost. The main options for log storage are an Amazon S3 bucket or a CloudWatch Log group.

   An Amazon S3 bucket provides cost-eﬀective, durable storage with an optional lifecycle policy. Logs stored in Amazon S3 buckets can be queried using services such as Amazon Athena.

   A CloudWatch log group provides durable storage and a built-in query facility through CloudWatch Logs Insights.
- **Identify appropriate log retention:** When you use an Amazon S3 bucket or CloudWatch log group to store logs, you must establish adequate lifecycles for each log source to optimize storage and retrieval costs. Customers generally have between three months to one year of logs readily available for querying, with retention of up to seven years. The choice of availability and retention should align with your security requirements and a composite of statutory, regulatory, and business mandates.
- **Use logging for each AWS service and application with proper retention and lifecycle policies:** For each AWS service or application in your organization, look for the specific logging configuration guidance:
  - [ Configure AWS CloudTrail Trail ](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-create-and-update-a-trail.html)
  - [ Configure VPC Flow Logs ](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)
  - [ Configure Amazon GuardDuty Finding Export ](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_exportfindings.html)
  - [ Configure AWS Config recording ](https://docs.aws.amazon.com/systems-manager/latest/userguide/quick-setup-config.html)
  - [ Configure AWS WAF web ACL traffic ](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html)
  - [ Configure AWS Network Firewall network traffic logs ](https://docs.aws.amazon.com/network-firewall/latest/developerguide/firewall-logging.html)
  - [ Configure Elastic Load Balancing access logs ](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html)
  - [ Configure Amazon Route 53 resolver query logs ](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-query-logs.html)
  - [ Configure Amazon RDS logs ](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_LogAccess.html)
  - [ Configure Amazon EKS Control Plane logs ](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
  - [ Configure Amazon CloudWatch agent for Amazon EC2 instances and on-premises servers ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- **Select and implement querying mechanisms for logs:** For log queries, you can use [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html) for data stored in CloudWatch log groups, and [Amazon Athena](https://aws.amazon.com/athena/) and [Amazon OpenSearch Service](https://aws.amazon.com/opensearch-service/) for data stored in Amazon S3. You can also use third-party querying tools such as a security information and event management (SIEM) service.

   The process for selecting a log querying tool should consider the people, process, and technology aspects of your security operations. Select a tool that fulﬁlls operational, business, and security requirements, and is both accessible and maintainable in the long term. Keep in mind that log querying tools work optimally when the number of logs to be scanned is kept within the tool’s limits. It is not uncommon to have multiple querying tools because of cost or technical constraints.

   For example, you might use a third-party security information and event management (SIEM) tool to perform queries for the last 90 days of data, but use Athena to perform queries beyond 90 days because of the log ingestion cost of a SIEM. Regardless of the implementation, verify that your approach minimizes the number of tools required to maximize operational eﬃciency, especially during a security event investigation.
- **Use logs for alerting:** AWS provides alerting through several security services:
  - [AWS Config](https://aws.amazon.com/config/) monitors and records your AWS resource configurations and allows you to automate the evaluation and remediation against desired configurations.
  - [Amazon GuardDuty](https://aws.amazon.com/guardduty/) is a threat detection service that continually monitors for malicious activity and unauthorized behavior to protect your AWS accounts and workloads. GuardDuty ingests, aggregates, and analyzes information from sources, such as AWS CloudTrail management and data events, DNS logs, VPC Flow Logs, and Amazon EKS Audit logs. GuardDuty pulls independent data streams directly from CloudTrail, VPC Flow Logs, DNS query logs, and Amazon EKS. You don’t have to manage Amazon S3 bucket policies or modify the way you collect and store logs. It is still recommended to retain these logs for your own investigation and compliance purposes.
  - [AWS Security Hub](https://aws.amazon.com/security-hub/) provides a single place that aggregates, organizes, and prioritizes your security alerts or findings from multiple AWS services and optional third-party products to give you a comprehensive view of security alerts and compliance status.

   You can also use custom alert generation engines for security alerts not covered by these services or for speciﬁc alerts relevant to your environment. For information on building these alerts and detections, see [Detection in the AWS Security Incident Response Guide](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/detection.html).

## Resources
### Related Best Practices
- [SEC04-BP02 Capture logs, findings, and metrics in standardized locations](sec_detect_investigate_events_logs.md)
- [SEC07-BP04 Define scalable data lifecycle management](sec_data_classification_lifecycle_management.md)
- [SEC10-BP06 Pre-deploy tools](sec_incident_response_pre_deploy_tools.md)
### Related Documents
- [AWS Security Incident Response Guide ](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/aws-security-incident-response-guide.html)
- [ Getting Started with Amazon Security Lake ](https://aws.amazon.com/security-lake/getting-started/)
- [ Getting started: Amazon CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_GettingStarted.html)
### Related Videos
- [AWS re:Invent 2022 - Introducing Amazon Security Lake ](https://www.youtube.com/watch?v=V7XwbPPjXSY)
### Related Examples
- [ Assisted Log Enabler for AWS](https://github.com/awslabs/assisted-log-enabler-for-aws/)
- [AWS Security Hub Findings Historical Export ](https://github.com/aws-samples/aws-security-hub-findings-historical-export)
