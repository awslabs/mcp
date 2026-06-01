---
id: "SUS04-BP03"
title: "Use policies to manage the lifecycle of your datasets"
pillar: "Sustainability"
risk_level: "MEDIUM"
capability: "How do you take advantage of data management policies and patterns to support your sustainability goals?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_data_a4.html"
description: "Manage the lifecycle of all of your data and automatically enforce deletion to minimize the total storage required for your workload."
area: ["Data management"]
---

# SUS04-BP03 Use policies to manage the lifecycle of your datasets

Manage the lifecycle of all of your data and automatically enforce
deletion to minimize the total storage required for your workload.

**Common anti-patterns:**

- You manually delete data.
- You do not delete any of your workload data.
- You do not move data to more energy-efficient storage tiers based on its retention and access requirements.

**Benefits of establishing this best practice:** Using data lifecycle policies ensures efficient data access and retention in a workload.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Datasets usually have different retention and access requirements during their lifecycle.
For example, your application may need frequent access to some datasets for a limited
period of time. After that, those datasets are infrequently accessed. To improve the efficiency of data storage and computation over time, implement lifecycle policies, which are rules that define how data is handled over time.

With lifecycle configuration rules, you can tell the specific storage service to transition a dataset to more energy-efficient storage tiers, archive it, or delete it. This practice minimizes active data storage and retrieval, which leads to lower energy consumption. In addition, practices such as archiving or deleting obsolete data support regulatory compliance and data governance.

### Implementation steps

- **Use data classification:** [Classify datasets in your workload.](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_data_a2.html)
- **Define handling rules:** Define handling procedures for each data class.
- **Enable automation:** Set automated lifecycle policies to enforce lifecycle rules.
Here are some examples of how to set up automated lifecycle policies
for different AWS storage services:

Storage service
How to set automated lifecycle policies

[Amazon S3](https://aws.amazon.com/s3/index.html)

You can use [Amazon S3 Lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html) to manage your objects throughout their lifecycle.
If your access patterns are unknown, changing, or unpredictable, you can use [Amazon S3
Intelligent-Tiering](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intelligent-tiering.html), which monitors access patterns and automatically moves objects that
have not been accessed to lower-cost access tiers. You can leverage [Amazon S3 Storage Lens](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens.html)
metrics to identify optimization opportunities and gaps in lifecycle management.

[Amazon Elastic Block Store](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AmazonEBS.html)

You can use [Amazon Data Lifecycle Manager](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snapshot-lifecycle.html) to automate the creation,
retention, and deletion of Amazon EBS snapshots and Amazon EBS-backed AMIs.

[Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/whatisefs.html)

[Amazon EFS lifecycle management](https://docs.aws.amazon.com/efs/latest/ug/lifecycle-management-efs.html) automatically manages file storage for your file systems.

[Amazon Elastic Container Registry](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html)

[Amazon ECR lifecycle policies](https://docs.aws.amazon.com/AmazonECR/latest/userguide/LifecyclePolicies.html) automate the cleanup of your
container images by expiring images based on age or count.

[AWS Elemental MediaStore](https://docs.aws.amazon.com/mediastore/latest/ug/what-is.html)

You can use an [object lifecycle policy](https://docs.aws.amazon.com/mediastore/latest/ug/policies-object-lifecycle.html) that governs how long objects should be stored in the MediaStore container.
- **Delete unused assets:** Delete unused volumes, snapshots, and data that is out of its retention period.
Use native service features like [Amazon DynamoDB Time To Live](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html) or [Amazon CloudWatch
log retention](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html#SettingLogRetention) for deletion.
- **Aggregate and compress:** Aggregate and compress data where applicable based on lifecycle rules.

## Resources

**Related documents:**

- [Optimize your Amazon S3 Lifecycle rules with Amazon S3 Storage Class Analysis](https://docs.aws.amazon.com/AmazonS3/latest/userguide/analytics-storage-class.html)
- [Evaluating
Resources with AWS Config Rules](https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config.html)

**Related videos:**

- [AWS re:Invent 2021 - Amazon S3 Lifecycle best practices to optimize your storage spend](https://www.youtube.com/watch?v=yGNXn7jOytA)
- [AWS re:Invent 2023 - Optimizing storage price and performance with Amazon S3](https://www.youtube.com/watch?v=RxgYNrXPOLw)
- [Simplify Your Data Lifecycle and Optimize Storage Costs With Amazon S3 Lifecycle](https://www.youtube.com/watch?v=53eHNSpaMJI)
- [Reduce Your Storage Costs Using Amazon S3 Storage Lens](https://www.youtube.com/watch?v=A8qOBLM6ITY)
