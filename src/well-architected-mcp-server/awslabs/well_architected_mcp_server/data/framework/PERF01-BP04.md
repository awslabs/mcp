---
id: "PERF01-BP04"
title: "Evaluate how trade-offs impact customers and architecture efficiency"
pillar: "Performance Efficiency"
risk_level: "HIGH"
capability: "How do you select appropriate cloud resources and architecture for your workload?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_architecture_evaluate_trade_offs.html"
---

# PERF01-BP04 Evaluate how trade-offs impact customers and architecture efficiency

When evaluating performance-related improvements, determine which
choices impact your customers and workload efficiency. For example,
if using a key-value data store increases system performance, it is
important to evaluate how the eventually consistent nature of this
change will impact customers.

**Common anti-patterns:**

- You assume that all performance gains should be implemented,
even if there are tradeoffs for implementation.
- You only evaluate changes to workloads when a performance issue
has reached a critical point.

**Benefits of establishing this best
practice:** When you are evaluating potential
performance-related improvements, you must decide if the tradeoffs
for the changes are acceptable with the workload requirements. In
some cases, you may have to implement additional controls to
compensate for the tradeoffs.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Identify critical areas in your architecture in terms of
performance and customer impact. Determine how you can make
improvements, what trade-offs those improvements bring, and how
they impact the system and the user experience. For example,
implementing caching data can help dramatically improve
performance but requires a clear strategy for how and when to
update or invalidate cached data to prevent incorrect system
behavior.

### Implementation steps

- Understand your workload requirements and SLAs.
- Clearly define evaluation factors. Factors may relate to
cost, reliability, security, and performance of your workload.
- Select architecture and services that can address your
requirements.
- Conduct experimentation and proof of concepts (POCs) to
evaluate trade-off factors and impact on customers and
architecture efficiency. Usually, highly-available,
performant, and secure workloads consume more cloud
resources while providing better customer experience. Understand the trade-offs across your workload’s complexity, performance, and cost.
Typically, prioritizing two of the factors comes at the expense of the third.

## Resources

**Related documents:**

- [Amazon
Builders’ Library](https://aws.amazon.com/builders-library)
- [Quick KPIs](https://docs.aws.amazon.com/quicksight/latest/user/kpi.html)
- [Amazon CloudWatch RUM](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html)
- [X-Ray
Documentation](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
- [Understand resiliency patterns and trade-offs to architect efficiently in the cloud](https://aws.amazon.com/blogs/architecture/understand-resiliency-patterns-and-trade-offs-to-architect-efficiently-in-the-cloud/)

**Related videos:**

- [Optimize
applications through Amazon CloudWatch RUM](https://www.youtube.com/watch?v=NMaeujY9A9Y)
- [AWS re:Invent 2023 - Capacity, availability, cost efficiency: Pick three](https://www.youtube.com/watch?v=E0dYLPXrX_w)
- [AWS re:Invent 2023 - Advanced integration patterns & trade-offs for loosely coupled systems](https://www.youtube.com/watch?v=FGKGdUiZKto)

**Related examples:**

- [Measure
page load time with Amazon CloudWatch Synthetics](https://github.com/aws-samples/amazon-cloudwatch-synthetics-page-performance)
- [Amazon CloudWatch RUM Web Client](https://github.com/aws-observability/aws-rum-web)
