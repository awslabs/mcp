---
id: "GENSEC03-BP01"
title: "Implement control plane and data access monitoring to generative AI services and foundation models"
pillar: "Security"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec03-bp01.html"
---

# GENSEC03-BP01 Implement control plane and data access monitoring to generative AI services and foundation models

Implement comprehensive monitoring across both control and data
planes to enhance the protection of generative AI workloads against
service-level misconfigurations. This monitoring and auditing
approach enables tracking of key aspects such as application
performance, workload quality, and security.

**Desired outcome:** When
implemented, you can track the changes made to generative AI
services and infrastructure, as well as changes to relevant data
stores.

**Benefits of establishing this best
practice:**
[Apply
security at all layers](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - Control and data plane monitoring
provides a layer of security at the service configuration and data
access layers.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Monitoring at the control plane and data layers should track
data access, as well as control plane API requests to the
services in question. Most cloud-based systems publish these
events over an event bus for capture, storage, and eventual
analysis. These capabilities are considered normal within a
modern data architecture. As data and AI workloads become more
closely intertwined in your organization, solutions like
Amazon SageMaker AI and its new Lakehouse capability help
simplify the collection and capturing of data access requests
by models, workloads, and users. Your organization AI policy
document should define how data access requests are captured
and monitored across your environment.

Consider AWS CloudTrail to record management and data events.
Amazon Bedrock, Amazon Q Business, and other generative AI
services integrate with CloudTrail and can be used to record
control plane operations like custom model import and runtime
operations like invokeAgent. Amazon CloudWatch can be
configured to capture logs for generative AI applications as
well. A combination of these AWS services or the use of a
third-party logging solution, if needed, improves visibility
into application security. CloudWatch and CloudTrail integrate
well with other managed AWS services powered by data, such
Quick Q, a generative business intelligence (BI)
tool.

### Implementation steps

- Performance monitoring:

Track response times, latency, and throughput of model
inference
- Monitor resource utilization (CPU, GPU, and memory)
- Measure token usage and request volumes
- Track batch processing efficiency and queue lengths
- Monitor model loading and unloading times

- Quality and accuracy monitoring:

Track completion rates and success ratios
- Monitor response quality scores
- Implement content safety measurements
- Track hallucination rates and accuracy metrics
- Monitor prompt effectiveness and completion relevance

- Security monitoring:

Track authentication and authorization attempts
- Monitor for potential prompt injection exploits
- Log access patterns and unusual behaviors
- Track rate limiting and quota usage
- Monitor for potential data leakage

- Cost monitoring:

Track token usage and associated costs
- Monitor resource utilization costs
- Track API call volumes and expenses
- Monitor storage and data transfer costs
- Track model deployment and training costs

- Audit trail implementation:

Maintain detailed logs of requests and responses
- Record user interactions and system changes
- Log model version changes and updates
- Track configuration modifications
- Maintain compliance-related audit trails

- Compliance monitoring:

Track data retention compliance
- Monitor PII handling and protection
- Verify regulatory requirement adherence
- Track consent management
- Monitor geographic data restrictions

## Resources

**Related best practices:**

- SEC04-BP01

**Related documents:**

- [AWS CloudTrail Data Events](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html#logging-data-events)
- [AWS CloudTrail Management Events](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-management-events-with-cloudtrail.html)

**Related examples:**

- [Gain
Insights with Natural Language Query into your AWS environment
using Amazon CloudTrail and Amazon Q in QuickSight](https://aws.amazon.com/blogs/mt/gain-insights-with-natural-language-query-into-your-aws-environment-using-amazon-cloudtrail-and-amazon-q-in-quicksight/)
- [Auditing
generative AI workloads with AWS CloudTrail](https://aws.amazon.com/blogs/mt/auditing-generative-ai-workloads-with-aws-cloudtrail/)
