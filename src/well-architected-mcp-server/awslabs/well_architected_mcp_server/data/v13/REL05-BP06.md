---
id: "REL05-BP06"
title: "Make systems stateless where possible"
framework: "WAF"
domain: "Reliability"
capability: "How do you design interactions in a distributed system to mitigate or withstand failures?"
risk_level: "Medium"
---

# REL05-BP06 Make systems stateless where possible

## Implementation Guidance
 Make your applications stateless. Stateless applications allow horizontal scaling and are tolerant to the failure of an individual node. Analyze and understand the components of your application that maintain state within the architecture. This helps you assess the potential impact of transitioning to a stateless design. A stateless architecture decouples user data and offloads the session data. This provides the flexibility to scale each component independently to meet varying workload demands and optimize resource utilization.

## Implementation Steps
- Identify and understand the stateful components in your application.
- Decouple data by separating and managing user data from the core application logic.
  - [Amazon Cognito](https://aws.amazon.com/cognito/) can decouple user data from application code by using features, such as [identity pools](https://docs.aws.amazon.com/cognito/latest/developerguide/getting-started-with-identity-pools.html), [user pools](https://docs.aws.amazon.com/cognito/latest/developerguide/getting-started-with-cognito-user-pools.html), and [Amazon Cognito Sync](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-sync.html).
  - You can use [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/) decouple user data by storing secrets in a secure, centralized location. This means that the application code doesn't need to store secrets, which makes it more secure.
  - Consider using [Amazon S3](https://aws.amazon.com/s3/) to store large, unstructured data, such as images and documents. Your application can retrieve this data when required, eliminating the need to store it in memory.
  - Use [Amazon DynamoDB](https://aws.amazon.com/dynamodb/) to store information such as user profiles. Your application can query this data in near-real time.
- Offload session data to a database, cache, or external files.
  - [Amazon ElastiCache](https://aws.amazon.com/elasticache/), Amazon DynamoDB, [Amazon Elastic File System](https://aws.amazon.com/efs/) (Amazon EFS), and [Amazon MemoryDB](https://aws.amazon.com/memorydb/) are examples of AWS services that you can use to offload session data.
- Design a stateless architecture after you identify which state and user data need to be persisted with your storage solution of choice.

## Resources
### Related Best Practices
- [REL11-BP03 Automate healing on all layers](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_auto_healing_system.html)
### Related Documents
- [The Amazon Builders' Library: Avoiding fallback in distributed systems](https://aws.amazon.com/builders-library/avoiding-fallback-in-distributed-systems)
- [The Amazon Builders' Library: Avoiding insurmountable queue backlogs](https://aws.amazon.com/builders-library/avoiding-insurmountable-queue-backlogs)
- [The Amazon Builders' Library: Caching challenges and strategies](https://aws.amazon.com/builders-library/caching-challenges-and-strategies/)
- [Best Practices for Stateless Web Tier on AWS](https://docs.aws.amazon.com/whitepapers/latest/best-practices-wordpress/stateless-web-tier.html)
