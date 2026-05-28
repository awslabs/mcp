---
id: "SUS04-BP05"
title: "Remove unneeded or redundant data"
framework: "WAF"
domain: "Sustainability"
capability: "How do you take advantage of data management policies and patterns to support your sustainability goals?"
risk_level: "Medium"
---

# SUS04-BP05 Remove unneeded or redundant data

## Anti-Patterns
- You duplicate data that can be easily obtained or recreated.
- You back up all data without considering its criticality.
- You only delete data irregularly, on operational events, or not at all.
- You store data redundantly irrespective of the storage service's durability.
- You turn on Amazon S3 versioning without any business justification.

## Implementation Guidance
 When you remove unneeded and redundant datasets, you can reduce storage cost and environmental footprint. This practice may also make computing more efficient, as compute resources only process important data instead of unneeded data. Automate the deletion of unneeded data. Use technologies that deduplicate data at the file and block level. Use service features for native data replication and redundancy.

## Implementation Steps
- **Evaluate public datasets:** Evaluate if you can avoid storing data by using existing publicly available datasets in [AWS Data Exchange](https://aws.amazon.com/data-exchange/) and [Open Data on AWS](https://registry.opendata.aws/).
- **De-deplicate data:** Use mechanisms that can deduplicate data at the block and object level. Here are some examples of how to deduplicate data on AWS:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_data_a6.html)
- **Use lifecycle policies:** Use lifecycle policies to automate unneeded data deletion. Use native service features like [Amazon DynamoDB Time To Live](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html), [Amazon S3 Lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html), or [Amazon CloudWatch log retention](https://docs.aws.amazon.com/managedservices/latest/userguide/log-customize-retention.html) for deletion.
- **Use data virtualization:** Use data virtualization capabilities on AWS to maintain data at its source and avoid data duplication.
  - [Cloud Native Data Virtualization on AWS](https://www.youtube.com/watch?v=BM6sMreBzoA)
  - [Optimize Data Pattern Using Amazon Redshift Data Sharing](https://catalog.workshops.aws/well-architected-sustainability/en-US/3-data/optimize-data-pattern-using-redshift-data-sharing)
- **Use incremental backup:** Use backup technology that can make incremental backups.
- **Use native durability:** Leverage the durability of [Amazon S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DataDurability.html) and [replication of Amazon EBS](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volumes.html) to meet your durability goals instead of self-managed technologies (such as a redundant array of independent disks (RAID)).
- **Use efficient logging:** Centralize log and trace data, deduplicate identical log entries, and establish mechanisms to tune verbosity when needed.
- **Use efficient caching:** Pre-populate caches only where justified.
- Establish cache monitoring and automation to resize the cache accordingly.
- **Remove old version assets:** Remove out-of-date deployments and assets from object stores and edge caches when pushing new versions of your workload.

## Resources
### Related Documents
- [Change log data retention in CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html#SettingLogRetention)
- [Data deduplication on Amazon FSx for Windows File Server](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/using-data-dedup.html)
- [Features of Amazon FSx for ONTAP including data deduplication](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/what-is-fsx-ontap.html#features-overview)
- [Invalidating Files on Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html)
- [Using AWS Backup to back up and restore Amazon EFS file systems](https://docs.aws.amazon.com/efs/latest/ug/awsbackup.html)
- [What is Amazon CloudWatch Logs?](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html)
- [Working with backups on Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)
- [Integrate and deduplicate datasets using AWS Lake Formation](https://aws.amazon.com/blogs/big-data/integrate-and-deduplicate-datasets-using-aws-lake-formation-findmatches/)
### Related Videos
- [Amazon Redshift Data Sharing Use Cases](https://www.youtube.com/watch?v=sIoTB8B5nn4)
### Related Examples
- [How do I analyze my Amazon S3 server access logs using Amazon Athena?](https://aws.amazon.com/premiumsupport/knowledge-center/analyze-logs-athena/)
