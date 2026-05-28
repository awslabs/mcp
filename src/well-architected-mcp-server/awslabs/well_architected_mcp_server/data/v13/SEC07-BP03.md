---
id: "SEC07-BP03"
title: "Automate identification and classification"
framework: "WAF"
domain: "Security"
capability: "How do you classify your data?"
risk_level: "Medium"
---

# SEC07-BP03 Automate identification and classification

## Desired Outcome
You are able to verify whether the proper controls are in place based on your classification and handling policy. Automated tools and services help you to identify and classify the sensitivity level of your data.  Automation also helps you continually monitor your environments to detect and alert if data is being stored or handled in unauthorized ways so corrective action can be taken quickly.

## Anti-Patterns
- Relying solely on manual processes for data identification and classification, which can be error-prone and time-consuming.  This can lead to inefficient and inconsistent data classification, especially as data volumes grow.
- Not having mechanisms to track and manage data assets across the organization.
- Overlooking the need for continuous monitoring and classification of data as it moves and evolves within the organization.

## Implementation Guidance
 While human judgment is often used to classify data during the initial design phases of a workload, consider having systems in place that automate identification and classification on test data as a preventive control. For example, developers can be provided a tool or service to scan representative data to determine its sensitivity.  Within AWS, you can upload data sets into [Amazon S3](https://aws.amazon.com/s3/) and scan them using [Amazon Macie](https://aws.amazon.com/macie/), [Amazon Comprehend](https://aws.amazon.com/comprehend/), or [Amazon Comprehend Medical](https://aws.amazon.com/comprehend/medical/).  Likewise, consider scanning data as part of unit and integration testing to detect where sensitive data is not expected. Alerting on sensitive data at this stage can highlight gaps in protections before deployment to production. Other features such as sensitive data detection in [AWS Glue](https://docs.aws.amazon.com/glue/latest/dg/detect-PII.html), [Amazon SNS](https://docs.aws.amazon.com/sns/latest/dg/sns-message-data-protection-managed-data-identifiers.htm), and [Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/mask-sensitive-log-data.html) can also be used to detect PII and take mitigating action. For any automated tool or service, understand how it defines sensitive data, and augment it with other human or automated solutions to close any gaps as needed.

 As a detective control, use ongoing monitoring of your environments to detect if sensitive data is being stored in non-compliant ways.  This can help detect situations such as sensitive data being emitted into log files or being copied to a data analytics environment without proper de-identification or redaction.  Data that is stored in Amazon S3 can be continually monitored for sensitive data using Amazon Macie.

## Implementation Steps
1.  Review the data classification scheme within your organization described in [SEC07-BP01](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_data_classification_identify_data.html).

   1.  With an understanding of your organization's data classification scheme, you can establish accurate processes for automated identification and classification that align with your company's policies.

1.  Perform an initial scan of your environments for automated identification and classification.

   1.  An initial full scan of your data can help produce a comprehensive understanding of where sensitive data resides in your environments. When a full scan is not initially required or is unable to be completed up-front due to cost, evaluate if data sampling techniques are suitable to achieve your outcomes. For example, Amazon Macie can be configured to perform a broad automated sensitive data discovery operation across your S3 buckets.  This capability uses sampling techniques to cost-efficiently perform a preliminary analysis of where sensitive data resides.  A deeper analysis of S3 buckets can then be performed using a sensitive data discovery job. Other data stores can also be exported to S3 to be scanned by Macie.

   1.  Establish access control defined in [SEC07-BP02](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_data_classification_define_protection.html) for your data storage resources identified within your scan.

1.  Configure ongoing scans of your environments.

   1.  The automated sensitive data discovery capability of Macie can be used to perform ongoing scans of your environments.  Known S3 buckets that are authorized to store sensitive data can be excluded using an allow list in Macie.

1.  Incorporate identification and classification into your build and test processes.

   1.  Identify tools that developers can use to scan data for sensitivity while workloads are in development.  Use these tools as part of integration testing to alert when sensitive data is unexpected and prevent further deployment.

1.  Implement a system or runbook to take action when sensitive data is found in unauthorized locations.

   1.  Restrict access to data using auto-remediation. For example, you can move this data to an S3 bucket with restricted access or tag the object if you use attribute-based access control (ABAC). Additionally, consider masking the data when it is detected.

   1.  Alert your data protection and incident response teams to investigate the root cause of the incident. Any learnings they identify can help prevent future incidents.

## Resources
### Related Documents
- [AWS Glue: Detect and process sensitive data](https://docs.aws.amazon.com/glue/latest/dg/detect-PII.html)
- [Using managed data identifiers in Amazon SNS](https://docs.aws.amazon.com/sns/latest/dg/sns-message-data-protection-managed-data-identifiers.html)
- [Amazon CloudWatch Logs: Help protect sensitive log data with masking](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/mask-sensitive-log-data.html)
### Related Examples
- [Enabling data classification for Amazon RDS database with Macie](https://aws.amazon.com/blogs/security/enabling-data-classification-for-amazon-rds-database-with-amazon-macie/)
- [Detecting sensitive data in DynamoDB with Macie](https://aws.amazon.com/blogs/security/detecting-sensitive-data-in-dynamodb-with-macie/)
### Related Tools
- [Amazon Macie](https://aws.amazon.com/macie/)
- [Amazon Comprehend](https://aws.amazon.com/comprehend/)
- [Amazon Comprehend Medical](https://aws.amazon.com/comprehend/medical/)
- [AWS Glue](https://aws.amazon.com/glue/)
