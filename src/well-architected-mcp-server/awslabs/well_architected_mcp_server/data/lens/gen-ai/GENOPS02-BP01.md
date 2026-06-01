---
id: "GENOPS02-BP01"
title: "Monitor all application layers"
pillar: "Operational Excellence"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genops02-bp01.html"
---

# GENOPS02-BP01 Monitor all application layers

Implement comprehensive monitoring and logging across all layers of
your generative AI application to maintain operational health,
provide reliability, and optimize performance. This best practice
aims to provide clear visibility into the application's behavior, from user interactions to core model performance. By
tracking key metrics, organizations can quickly identify and address
issues, enhance user experiences, and make data-driven decisions to
improve their AI systems.

**Desired outcome:** When
implemented, your organization closely monitors the performance of
generative AI workloads.

**Benefits of establishing this best
practice:**

- [Implement
observability for actionable insights](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - Monitor the
performance of your generative AI workload at all layers of the
application, increasing visibility into application operational
state and facilitating the early intervention of operational
issues.
- [Learn
from all operational events and metrics](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - Capturing
fine-grained observations enables continuous improvement.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Generative AI applications have several layers. First and foremost
is the application layer, which is the software abstraction above
a foundation model. Then, there is a service layer, an optional
gateway that negotiates prompts and brokers responses back to the
application layer. Depending on the use case, the service layer
may interact with a prompt catalog, a vector data store, or
several guardrails before ultimately interacting with a foundation
model. Simple generative AI workloads may respond back to the
service layer and apply configured guardrails where appropriate
before ultimately responding back at the application layer. More
complex workloads may navigate a knowledge graph, run a prompt
flow, or initiate an agent. The different layers and scenarios for
a generative AI application to traverse require proactive
monitoring and application telemetry at each layer.

Managed services like Amazon Bedrock, Amazon Q Business, and
Amazon OpenSearch Service Serverless facilitate much of this
monitoring on your behalf. These managed services integrate
well with monitoring and logging services like Amazon CloudWatch and AWS CloudTrail. Amazon SageMaker AI Inference
Endpoints can also log to CloudWatch. Evaluate different
logging solutions that best suit your needs, and implement
monitoring at each layer of your custom generative AI
workflow. These considerations should also be applied to
generative business intelligence (BI) solutions Quick Q. Monitor the appropriate Quick Q
metrics to identify operational issues when serving generative
BI insights.

In SageMaker AI HyperPod with both Amazon EKS and Slurm
orchestration, establish comprehensive observability across
infrastructure, service, application, and model performance
layers using SageMaker AI HyperPod's built-in observability
capabilities and AWS monitoring services.

For EKS-based HyperPod, use the one-click observability
feature that automatically installs Amazon EKS add-ons for
consolidated health and performance data from multiple sources
including NVIDIA DCGM, Kubernetes node exporters, Elastic
Fabric Adapter (EFA), and file systems, all accessible through
unified dashboards in Amazon Managed Grafana with metrics
automatically published to Amazon Managed Service for Prometheus.

Configure CloudWatch Container Insights for enhanced
observability of CPU, GPU, Trainium, EFA, and file system
metrics up to the container level, while implementing deep
health checks and automated node recovery monitoring that
tracks schedulable and unschedulable node status.

For Slurm-based HyperPod, implement comprehensive monitoring
through node exporters for CPU load averages, memory, disk
usage, network traffic, and file system metrics, NVIDIA DCGM
for GPU utilization, temperatures, power usage, and memory
monitoring, and EFA metrics for network performance and error
tracking.

Both systems benefit from SageMaker AI HyperPod's unified
observability solution that reduces troubleshooting time from
days to minutes through pre-built actionable insights,
real-time task performance metric tracking with automated
alerting, and automatic root cause remediation with
customer-defined policies, providing comprehensive visibility
into training job performance, resource utilization, and
system health across operational layers.

### Implementation steps

- Identify your application layers, including:

Application layer
- Service layer
- Foundation model layer
- Additional layers (for example, prompt catalog, vector
data store, or knowledge graph)

- For application layer monitoring:

Enable logs and metrics in Amazon CloudWatch
- For custom metrics, set up for application-specific
events and performance indicators

- For service layer monitoring:

Enable logs and metrics in Amazon CloudWatch
- For request flow analysis, implement tracing with AWS X-Ray or use Amazon Bedrock Agent's tracing feature

- For foundation model layer monitoring:

Use built-in monitoring in Amazon Bedrock or Amazon Q Business
- Configure CloudWatch logging for Amazon SageMaker AI
Inference Endpoints

- For additional layer monitoring:

Enable logs and metrics in your chosen vector database,
such as Amazon OpenSearch Service
- Set up CloudWatch logs and metrics for prompt catalogs
or knowledge graphs

- Configure alerting and dashboards.

Set up CloudWatch alarms for critical metrics and
thresholds
- Create CloudWatch dashboards for key performance
indicators

- Configure security monitoring.

Enable AWS CloudTrail for API activity logging
- Set up Amazon GuardDuty for threat detection

- Continually optimize.

Review and analyze log data to identify improvements
- Adjust monitoring configurations based on changing
application needs and usage patterns

- Consider additional logging solutions:

For log ingestion and transformation, consider Amazon Data Firehose
- For as-needed querying, explore Amazon Athena for logs
stored in Amazon S3

## Resources

Related best practices:

- OPS08-BP01
- OPS08-BP02
- OPS08-BP03
- OPS08-BP04
- OPS08-BP05

**Related documents:**

- [Using
Amazon CloudWatch Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html)
- [Using
Amazon CloudWatch Dashboards](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html)
- [Amazon CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html)
- [CloudWatch Logs Insights Query Examples](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-examples.html)
- [Publishing
Custom Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html)

**Related examples:**

- [Monitor
the health and performance of Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring.html)
- [Metrics
for monitoring Amazon SageMaker AI with Amazon CloudWatch](https://docs.aws.amazon.com/sagemaker/latest/dg/monitoring-cloudwatch.html)
- [Monitoring
OpenSearch Serverless with Amazon CloudWatch](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/monitoring-cloudwatch.html)
- [Monitoring
Amazon Q Business and Amazon Q Apps with Amazon CloudWatch](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/monitoring-cloudwatch.html)
- [Monitoring
Amazon Q Developer with Amazon CloudWatch](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/monitoring-cloudwatch.html)
- [Accelerate
Foundation Model Development with One-Click Observability in
Amazon SageMaker AI HyperPod](https://aws.amazon.com/blogs/machine-learning/accelerate-foundation-model-development-with-one-click-observability-in-amazon-sagemaker-hyperpod/)
- [Amazon SageMaker AI HyperPod launches model deployments to accelerate
the generative AI model development lifecycle](https://aws.amazon.com/blogs/machine-learning/amazon-sagemaker-hyperpod-launches-model-deployments-to-accelerate-the-generative-ai-model-development-lifecycle/)

**Related tools:**

- [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/)
- [AWS CloudTrail](https://aws.amazon.com/cloudtrail/)
- [Amazon SageMaker AI Model Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html)
- [Amazon Data Firehose](https://docs.aws.amazon.com/firehose/latest/dev/what-is-this-service.html)
- [Amazon Athena](https://aws.amazon.com/athena/)
- [Amazon GuardDuty](https://aws.amazon.com/guardduty/)
- [Amazon OpenSearch Service Serverless](https://aws.amazon.com/opensearch-service/features/serverless/)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [Amazon Q](https://aws.amazon.com/q/)
