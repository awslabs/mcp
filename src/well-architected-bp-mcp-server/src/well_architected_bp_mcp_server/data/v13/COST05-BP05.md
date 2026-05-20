---
id: "COST05-BP05"
title: "Select components of this workload to optimize cost in line with organization priorities"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you evaluate cost when you select services?"
risk_level: "Medium"
---

# COST05-BP05 Select components of this workload to optimize cost in line with organization priorities

## Implementation Guidance
 Consider the cost of services and options when selecting all components. This includes using application level and managed services, such as [Amazon Relational Database Service](https://aws.amazon.com/rds/) (Amazon RDS), [Amazon DynamoDB](https://aws.amazon.com/dynamodb/), [Amazon Simple Notification Service](https://aws.amazon.com/sns/) (Amazon SNS), and [Amazon Simple Email Service](https://aws.amazon.com/ses/) (Amazon SES) to reduce overall organization cost.

 Use serverless and containers for compute, such as [AWS Lambda](https://aws.amazon.com/lambda/) and [Amazon Simple Storage Service](https://aws.amazon.com/s3/) (Amazon S3) for static websites. Containerize your application if possible and use AWS Managed Container Services such as [Amazon Elastic Container Service](https://aws.amazon.com/ecs/) (Amazon ECS) or [Amazon Elastic Kubernetes Service](https://aws.amazon.com/eks/) (Amazon EKS).

 Minimize license costs by using open-source software, or software that does not have license fees (for example, Amazon Linux for compute workloads or migrate databases to Amazon Aurora).

 You can use serverless or application-level services such as [Lambda](https://aws.amazon.com/lambda/), [Amazon Simple Queue Service (Amazon SQS)](https://aws.amazon.com/sqs/), [Amazon SNS](https://aws.amazon.com/sqs/), and [Amazon SES](https://aws.amazon.com/ses/). These services remove the need for you to manage a resource and provide the function of code execution, queuing services, and message delivery. The other benefit is that they scale in performance and cost in line with usage, allowing efficient cost allocation and attribution.

 Using [event-driven architecture](https://aws.amazon.com/what-is/eda/) is also possible with serverless services. Event-driven architectures are push-based, so everything happens on demand as the event presents itself in the router. This way, you’re not paying for continuous polling to check for an event. This means less network bandwidth consumption, less CPU utilization, less idle fleet capacity, and fewer SSL/TLS handshakes.

 For more information on serverless, see [Well-Architected Serverless Application lens whitepaper.](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/welcome.html)

## Implementation Steps
- **Select each service to optimize cost:** Using your prioritized list and analysis, select each option that provides the best match with your organizational priorities. Instead of increasing the capacity to meet the demand, consider other options which may give you better performance with lower cost. For example, if you need to review expected traffic for your databases on AWS, consider either increasing the instance size or using Amazon ElastiCache services (Redis or Memcached) to provide cached mechanisms for your databases.
- **Evaluate event-driven architecture:** Using serverless architecture also allows you to build event-driven architecture for distributed microservice-based applications, which helps you build scalable, resilient, agile and cost-effective solutions.

## Resources
### Related Documents
- [AWS Total Cost of Ownership (TCO) Calculator](https://aws.amazon.com/tco-calculator/)
- [AWS Serverless](https://aws.amazon.com/serverless/)
- [What is Event-Driven Architecture](https://aws.amazon.com/what-is/eda/)
- [Amazon S3 storage classes](https://aws.amazon.com/s3/storage-classes/)
- [Cloud products](https://aws.amazon.com/products/)
- [Amazon ElastiCache (Redis OSS)](https://aws.amazon.com/elasticache/redis)
### Related Examples
- [Getting started with event-driven architecture](https://aws.amazon.com/blogs/compute/getting-started-with-event-driven-architecture/)
- [Event-driven architecture](https://aws.amazon.com/event-driven-architecture/)
- [How Statsig runs 100x more cost-effectively using Amazon ElastiCache (Redis OSS)](https://aws.amazon.com/blogs/database/how-statsig-runs-100x-more-cost-effectively-using-amazon-elasticache-for-redis/)
- [Best practices for working with AWS Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
