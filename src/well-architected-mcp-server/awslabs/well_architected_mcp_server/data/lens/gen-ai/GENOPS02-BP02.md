---
id: "GENOPS02-BP02"
title: "Monitor foundation model metrics"
pillar: "Operational Excellence"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genops02-bp02.html"
---

# GENOPS02-BP02 Monitor foundation model metrics

It's critical to set up continuous monitoring and alerting for
foundation models for performance, security, and cost-efficiency.
This best practice offers a structured approach to monitor models
that fosters rapid identification and resolution of issues like data
drift, model degradation, and security threats. Adopting this
practice enhances reliability, efficiency, and trust in your
applications, driving better business outcomes and user
satisfaction. It can also help you with regulatory compliance and
optimizes resource utilization.

**Desired outcome:** A robust
monitoring system is in place that provides real-time visibility
into the performance of your foundation models, allows for early
detection of anomalies or degradation, and speeds up response to
incidents. This system integrates with your existing observability
tools and processes, providing a holistic view of your application's
health.

**Benefits of establishing this best
practice:**

- [Implement
observability for actionable insights](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - Monitor
foundation model metrics.
- [Learn
from all operational events and metrics](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - Capturing
fine-grained observations enables continuous improvement.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

To implement comprehensive monitoring for your foundation model
metrics, consider using cloud-native monitoring solutions that
integrate with your AI services. To achieve better performance and
quick incident response, set warning and error thresholds for the
metrics based on your workload's expected patterns. Additionally,
define and practice incident response playbooks for when these
alerts go off. Configure alarms to monitor specific thresholds and
to send notifications or take actions when values exceed those
thresholds. These metrics can be visualized using graphs in the
console.

For applications using Amazon Bedrock, use Amazon CloudWatch to
monitor crucial metrics such as invocation counts, latency, token
usage, error rates, and throttling events. Set up custom
dashboards to visualize these metrics, and configure alarms to
alert you when predefined thresholds are exceeded.

If you're using Amazon SageMaker AI for hosting models, use
the invocation and resource utilization metrics available in
Amazon CloudWatch, such as invocation counts, latency, and
error rates, as well as GPU and memory utilization. The Model
Monitor feature offers additional metrics to help you monitor
and evaluate the performance of your models in production. You
can establish baselines, schedule monitoring jobs, and set up
alerts to detect deviations from predefined thresholds.

For SageMaker AI HyperPod with both Amazon EKS and Slurm
orchestration, use the system's comprehensive one-click
observability capabilities that automatically collect and
visualize key metrics across operational layers.

For EKS-based HyperPod, use the integrated Amazon EKS add-on
for SageMaker AI HyperPod observability that consolidates health
and performance data from NVIDIA DCGM, Kubernetes node
exporters, Elastic Fabric Adapter (EFA), and file systems into
unified Amazon Managed Grafana dashboards with metrics
automatically published to Amazon Managed Service for Prometheus.

Configure CloudWatch Container Insights for enhanced
monitoring of CPU, GPU, Trainium, EFA, and file system metrics
up to the container level, while implementing automated
alerting for model invocation latency, concurrent requests,
error rates, and token-level metrics.

For Slurm-based HyperPod, implement comprehensive monitoring
through node exporters for system metrics, NVIDIA DCGM for GPU
health monitoring, and EFA metrics for network performance
tracking, all integrated with the unified observability
solution.

Both systems benefit from SageMaker AI HyperPod's real-time task
performance metric tracking with automated alerting
capabilities, automatic root cause remediation with
customer-defined policies, and inference observability that
captures essential model performance data including invocation
latency, concurrent requests, error rates, and token-level
metrics through standardized Prometheus endpoints.

Additionally, establish incident response playbooks for when
alerts trigger, configure custom thresholds based on
workload-specific patterns, and use a unified dashboard that
reduces troubleshooting time from days to minutes through
pre-built, actionable insights.

To enable automated responses to specific events, consider
implementing Amazon EventBridge. It monitors events from other
AWS services in near real-time. Use it to send event
information when they match rules you define, such as state
change events in a training job you've submitted. Configure
your application to respond automatically to these events.

### Implementation steps

- For Amazon Bedrock, enable model invocation logging.

Choose your desired data output options and log
destination (Amazon S3 or CloudWatch Logs)
- Track key metrics like
InputTokenCount,
OutputTokenCount, and
InvocationThrottles
- Use these metrics to understand model usage and
performance
- If needed, implement additional custom logging in your
application using the CloudWatch
PutMetricData API

- For Amazon SageMaker AI, implement Amazon SageMaker AI Model
Monitor.

Establish performance baselines for hosted models
- Include graphs for resource utilization (like memory and
GPU) where applicable
- Set up regular monitoring jobs to evaluate model
performance
- Configure alerts for deviations detected during
monitoring

- Set up a dashboard to visualize key metrics.

Create CloudWatch dashboards for your AI services (like
Amazon Bedrock and SageMaker AI)
- Add widgets for important metrics such as invocations,
latency, token counts, and error rates
- Consider implementing anomaly detection algorithms to
identify unusual patterns in data

- Create alarms for critical thresholds.

Elevated latency in model invocations
- High error rates or throttling events

- Implement EventBridge rules.

Create rules to capture significant events from your AI
services
- Set up appropriate targets for these rules (like SNS
topics or Lambda functions) and automate the responses

- Develop incident response playbooks.

Create playbooks for common scenarios (for example, high
latency or increased error rates)
- Define steps for identifying root causes and
implementing mitigations
- Establish procedures for communication and escalation

- Establish a regular review process

Schedule periodic reviews of dashboards and metrics
- Regularly assess and adjust alarm thresholds
- Conduct retrospective reviews on incidents and
near-misses
- Perform periodic audits of your monitoring coverage

## Resources

**Related best practices:**

- OPS08-BP01
- OPS08-BP02
- OPS08-BP04
- OPS08-BP05

**Related documents:**

- [Monitor
model invocation using CloudWatch Logs - Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html)
- [Monitor
the health and performance of Amazon Bedrock - Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring.html)
- [Monitoring
Generative AI applications using Amazon Bedrock and Amazon CloudWatch integration | AWS Cloud Operations & Migrations
Blog](https://aws.amazon.com/blogs/mt/monitoring-generative-ai-applications-using-amazon-bedrock-and-amazon-cloudwatch-integration/)
- [Data
and model quality monitoring with Amazon SageMaker AI Model
Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html)
- [AWS Well-Architected Framework: Operational Excellence
Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)
- [Accelerate
Foundation Model Development with One-Click Observability in
Amazon SageMaker AI HyperPod](https://aws.amazon.com/blogs/machine-learning/accelerate-foundation-model-development-with-one-click-observability-in-amazon-sagemaker-hyperpod/)
- [Amazon SageMaker AI HyperPod launches model deployments to accelerate
the generative AI model development lifecycle](https://aws.amazon.com/blogs/machine-learning/amazon-sagemaker-hyperpod-launches-model-deployments-to-accelerate-the-generative-ai-model-development-lifecycle/)

**Related examples:**

- [SageMaker AI
Model Monitor Example Notebooks](https://github.com/aws/amazon-sagemaker-examples/tree/main/sagemaker_model_monitor)
- [EventBridge
Rules for SageMaker AI Training Jobs](https://docs.aws.amazon.com/sagemaker/latest/dg/automating-sagemaker-with-eventbridge.html)

**Related tools:**

- [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/)
- [Amazon SageMaker AI Model Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html)
- [Amazon EventBridge](https://aws.amazon.com/eventbridge/)
- [AWS Lambda](https://aws.amazon.com/lambda/) (for automated responses)
- [Amazon Simple Notification Service](https://aws.amazon.com/sns/) (for notifications)
