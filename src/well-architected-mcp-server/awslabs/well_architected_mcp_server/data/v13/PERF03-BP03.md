---
id: "PERF03-BP03"
title: "Collect and record data store performance metrics"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you store, manage, and access data in your workload?"
risk_level: "High"
---

# PERF03-BP03 Collect and record data store performance metrics

## Anti-Patterns
- You only use manual log file searching for metrics.
- You only publish metrics to internal tools used by your team and don’t have a comprehensive picture of your workload.
- You only use the default metrics recorded by your selected monitoring software.
- You only review metrics when there is an issue.
- You only monitor system-level metrics and do not capture data access or usage metrics.

## Implementation Guidance
 To monitor the performance of your data stores, you must record multiple performance metrics over a period of time. This allows you to detect anomalies, as well as measure performance against business metrics to verify you are meeting your workload needs.

 Metrics should include both the underlying system that is supporting the data store and the database metrics. The underlying system metrics might include CPU utilization, memory, available disk storage, disk I/O, cache hit ratio, and network inbound and outbound metrics, while the data store metrics might include transactions per second, top queries, average queries rates, response times, index usage, table locks, query timeouts, and number of connections open. This data is crucial to understand how the workload is performing and how the data management solution is used. Use these metrics as part of a data-driven approach to tune and optimize your workload's resources.

 Use tools, libraries, and systems that record performance measurements related to database performance.

## Implementation Steps
- Identify the key performance metrics for your data store to track.
  - [Amazon S3 Metrics and dimensions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/metrics-dimensions.html)
  - [Monitoring metrics for in an Amazon RDS instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Monitoring.html)
  - [Monitoring DB load with Performance Insights on Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.html)
  - [Overview of Enhanced Monitoring](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_Monitoring.OS.overview.html)
  - [DynamoDB Metrics and dimensions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html)
  - [Monitoring DynamoDB Accelerator](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.Monitoring.html)
  - [Monitoring Amazon MemoryDB with Amazon CloudWatch](https://docs.aws.amazon.com/memorydb/latest/devguide/monitoring-cloudwatch.html)
  - [Which Metrics Should I Monitor?](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/CacheMetrics.WhichShouldIMonitor.html)
  - [Monitoring Amazon Redshift cluster performance](https://docs.aws.amazon.com/redshift/latest/mgmt/metrics.html)
  - [Timestream metrics and dimensions](https://docs.aws.amazon.com/timestream/latest/developerguide/metrics-dimensions.html)
  - [Amazon CloudWatch metrics for Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraMonitoring.Metrics.html)
  - [Logging and monitoring in Amazon Keyspaces (for Apache Cassandra)](https://docs.aws.amazon.com/keyspaces/latest/devguide/monitoring.html)
  - [Monitoring Amazon Neptune Resources](https://docs.aws.amazon.com/neptune/latest/userguide/monitoring.html)
- Use an approved logging and monitoring solution to collect these metrics. [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) can collect metrics across the resources in your architecture. You can also collect and publish custom metrics to surface business or derived metrics. Use CloudWatch or third-party solutions to set alarms that indicate when thresholds are breached.
- Check if data store monitoring can benefit from a machine learning solution that detects performance anomalies.
  - [Amazon DevOps Guru for Amazon RDS](https://docs.aws.amazon.com/devops-guru/latest/userguide/working-with-rds.overview.how-it-works.html) provides visibility into performance issues and makes recommendations for corrective actions.
- Configure data retention in your monitoring and logging solution to match your security and operational goals.
  - [Default data retention for CloudWatch metrics](https://aws.amazon.com/cloudwatch/faqs/#AWS_resource_.26_custom_metrics_monitoring)
  - [Default data retention for CloudWatch Logs](https://aws.amazon.com/cloudwatch/faqs/#Log_management)

## Resources
### Related Documents
- [AWS Database Caching](https://aws.amazon.com/caching/database-caching/)
- [Amazon Athena top 10 performance tips](https://aws.amazon.com/blogs/big-data/top-10-performance-tuning-tips-for-amazon-athena/)
- [Amazon Aurora best practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Aurora.BestPractices.html)
- [DynamoDB Accelerator](https://aws.amazon.com/dynamodb/dax/)
- [Amazon DynamoDB best practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BestPractices.html)
- [Amazon Redshift Spectrum best practices](https://aws.amazon.com/blogs/big-data/10-best-practices-for-amazon-redshift-spectrum/)
- [Amazon Redshift performance](https://docs.aws.amazon.com/redshift/latest/dg/c_challenges_achieving_high_performance_queries.html)
- [Cloud Databases with AWS](https://aws.amazon.com/products/databases/)
- [Amazon RDS Performance Insights](https://aws.amazon.com/rds/performance-insights/)
### Related Videos
- [AWS re:Invent 2022 - Performance monitoring with Amazon RDS and Aurora, featuring Autodesk ](https://www.youtube.com/watch?v=wokRbwK4YLo)
- [ Database Performance Monitoring and Tuning with Amazon DevOps Guru for Amazon RDS ](https://www.youtube.com/watch?v=cHKuVH7YGBE)
- [AWS re:Invent 2023 - What’s new with AWS file storage ](https://www.youtube.com/watch?v=yXIeIKlTFV0)
- [AWS re:Invent 2023 - Dive deep into Amazon DynamoDB ](https://www.youtube.com/watch?v=ld-xoehkJuU)
- [AWS re:Invent 2023 - Building and optimizing a data lake on Amazon S3 ](https://www.youtube.com/watch?v=mpQa_Zm1xW8)
- [AWS re:Invent 2023 - What’s new with AWS file storage ](https://www.youtube.com/watch?v=yXIeIKlTFV0)
- [AWS re:Invent 2023 - Dive deep into Amazon DynamoDB ](https://www.youtube.com/watch?v=ld-xoehkJuU)
- [Best Practices for Monitoring Redis Workloads on Amazon ElastiCache](https://www.youtube.com/watch?v=c-hTMLN35BY&ab_channel=AWSOnlineTechTalks)
### Related Examples
- [AWS Dataset Ingestion Metrics Collection Framework](https://github.com/awslabs/aws-dataset-ingestion-metrics-collection-framework)
- [Amazon RDS Monitoring Workshop](https://www.workshops.aws/?tag=Enhanced%20Monitoring)
- [AWS Purpose Built Databases Workshop ](https://catalog.us-east-1.prod.workshops.aws/workshops/93f64257-52be-4c12-a95b-c0a1ff3b7e2b/en-US)
