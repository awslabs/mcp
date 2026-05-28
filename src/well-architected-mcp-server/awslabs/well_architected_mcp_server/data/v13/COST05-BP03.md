---
id: "COST05-BP03"
title: "Perform a thorough analysis of each component"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you evaluate cost when you select services?"
risk_level: "High"
---

# COST05-BP03 Perform a thorough analysis of each component

## Implementation Guidance
 Consider the time savings that will allow your team to focus on retiring technical debt, innovation, value-adding features and building what differentiates the business. For example, you might need to lift and shift (also known as rehost) your databases from your on-premises environment to the cloud as rapidly as possible and optimize later. It is worth exploring the possible savings attained by using managed services on AWS that may remove or reduce license costs. Managed services on AWS remove the operational and administrative burden of maintaining a service, such as patching or upgrading the OS, and allow you to focus on innovation and business.

 Since managed services operate at cloud scale, they can offer a lower cost per transaction or service. You can make potential optimizations in order to achieve some tangible benefit, without changing the core architecture of the application. For example, you may be looking to reduce the amount of time you spend managing database instances by migrating to a database-as-a-service platform like [Amazon Relational Database Service (Amazon RDS)](https://aws.amazon.com/rds/) or migrating your application to a fully managed platform like [AWS Elastic Beanstalk](https://aws.amazon.com/elasticbeanstalk/).

Usually, managed services have attributes that you can set to ensure sufficient capacity. You must set and monitor these attributes so that your excess capacity is kept to a minimum and performance is maximized. You can modify the attributes of AWS Managed Services using the AWS Management Console or AWS APIs and SDKs to align resource needs with changing demand. For example, you can increase or decrease the number of nodes on an Amazon EMR cluster (or an Amazon Redshift cluster) to scale out or in.

You can also pack multiple instances on an AWS resource to activate higher density usage. For example, you can provision multiple small databases on a single Amazon Relational Database Service (Amazon RDS) database instance. As usage grows, you can migrate one of the databases to a dedicated Amazon RDS database instance using a snapshot and restore process.

When provisioning workloads on managed services, you must understand the requirements of adjusting the service capacity. These requirements are typically time, effort, and any impact to normal workload operation. The provisioned resource must allow time for any changes to occur, provision the required overhead to allow this. The ongoing effort required to modify services can be reduced to virtually zero by using APIs and SDKs that are integrated with system and monitoring tools, such as Amazon CloudWatch.

[Amazon RDS](https://aws.amazon.com/rds/), [Amazon Redshift](https://aws.amazon.com/redshift/), and [Amazon ElastiCache](https://aws.amazon.com/elasticache/) provide a managed database service. [Amazon Athena](https://aws.amazon.com/athena/), [Amazon EMR](https://aws.amazon.com/emr/), and [Amazon OpenSearch Service](https://aws.amazon.com/opensearch-service/) provide a managed analytics service.

[AMS](https://aws.amazon.com/managed-services/) is a service that operates AWS infrastructure on behalf of enterprise customers and partners. It provides a secure and compliant environment that you can deploy your workloads onto. AMS uses enterprise cloud operating models with automation to allow you to meet your organization requirements, move into the cloud faster, and reduce your on-going management costs.

## Implementation Steps
- ** Perform a thorough analysis: **Using the component list, work through each component from the highest priority to the lowest priority. For the higher priority and more costly components, perform additional analysis and assess all available options and their long term impact. For lower priority components, assess if changes in usage would change the priority of the component, and then perform an analysis of appropriate effort.
- **Compare managed and unmanaged resources:** Consider the operational cost for the resources you manage and compare them with AWS managed resources. For example, review your databases running on Amazon EC2 instances and compare with Amazon RDS options (an AWS managed service) or Amazon EMR compared to running Apache Spark on Amazon EC2. When moving from a self-managed workload to a AWS fully managed workload, research your options carefully. The three most important factors to consider are the [type of managed service](https://aws.amazon.com/products/?&aws-products-all.q=managed) you want to use, the process you will use to [migrate your data](https://aws.amazon.com/big-data/datalakes-and-analytics/migrations/) and understand the [AWS shared responsibility model](https://aws.amazon.com/compliance/shared-responsibility-model/).

## Resources
### Related Documents
- [AWS Total Cost of Ownership (TCO) Calculator](https://aws.amazon.com/tco-calculator/)
- [Amazon S3 storage classes](https://aws.amazon.com/s3/storage-classes/)
- [AWS Cloud products](https://aws.amazon.com/products/)
- [AWS Shared Responsibility Model ](https://aws.amazon.com/compliance/shared-responsibility-model/)
### Related Videos
- [ Why move to a managed database? ](https://www.youtube.com/watch?v=VRFdc-MVa4I)
- [ What is Amazon EMR and how can I use it for processing data? ](https://www.youtube.com/watch?v=jylp2atrZjc)
### Related Examples
- [ Why to move to a managed database ](https://aws.amazon.com/getting-started/hands-on/move-to-managed/why-move-to-a-managed-database/)
- [ Consolidate data from identical SQL Server databases into a single Amazon RDS for SQL Server database using AWS DMS](https://aws.amazon.com/blogs/database/consolidate-data-from-identical-sql-server-databases-into-a-single-amazon-rds-for-sql-server-database-using-aws-dms/)
- [ Deliver data at scale to Amazon Managed Streaming for Apache Kafka (Amazon MSK) ](https://aws.amazon.com/getting-started/hands-on/deliver-data-at-scale-to-amazon-msk-with-iot-core/?ref=gsrchandson)
- [ Migrate an ASP.NET web application to AWS Elastic Beanstalk](https://aws.amazon.com/getting-started/hands-on/migrate-aspnet-web-application-elastic-beanstalk/?ref=gsrchandson&id=itprohandson)
