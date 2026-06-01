---
id: "GENREL01-BP01"
title: "Scale and balance foundation model throughput as a function of utilization"
pillar: "Reliability"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genrel01-bp01.html"
---

# GENREL01-BP01 Scale and balance foundation model throughput as a function of utilization

Collect information on the generative AI workload's utilization,
and implement dynamic scaling strategies to match capacity with
demand. Use this information to determine the required
throughput for your foundation model and establish appropriate
quotas and scaling policies.

**Desired outcome:** When
implemented, this best practice improves the reliability of your
generative AI workload by matching the configured or provisioned
throughput to your foundation models to the workload's demand.
This results in optimal resource utilization and consistent
performance under varying loads.

**Benefits of establishing this best
practice:**
[Stop
guessing capacity](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html) - By understanding the throughput needs
of your generative AI workload, you remove the need to guess at
throughput capacity.

**Level of risk exposed if this best
practice is not established:** Medium

## Implementation guidance

When managing throughput for foundation models, consider
implementing a comprehensive monitoring and scaling strategy.
Use a robust monitoring system that provides detailed insights
for tracking throughput metrics and creating alarms for quota
utilization.

To handle traffic spikes and maintain consistent performance,
implement request buffering using a message queue service,
which can help smooth out irregular traffic patterns and avoid
overwhelming the model endpoints. Use a service quota
management system to adjust service limits based on your
workload requirements, while implementing auto-scaling
mechanisms to enable dynamic capacity management based on
demand.

Consider placing queues between generative AI applications and
models so that models do not deny or drop requests due to
throughput constraints. This architecture lends itself to
event-driven messaging patterns, making it a particularly
robust option for architectures with high demand.

For handling common throughput bottlenecks, consider
implementing token bucket algorithms for rate limiting or
using provisioned throughput options when dealing with token
rate limits. To address concurrent request limits, implement
request queuing or distribute requests across multiple
Regions. For model loading overhead, maintain a warm pool of
model instances or implement model caching strategies. Each of
these solutions should be monitored for effectiveness using
your chosen metrics and monitoring system.

Provisioned Throughput endpoints or cross-Region inference
profiles on Amazon Bedrock may help to alleviate scaling
bottlenecks for fully-managed inference hosting. Provisioned
Throughput provides dedicated infrastructure that can achieve
higher, more stable throughput than allowed through default
quotas for on demand models hosted on Amazon Bedrock.
Provisioned Throughput capacity can be monitored in Amazon CloudWatch, which helps you proactively scale when capacity
nears critical thresholds.

Cross-Region inference profiles distribute inference demand
over a region of availability. For model endpoints hosted on
Amazon SageMaker AI Inference Endpoints, consider using
traditional throughput scaling techniques like EC2 Autoscaling
groups behind a load balancer. If your increased throughput
needs are periodic and predictable, consider deploying larger
instance types in advance of the increased need. Ultimately,
it is encouraged to proactively engage with AWS support to
increase service quotas based on known workload demands.

### Implementation steps

- Set up comprehensive monitoring using CloudWatch:

Create custom dashboards for throughput metrics
- Configure alarms for quota utilization
- Enable detailed monitoring for critical resources

- Implement request management:

Deploy queue-based architecture for request buffering
- Set up rate limiting at the application layer
- Configure retry mechanisms with exponential backoff

- Configure scaling mechanisms:

Set up auto-scaling policies based on demand
- Configure provisioned throughput where appropriate
- Implement cross-region request distribution

- Establish ongoing optimization:

Regular review of utilization patterns
- Periodic adjustment of quotas and scaling parameters
- Continuous monitoring and refinement of thresholds

## Resources

**Related best practices:**

- [REL01-BP01](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_manage_service_limits_aware_quotas_and_constraints.html)
- [REL01-BP02](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_manage_service_limits_limits_considered.html)
- [REL01-BP03](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_manage_service_limits_aware_fixed_limits.html)

**Related documents:**

- [Increase throughput with cross-Region inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html)
- [Increase model invocation capacity with Provisioned Throughput in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/prov-throughput.html)

**Related examples:**

- [Enable
Amazon Bedrock cross-Region inference in multi-account
environments](https://aws.amazon.com/blogs/machine-learning/enable-amazon-bedrock-cross-region-inference-in-multi-account-environments/)
- [Building
well-architected serverless applications: Regulating inbound
request rates – part 1](https://aws.amazon.com/blogs/compute/building-well-architected-serverless-applications-regulating-inbound-request-rates-part-1/)
- [Getting Started with cross-Region inference in Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/getting-started-with-cross-region-inference-in-amazon-bedrock/)
