---
id: "PERF03-BP01"
title: "Use a purpose-built data store that best supports your data access and storage requirements"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you store, manage, and access data in your workload?"
risk_level: "High"
---

# PERF03-BP01 Use a purpose-built data store that best supports your data access and storage requirements

## Anti-Patterns
- You stick to one data store because there is internal experience and knowledge of one particular type of database solution.
- You assume that all workloads have similar data storage and access requirements.
- You have not implemented a data catalog to inventory your data assets.

## Implementation Guidance
 When selecting and implementing data storage, make sure that the querying, scaling, and storage characteristics support the workload data requirements. AWS provides numerous data storage and database technologies including block storage, object storage, streaming storage, file system, relational, key-value, document, in-memory, graph, time series, and ledger databases. Each data management solution has options and configurations available to you to support your use-cases and data models. By understanding data characteristics and requirements, you can break away from monolithic storage technology and restrictive, one-size-fits-all approaches to focus on managing data appropriately.

## Implementation Steps
- Conduct an inventory of the various data types that exist in your workload.
- Understand and document data characteristics and requirements, including:
  - Data type (unstructured, semi-structured, relational)
  - Data volume and growth
  - Data durability: persistent, ephemeral, transient
  - ACID (atomicity, consistency, isolation, durability) requirements
  - Data access patterns (read-heavy or write-heavy)
  - Latency
  - Throughput
  - IOPS (input/output operations per second)
  - Data retention period
- Learn about different data stores ([storage](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/storage-services.html) and [database](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/database.html) services) available for your workload on AWS that can meet your data characteristics, as outlined in [PERF01-BP01 Learn about and understand available cloud services and features](perf_architecture_understand_cloud_services_and_features.md). Some examples of AWS storage technologies and their key characteristics include:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/perf_data_use_purpose_built_data_store.html)
- If you are building a data platform, leverage [modern data architecture](https://aws.amazon.com/big-data/datalakes-and-analytics/modern-data-architecture/) on AWS to integrate your data lake, data warehouse, and purpose-built data stores.
- The key questions that you need to consider when choosing a data store for your workload are as follows:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/perf_data_use_purpose_built_data_store.html)
- Perform experiments and benchmarking in a non-production environment to identify which data store can address your workload requirements.

## Resources
### Related Documents
- [Amazon EBS Volume Types](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EBSVolumeTypes.html)
- [Amazon EC2 Storage](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Storage.html)
- [Amazon EFS: Amazon EFS Performance](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
- [Amazon FSx for Lustre Performance](https://docs.aws.amazon.com/fsx/latest/LustreGuide/performance.html)
- [Amazon FSx for Windows File Server Performance](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/performance.html)
- [Amazon Glacier: Amazon Glacier Documentation](https://docs.aws.amazon.com/amazonglacier/latest/dev/introduction.html)
- [Amazon S3: Request Rate and Performance Considerations](https://docs.aws.amazon.com/AmazonS3/latest/dev/request-rate-perf-considerations.html)
- [Cloud Storage with AWS](https://aws.amazon.com/products/storage/)
- [Amazon EBS I/O Characteristics](https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/ebs-io-characteristics.html)
- [Cloud Databases with AWS ](https://aws.amazon.com/products/databases/?ref=wellarchitected)
- [AWS Database Caching ](https://aws.amazon.com/caching/database-caching/?ref=wellarchitected)
- [DynamoDB Accelerator](https://aws.amazon.com/dynamodb/dax/?ref=wellarchitected)
- [Amazon Aurora best practices ](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Aurora.BestPractices.html?ref=wellarchitected)
- [Amazon Redshift performance ](https://docs.aws.amazon.com/redshift/latest/dg/c_challenges_achieving_high_performance_queries.html?ref=wellarchitected)
- [Amazon Athena top 10 performance tips ](https://aws.amazon.com/blogs/big-data/top-10-performance-tuning-tips-for-amazon-athena/?ref=wellarchitected)
- [Amazon Redshift Spectrum best practices ](https://aws.amazon.com/blogs/big-data/10-best-practices-for-amazon-redshift-spectrum/?ref=wellarchitected)
- [Amazon DynamoDB best practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BestPractices.html?ref=wellarchitected)
- [Choose between Amazon EC2 and Amazon RDS](https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-sql-server/comparison.html)
- [ Best Practices for Implementing Amazon ElastiCache ](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/BestPractices.html)
### Related Videos
- [AWS re:Invent 2023: Improve Amazon Elastic Block Store efficiency and be more cost-efficient](https://www.youtube.com/watch?v=7-CB02rqiuw)
- [AWS re:Invent 2023: Optimizing storage price and performance with Amazon Simple Storage Service](https://www.youtube.com/watch?v=RxgYNrXPOLw)
- [AWS re:Invent 2023: Building and optimizing a data lake on Amazon Simple Storage Service](https://www.youtube.com/watch?v=mpQa_Zm1xW8)
- [AWS re:Invent 2022: Building modern data architectures on AWS](https://www.youtube.com/watch?v=Uk2CqEt5f0o)
- [AWS re:Invent 2022: Building data mesh architectures on AWS](https://www.youtube.com/watch?v=nGRvlobeM_U)
- [AWS re:Invent 2023: Deep dive into Amazon Aurora and its innovations](https://www.youtube.com/watch?v=je6GCOZ22lI)
- [AWS re:Invent 2023: Advanced data modeling with Amazon DynamoDB](https://www.youtube.com/watch?v=PVUofrFiS_A)
- [AWS re:Invent 2022: Modernize apps with purpose-built databases](https://www.youtube.com/watch?v=V-DiplATdi0)
- [ Amazon DynamoDB deep dive: Advanced design patterns ](https://www.youtube.com/watch?v=6yqfmXiZTlM)
### Related Examples
- [AWS Purpose Built Databases Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/93f64257-52be-4c12-a95b-c0a1ff3b7e2b/en-US)
- [Databases for Developers](https://catalog.workshops.aws/db4devs/en-US)
- [AWS Modern Data Architecture Immersion Day](https://catalog.us-east-1.prod.workshops.aws/workshops/32f3e732-d67d-4c63-b967-c8c5eabd9ebf/en-US)
- [Build a Data Mesh on AWS](https://catalog.us-east-1.prod.workshops.aws/workshops/23e6326b-58ee-4ab0-9bc7-3c8d730eb851/en-US)
- [Amazon S3 Examples](https://docs.aws.amazon.com/sdk-for-javascript/v2/developer-guide/s3-examples.html)
- [Optimize Data Pattern using Amazon Redshift Data Sharing](https://wellarchitectedlabs.com/sustainability/300_labs/300_optimize_data_pattern_using_redshift_data_sharing/)
- [Database Migrations](https://github.com/aws-samples/aws-database-migration-samples)
- [MS SQL Server - AWS Database Migration Service (AWS DMS) Replication Demo](https://github.com/aws-samples/aws-dms-sql-server)
- [Database Modernization Hands On Workshop](https://github.com/aws-samples/amazon-rds-purpose-built-workshop)
- [Amazon Neptune Samples](https://github.com/aws-samples/amazon-neptune-samples)
