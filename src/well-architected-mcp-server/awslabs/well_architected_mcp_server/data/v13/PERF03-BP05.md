---
id: "PERF03-BP05"
title: "Implement data access patterns that utilize caching"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you store, manage, and access data in your workload?"
risk_level: "Medium"
---

# PERF03-BP05 Implement data access patterns that utilize caching

## Anti-Patterns
- You cache data that changes frequently.
- You rely on cached data as if it is durably stored and always available.
- You don't consider the consistency of your cached data.
- You don't monitor the efficiency of your caching implementation.

## Implementation Guidance
 A cache is a software or hardware component aimed at storing data so that future requests for the same data can be served faster or more efficiently. The data stored in a cache can be reconstructed if lost by repeating an earlier calculation or fetching it from another data store.

 Data caching can be one of the most effective strategies to improve your overall application performance and reduce burden on your underlying primary data sources. Data can be cached at multiple levels in the application, such as within the application making remote calls, known as *client-side caching*, or by using a fast secondary service for storing the data, known as *remote caching*.

 **Client-side caching**

 With client-side caching, each client (an application or service that queries the backend datastore) can store the results of their unique queries locally for a specified amount of time. This can reduce the number of requests across the network to a datastore by checking the local client cache first. If the results are not present, the application can then query the datastore and store those results locally. This pattern allows each client to store data in the closest location possible (the client itself), resulting in the lowest possible latency. Clients can also continue to serve some queries when the backend datastore is unavailable, increasing the availability of the overall system.

 One disadvantage of this approach is that when multiple clients are involved, they may store the same cached data locally. This results in both duplicate storage usage and data inconsistency between those clients. One client might cache the results of a query, and one minute later another client can run the same query and get a different result.

 **Remote caching**

 To solve the issue of duplicate data between clients, a fast external service, or *remote cache*, can be used to store the queried data. Instead of checking a local data store, each client will check the remote cache before querying the backend datastore. This strategy allows for more consistent responses between clients, better efficiency in stored data, and a higher volume of cached data because the storage space scales independently of clients.

 The disadvantage of a remote cache is that the overall system may see a higher latency, as an additional network hop is required to check the remote cache. Client-side caching can be used alongside remote caching for multi-level caching to improve the latency.

## Implementation Steps
- Identify databases, APIs and network services that could benefit from caching. Services that have heavy read workloads, have a high read-to-write ratio, or are expensive to scale are candidates for caching.
  - [Database Caching](https://aws.amazon.com/caching/database-caching/)
  - [Enabling API caching to enhance responsiveness](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-caching.html)
- Identify the appropriate type of caching strategy that best fits your access pattern.
  - [Caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Strategies.html)
  - [AWS Caching Solutions](https://aws.amazon.com/caching/aws-caching/)
- Follow [Caching Best Practices](https://aws.amazon.com/caching/best-practices/) for your data store.
- Configure a cache invalidation strategy, such as a time-to-live (TTL), for all data that balances freshness of data and reducing pressure on backend datastore.
- Enable features such as automatic connection retries, exponential backoff, client-side timeouts, and connection pooling in the client, if available, as they can improve performance and reliability.
  - [Best practices: Redis clients and Amazon ElastiCache (Redis OSS)](https://aws.amazon.com/blogs/database/best-practices-redis-clients-and-amazon-elasticache-for-redis/)
- Monitor cache hit rate with a goal of 80% or higher. Lower values may indicate insufficient cache size or an access pattern that does not benefit from caching.
  - [Which metrics should I monitor?](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/CacheMetrics.WhichShouldIMonitor.html)
  - [Best practices for monitoring Redis workloads on Amazon ElastiCache](https://www.youtube.com/watch?v=c-hTMLN35BY)
  - [Monitoring best practices with Amazon ElastiCache (Redis OSS) using Amazon CloudWatch](https://aws.amazon.com/blogs/database/monitoring-best-practices-with-amazon-elasticache-for-redis-using-amazon-cloudwatch/)
- Implement [data replication](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Replication.Redis.Groups.html) to offload reads to multiple instances and improve data read performance and availability.

## Resources
### Related Documents
- [Using the Amazon ElastiCache Well-Architected Lens](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/WellArchitechtedLens.html)
- [Monitoring best practices with Amazon ElastiCache (Redis OSS) using Amazon CloudWatch](https://aws.amazon.com/blogs/database/monitoring-best-practices-with-amazon-elasticache-for-redis-using-amazon-cloudwatch/)
- [Which Metrics Should I Monitor?](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/CacheMetrics.WhichShouldIMonitor.html)
- [Performance at Scale with Amazon ElastiCache whitepaper](https://docs.aws.amazon.com/whitepapers/latest/scale-performance-elasticache/scale-performance-elasticache.html)
- [Caching challenges and strategies](https://aws.amazon.com/builders-library/caching-challenges-and-strategies/)
### Related Videos
- [Amazon ElastiCache Learning Path](https://pages.awscloud.com/GLB-WBNR-AWS-OTT-2021_LP_0003-DAT_AmazonElastiCache.html)
- [Design for success with Amazon ElastiCache best practices](https://youtu.be/_4SkEy6r-C4)
- [AWS re:Invent 2020 - Design for success with Amazon ElastiCache best practices ](https://www.youtube.com/watch?v=_4SkEy6r-C4)
- [AWS re:Invent 2023 - [LAUNCH] Introducing Amazon ElastiCache Serverless ](https://www.youtube.com/watch?v=YYStP97pbXo)
- [AWS re:Invent 2022 - 5 great ways to reimagine your data layer with Redis ](https://www.youtube.com/watch?v=CD1kvauvKII)
- [AWS re:Invent 2021 - Deep dive on Amazon ElastiCache (Redis OSS) ](https://www.youtube.com/watch?v=QEKDpToureQ)
### Related Examples
- [Boosting MySQL database performance with Amazon ElastiCache (Redis OSS)](https://aws.amazon.com/getting-started/hands-on/boosting-mysql-database-performance-with-amazon-elasticache-for-redis/)
