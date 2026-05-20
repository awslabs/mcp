---
id: "SUS04-BP06"
title: "Use shared file systems or storage to access common data"
framework: "WAF"
domain: "Sustainability"
capability: "How do you take advantage of data management policies and patterns to support your sustainability goals?"
risk_level: "Medium"
---

# SUS04-BP06 Use shared file systems or storage to access common data

## Anti-Patterns
- You provision storage for each individual client.
- You do not detach data volume from inactive clients.
- You do not provide access to storage across platforms and systems.

## Implementation Guidance
 If you have multiple users or applications accessing the same datasets, using shared storage technology is crucial to use efficient infrastructure for your workload. Shared storage technology provides a central location to store and manage datasets and avoid data duplication. It also enforces consistency of the data across different systems. Moreover, shared storage technology allows for more efficient use of compute power, as multiple compute resources can access and process data at the same time in parallel.

 Fetch data from these shared storage services only as needed and detach unused volumes to free up resources.

## Implementation Steps
- **Use shared storage:** Migrate data to shared storage when the data has multiple consumers. Here are some examples of shared storage technology on AWS:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_data_a7.html)
- **Fetch data as needed:** Copy data to or fetch data from shared file systems only as needed. As an example, you can create an [Amazon FSx for Lustre file system backed by Amazon S3](https://aws.amazon.com/blogs/storage/new-enhancements-for-moving-data-between-amazon-fsx-for-lustre-and-amazon-s3/) and only load the subset of data required for processing jobs to Amazon FSx.
- **Delete unneeded data:** Delete data as appropriate for your usage patterns as outlined in [SUS04-BP03 Use policies to manage the lifecycle of your datasets](sus_sus_data_a4.md).
- **Detach inactive clients:** Detach volumes from clients that are not actively using them.

## Resources
### Related Documents
- [ Linking your file system to an Amazon S3 bucket ](https://docs.aws.amazon.com/fsx/latest/LustreGuide/create-dra-linked-data-repo.html)
- [ Using Amazon EFS for AWS Lambda in your serverless applications ](https://aws.amazon.com/blogs/compute/using-amazon-efs-for-aws-lambda-in-your-serverless-applications/)
- [ Amazon EFS Intelligent-Tiering Optimizes Costs for Workloads with Changing Access Patterns ](https://aws.amazon.com/blogs/aws/new-amazon-efs-intelligent-tiering-optimizes-costs-for-workloads-with-changing-access-patterns/)
- [ Using Amazon FSx with your on-premises data repository ](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fsx-on-premises.html)
### Related Videos
- [ Storage cost optimization with Amazon EFS ](https://www.youtube.com/watch?v=0nYAwPsYvBo)
- [AWS re:Invent 2023 - What's new with AWS file storage](https://www.youtube.com/watch?v=yXIeIKlTFV0)
- [AWS re:Invent 2023 - File storage for builders and data scientists on Amazon Elastic File System](https://www.youtube.com/watch?v=g0f6lrmEyRM)
