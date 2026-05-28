---
id: "REL09-BP03"
title: "Perform data backup automatically"
framework: "WAF"
domain: "Reliability"
capability: "How do you back up data?"
risk_level: "Medium"
effort: "Low"
---

# REL09-BP03 Perform data backup automatically

## Desired Outcome
An automated process that creates backups of data sources at an established cadence.

## Anti-Patterns
- Performing backups manually.
- Using resources that have backup capability, but not including the backup in your automation.

## Implementation Guidance
 AWS Backup can be used to create automated data backups of various AWS data sources. Amazon RDS instances can be backed up almost continuously every five minutes and Amazon S3 objects can be backed up almost continuously every fifteen minutes, providing for point-in-time recovery (PITR) to a specific point in time within the backup history. For other AWS data sources, such as Amazon EBS volumes, Amazon DynamoDB tables, or Amazon FSx file systems, AWS Backup can run automated backup as frequently as every hour. These services also offer native backup capabilities. AWS services that offer automated backup with point-in-time recovery include [Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery_Howitworks.html), [Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html), and [Amazon Keyspaces (for Apache Cassandra)](https://docs.aws.amazon.com/keyspaces/latest/devguide/PointInTimeRecovery.html) – these can be restored to a specific point in time within the backup history. Most other AWS data storage services offer the ability to schedule periodic backups, as frequently as every hour.

 Amazon RDS and Amazon DynamoDB offer continuous backup with point-in-time recovery. Amazon S3 versioning, once turned on, is automatic. [Amazon Data Lifecycle Manager](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snapshot-lifecycle.html) can be used to automate the creation, copy and deletion of Amazon EBS snapshots. It can also automate the creation, copy, deprecation and deregistration of Amazon EBS-backed Amazon Machine Images (AMIs) and their underlying Amazon EBS snapshots.

 AWS Elastic Disaster Recovery provides continuous block-level replication from the source environment (on-premises or AWS) to the target recovery region. Point-in-time Amazon EBS snapshots are automatically created and managed by the service.

 For a centralized view of your backup automation and history, AWS Backup provides a fully managed, policy-based backup solution. It centralizes and automates the back up of data across multiple AWS services in the cloud as well as on premises using the AWS Storage Gateway.

 In additional to versioning, Amazon S3 features replication. The entire S3 bucket can be automatically replicated to another bucket in the same, or a different AWS Region.

## Implementation Steps
1.  **Identify data sources** that are currently being backed up manually. For more detail, see [REL09-BP01 Identify and back up all data that needs to be backed up, or reproduce the data from sources](rel_backing_up_data_identified_backups_data.md).

1.  **Determine the RPO** for the workload. For more detail, see [REL13-BP01 Define recovery objectives for downtime and data loss](rel_planning_for_recovery_objective_defined_recovery.md).

1.  **Use an automated backup solution or managed service**. AWS Backup is a fully-managed service that makes it easy to [centralize and automate data protection across AWS services, in the cloud, and on-premises](https://docs.aws.amazon.com/aws-backup/latest/devguide/creating-a-backup.html#creating-automatic-backups). Using backup plans in AWS Backup, create rules which define the resources to backup, and the frequency at which these backups should be created. This frequency should be informed by the RPO established in Step 2. For hands-on guidance on how to create automated backups using AWS Backup, see [Testing Backup and Restore of Data](https://wellarchitectedlabs.com/reliability/200_labs/200_testing_backup_and_restore_of_data/). Native backup capabilities are offered by most AWS services that store data. For example, RDS can be leveraged for automated backups with point-in-time recovery (PITR).

1.  **For data sources not supported** by an automated backup solution or managed service such as on-premises data sources or message queues, consider using a trusted third-party solution to create automated backups. Alternatively, you can create automation to do this using the AWS CLI or SDKs. You can use AWS Lambda Functions or AWS Step Functions to define the logic involved in creating a data backup, and use Amazon EventBridge to invoke it at a frequency based on your RPO.

## Resources
### Related Documents
- [APN Partner: partners that can help with backup](https://aws.amazon.com/partners/find/results/?keyword=Backup)
- [AWS Marketplace: products that can be used for backup](https://aws.amazon.com/marketplace/search/results?searchTerms=Backup)
- [Creating an EventBridge Rule That Triggers on a Schedule](https://docs.aws.amazon.com/eventbridge/latest/userguide/create-eventbridge-scheduled-rule.html)
- [What Is AWS Backup?](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)
- [What Is AWS Step Functions?](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
- [ What is AWS Elastic Disaster Recovery? ](https://docs.aws.amazon.com/drs/latest/userguide/what-is-drs.html)
### Related Videos
- [AWS re:Invent 2019: Deep dive on AWS Backup, ft. Rackspace (STG341)](https://youtu.be/av8DpL0uFjc)
