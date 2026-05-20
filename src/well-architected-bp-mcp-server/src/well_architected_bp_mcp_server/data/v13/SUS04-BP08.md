---
id: "SUS04-BP08"
title: "Back up data only when difficult to recreate"
framework: "WAF"
domain: "Sustainability"
capability: "How do you take advantage of data management policies and patterns to support your sustainability goals?"
risk_level: "Medium"
---

# SUS04-BP08 Back up data only when difficult to recreate

## Anti-Patterns
- You do not have a backup strategy for your data.
- You back up data that can be easily recreated.

## Implementation Guidance
 Avoiding the back up of unnecessary data can help lower cost and reduce the storage resources used by the workload. Only back up data that has business value or is needed to satisfy compliance requirements. Examine backup policies and exclude ephemeral storage that doesn’t provide value in a recovery scenario.

## Implementation Steps
- **Classify data:** Implement data classification policy as outlined in [SUS04-BP01 Implement a data classification policy](sus_sus_data_a2.md).
- **Design a backup strategy:** Use the criticality of your data classification and design backup strategy based on your [recovery time objective (RTO) and recovery point objective (RPO](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)). Avoid backing up non-critical data.
  - Exclude data that can be easily recreated.
  - Exclude ephemeral data from your backups.
  - Exclude local copies of data, unless the time required to restore that data from a common location exceeds your service-level agreements (SLAs).
- **Use automated backup:** Use an automated solution or managed service to back up business-critical data.
  - [AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html) is a fully-managed service that makes it easy to centralize and automate data protection across AWS services, in the cloud, and on premises. For hands-on guidance on how to create automated backups using AWS Backup, see [Well-Architected Labs - Testing Backup and Restore of Data](https://catalog.workshops.aws/well-architected-reliability/en-US/4-failure-management/1-backup/30-testing-backup-and-restore-of-data).
  - [Automate backups and optimize backup costs for Amazon EFS using AWS Backup](https://aws.amazon.com/blogs/storage/automating-backups-and-optimizing-backup-costs-for-amazon-efs-using-aws-backup/).

## Resources
### Related Best Practices
- [REL09-BP01 Identify and back up all data that needs to be backed up, or reproduce the data from sources](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_backing_up_data_identified_backups_data.html)
- [REL09-BP03 Perform data backup automatically](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_backing_up_data_automated_backups_data.html)
- [REL13-BP02 Use defined recovery strategies to meet the recovery objectives](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)
### Related Documents
- [Using AWS Backup to back up and restore Amazon EFS file systems](https://docs.aws.amazon.com/efs/latest/ug/awsbackup.html)
- [Amazon EBS snapshots](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EBSSnapshots.html)
- [Working with backups on Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)
- [ APN Partner: partners that can help with backup ](https://partners.amazonaws.com/search/partners?keyword=Backup)
- [AWS Marketplace: products that can be used for backup ](https://aws.amazon.com/marketplace/search/results?searchTerms=Backup)
- [ Backing Up Amazon EFS ](https://docs.aws.amazon.com/efs/latest/ug/efs-backup-solutions.html)
- [ Backing Up Amazon FSx for Windows File Server ](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/using-backups.html)
- [ Backup and Restore for Amazon ElastiCache (Redis OSS) ](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/backups.html)
### Related Videos
- [AWS re:Invent 2023 - Backup and disaster recovery strategies for increased resilience](https://www.youtube.com/watch?v=E073XISxrSU)
- [AWS re:Invent 2023 - What's new with AWS Backup](https://www.youtube.com/watch?v=QIffkOyTf7I)
- [AWS re:Invent 2021 - Backup, disaster recovery, and ransomware protection with AWS](https://www.youtube.com/watch?v=Ru4jxh9qazc)
