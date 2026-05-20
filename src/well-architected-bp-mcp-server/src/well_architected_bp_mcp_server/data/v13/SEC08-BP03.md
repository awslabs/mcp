---
id: "SEC08-BP03"
title: "Automate data at rest protection"
framework: "WAF"
domain: "Security"
capability: "How do you protect your data at rest?"
risk_level: "Medium"
---

# SEC08-BP03 Automate data at rest protection

## Desired Outcome
Automated systems scan and monitor data storage locations for misconfiguration of controls, unauthorized access, and unexpected use.  Detection of misconfigured storage locations initiates automated remediations.  Automated processes create data backups and store immutable copies outside of the original environment.

## Anti-Patterns
- Not considering options to enable encryption by default settings, where supported.
- Not considering security events, in addition to operational events, when formulating an automated backup and recovery strategy.
- Not enforcing public access settings for storage services.
- Not monitoring and audit your controls for protecting data at rest.

## Implementation Guidance
 Automation is a theme throughout the practices for protecting your data at rest. [SEC01-BP06 Automate deployment of standard security controls](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_automate_security_controls.html) describes how you can capture the configuration of your resources using *infrastructure as code* (IaC) templates, such as with [AWS CloudFormation](https://aws.amazon.com/cloudformation/).  These templates are committed to a version control system, and are used to deploy resources on AWS through a CI/CD pipeline.  These techniques equally apply to automating the configuration of your data storage solutions, such as encryption settings on Amazon S3 buckets.

 You can check the settings that you define in your IaC templates for misconfiguration in your CI/CD pipelines using rules in [AWS CloudFormation Guard](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html).  You can monitor settings that are not yet available in CloudFormation or other IaC tooling for misconfiguration with [AWS Config](https://aws.amazon.com/config/).  Alerts that Config generates for misconfigurations can be remediated automatically, as described in [SEC04-BP04 Initiate remediation for non-compliant resources](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_detect_investigate_events_noncompliant_resources.html).

 Using automation as part of your permissions management strategy is also an integral component of automated data protections. [SEC03-BP02 Grant least privilege access](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_permissions_least_privileges.html) and [SEC03-BP04 Reduce permissions continuously](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_permissions_continuous_reduction.html) describe configuring least-privilege access policies that are continually monitored by the [AWS Identity and Access Management Access Analyzer](https://aws.amazon.com/iam/access-analyzer/) to generate findings when permission can be reduced.  Beyond automation for monitoring permissions, you can configure [Amazon GuardDuty](https://aws.amazon.com/guardduty/) to watch for anomalous data access behavior for your [EBS volumes](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-ec2.html) (by way of an EC2 instance), [S3 buckets](https://docs.aws.amazon.com/guardduty/latest/ug/s3-protection.html), and supported [Amazon Relational Database Service databases](https://docs.aws.amazon.com/guardduty/latest/ug/rds-protection.html).

 Automation also plays a role in detecting when sensitive data is stored in unauthorized locations. [SEC07-BP03 Automate identification and classification](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_data_classification_auto_classification.html) describes how [Amazon Macie](https://aws.amazon.com/macie/) can monitor your S3 buckets for unexpected sensitive data and generate alerts that can initiate an automated response.

 Follow the practices in [REL09 Back up data](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/back-up-data.html) to develop an automated data backup and recovery strategy. Data backup and recovery is as important for recovering from security events as it is for operational events.

## Implementation Steps
1.  Capture data storage configuration in IaC templates.  Use automated checks in your CI/CD pipelines to detect misconfigurations.

   1.  You can use for [AWS CloudFormation](https://aws.amazon.com/cloudformation/) your IaC templates, and [AWS CloudFormation Guard](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html) for checking templates for misconfiguration.

   1.  Use [AWS Config](https://aws.amazon.com/config/) to run rules in a proactive evaluation mode. Use this setting to check the compliance of a resource as a step in your CI/CD pipeline before creating it.

1.  Monitor resources for data storage misconfigurations.

   1.  Set [AWS Config](https://aws.amazon.com/config/) to monitor data storage resources for changes in control configurations and generate alerts to invoke remediation actions when it detects a misconfiguration.

   1.  See [SEC04-BP04 Initiate remediation for non-compliant resources](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_detect_investigate_events_noncompliant_resources.html) for more guidance on automated remediations.

1.  Monitor and reduce data access permissions continually through automation.

   1.  [IAM Access Analyzer](https://aws.amazon.com/iam/access-analyzer/) can run continually to generate alerts when permissions can potentially be reduced.

1.  Monitor and alert on anomalous data access behaviors.

   1.  [GuardDuty](https://aws.amazon.com/guardduty/) watches for both known threat signatures and deviations from baseline access behaviors for data storage resources such as EBS volumes, S3 buckets, and RDS databases.

1.  Monitor and alert on sensitive data being stored in unexpected locations.

   1.  Use [Amazon Macie](https://aws.amazon.com/macie/) to continually scan your S3 buckets for sensitive data.

1.  Automate secure and encrypted backups of your data.

   1.  [AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html) is a managed service that creates encrypted and secure backups of various data sources on AWS.  [Elastic Disaster Recovery](https://aws.amazon.com/disaster-recovery/) allows you to copy full server workloads and maintain continuous data protection with a recovery point objective (RPO) measured in seconds.  You can configure both services to work together to automate creating data backups and copying them to failover locations.  This can help keep your data available when impacted by either operational or security events.

## Resources
### Related Best Practices
- [SEC01-BP06 Automate deployment of standard security controls](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_automate_security_controls.html)
- [SEC03-BP02 Grant least privilege access](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_permissions_least_privileges.html)
- [SEC03-BP04 Reduce permissions continuously](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_permissions_continuous_reduction.html)
- [SEC04-BP04 Initiate remediation for non-compliant resources](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_detect_investigate_events_noncompliant_resources.html)
- [SEC07-BP03 Automate identification and classification](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_data_classification_auto_classification.html)
- [REL09-BP02 Secure and encrypt backups](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_backing_up_data_secured_backups_data.html)
- [REL09-BP03 Perform data backup automatically](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_backing_up_data_automated_backups_data.html)
### Related Documents
- [AWS Prescriptive Guidance: Automatically encrypt existing and new Amazon EBS volumes](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/automatically-encrypt-existing-and-new-amazon-ebs-volumes.html)
- [Ransomware Risk Management on AWS Using the NIST Cyber Security Framework (CSF)](https://docs.aws.amazon.com/whitepapers/latest/ransomware-risk-management-on-aws-using-nist-csf/ransomware-risk-management-on-aws-using-nist-csf.html)
### Related Examples
- [How to use AWS Config proactive rules and AWS CloudFormation Hooks to prevent creation of noncompliant cloud resources](https://aws.amazon.com/blogs/mt/how-to-use-aws-config-proactive-rules-and-aws-cloudformation-hooks-to-prevent-creation-of-non-complaint-cloud-resources/)
- [Automate and centrally manage data protection for Amazon S3 with AWS Backup](https://aws.amazon.com/blogs/storage/automate-and-centrally-manage-data-protection-for-amazon-s3-with-aws-backup/)
- [AWS re:Invent 2023 - Implement proactive data protection using Amazon EBS snapshots](https://www.youtube.com/watch?v=d7C6XsUnmHc)
- [AWS re:Invent 2022 - Build and automate for resilience with modern data protection](https://www.youtube.com/watch?v=OkaGvr3xYNk)
### Related Tools
- [AWS CloudFormation Guard](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html)
- [AWS CloudFormation Guard Rules Registry](https://github.com/aws-cloudformation/aws-guard-rules-registry)
- [IAM Access Analyzer](https://aws.amazon.com/iam/access-analyzer/)
- [Amazon Macie](https://aws.amazon.com/macie/)
- [AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)
- [Elastic Disaster Recovery](https://aws.amazon.com/disaster-recovery/)
