---
id: "PERF01-BP04"
title: "Evaluate how trade-offs impact customers and architecture efficiency"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you select appropriate cloud resources and architecture for your workload?"
risk_level: "High"
---

# PERF01-BP04 Evaluate how trade-offs impact customers and architecture efficiency

## Anti-Patterns
- You assume that all performance gains should be implemented, even if there are tradeoffs for implementation.
- You only evaluate changes to workloads when a performance issue has reached a critical point.

## Implementation Guidance
 Identify critical areas in your architecture in terms of performance and customer impact. Determine how you can make improvements, what trade-offs those improvements bring, and how they impact the system and the user experience. For example, implementing caching data can help dramatically improve performance but requires a clear strategy for how and when to update or invalidate cached data to prevent incorrect system behavior.

## Implementation Steps
- Understand your workload requirements and SLAs.
- Clearly define evaluation factors. Factors may relate to cost, reliability, security, and performance of your workload.
- Select architecture and services that can address your requirements.
- Conduct experimentation and proof of concepts (POCs) to evaluate trade-off factors and impact on customers and architecture efficiency. Usually, highly-available, performant, and secure workloads consume more cloud resources while providing better customer experience. Understand the trade-offs across your workload’s complexity, performance, and cost. Typically, prioritizing two of the factors comes at the expense of the third.

## Resources
### Related Documents
- [Amazon Builders’ Library](https://aws.amazon.com/builders-library)
- [Quick Suite KPIs](https://docs.aws.amazon.com/quicksight/latest/user/kpi.html)
- [Amazon CloudWatch RUM](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html)
- [X-Ray Documentation](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
- [ Understand resiliency patterns and trade-offs to architect efficiently in the cloud ](https://aws.amazon.com/blogs/architecture/understand-resiliency-patterns-and-trade-offs-to-architect-efficiently-in-the-cloud/)
### Related Videos
- [Optimize applications through Amazon CloudWatch RUM](https://www.youtube.com/watch?v=NMaeujY9A9Y)
- [AWS re:Invent 2023 - Capacity, availability, cost efficiency: Pick three ](https://www.youtube.com/watch?v=E0dYLPXrX_w)
- [AWS re:Invent 2023 - Advanced integration patterns & trade-offs for loosely coupled systems ](https://www.youtube.com/watch?v=FGKGdUiZKto)
### Related Examples
- [Measure page load time with Amazon CloudWatch Synthetics](https://github.com/aws-samples/amazon-cloudwatch-synthetics-page-performance)
- [Amazon CloudWatch RUM Web Client](https://github.com/aws-observability/aws-rum-web)
