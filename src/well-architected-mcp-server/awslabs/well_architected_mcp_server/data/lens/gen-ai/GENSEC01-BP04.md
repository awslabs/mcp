---
id: "GENSEC01-BP04"
title: "Implement access monitoring to generative AI services and foundation models"
pillar: "Security"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec01-bp04.html"
---

# GENSEC01-BP04 Implement access monitoring to generative AI services and foundation models

Generative AI services and foundation models can be resource
intensive to use and can be misused. Implementing access monitoring
on these services and models helps to identify, triage and resolve
unintended access quickly.

**Desired outcome:** When
implemented, this current guidance monitors access to sensitive
generative AI systems and foundation models. Unintended and
unauthorized use of generative AI services and foundation models can
be identified quickly and further action can be taken if
appropriate.

**Benefits of establishing this current
guidance:** [Maintain
traceability](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - Access monitoring traces access to generative
AI services and foundation models.

**Level of risk exposed if this current
guidance is not established:** High

## Implementation guidance

AWS CloudTrail can be used to monitor access to AWS services.
To track service-level access to generative AI services such
as Amazon Bedrock, customers can utilize AWS CloudTrail. In
Amazon Bedrock, customers can additionally turn on model
invocation logging to collect metadata, requests and responses
for model invocations in an AWS account. Similar capabilities
exist for the Amazon Q family of services.

For additional controls, consider implementing guardrails to
mask or remove sensitive data elements (like personal data) in
the prompts before foundation model invocations are made. This
additional step helps to mitigate the unintended or
unauthorized access to private or restricted data and makes
sure your organization policies and responsible AI governance
are followed.

When using Amazon SageMaker AI HyperPod environments using Amazon EKS or Slurm, enable AWS CloudTrail to log API calls and
resource access events related to SageMaker AI, EKS, and Slurm
workloads. Configure Amazon CloudWatch Logs to capture
detailed logs from training jobs, inference endpoints, and
orchestration layers, and record user actions and model
invocations.

Set up centralized log storage in Amazon S3 or CloudWatch Logs
for secure retention and analysis. Use CloudWatch Alarms or
AWS Security Hub CSPM to automatically alert on suspicious or
unauthorized activities, and regularly review logs to detect
unusual patterns or potential security incidents.

These strategies provide comprehensive traceability, help
support compliance, and enable rapid detection and response to
unauthorized access, fully aligning with AWS Well-Architected
security best practices for generative AI workloads.

Consider implementing access or query logging on data stores
or generative business intelligence (BI) solutions. For
traceability purposes, log both name of the generative AI
application and the end-user making the request. Agentic
workloads will require additional logging for each agent
called. Generative AI workloads should be architected with
application identities for traceability purposes. Consider
recording these identities in your organization's AI policy
document alongside other relevant security information such as
workload owner or permission boundaries.

### Implementation steps

- In Amazon Bedrock, configure model invocation logging to
track model invocations and store the logs in Amazon S3,
Amazon CloudWatch Logs, or both.
- In Amazon Q Developer, capture user activity by enabling
user activity capture in the settings.
- In Amazon Q Business, configure log delivery for
analysis and review into Amazon S3, Amazon CloudWatch Logs, or Amazon Data Firehose.
- For self-hosted models on Amazon SageMaker AI Inference
Endpoints, configure logging using your preferred
logging solution.
- Introduce logging, monitoring and telemetry capture in
additional application layers, depending on your
specific workload.

## Resources

**Related best practices:**

- [SEC03-BP08](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_permissions_share_securely.html)

**Related documents:**

- [Monitoring
Amazon Q Business and Q Apps](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/monitoring-overview.html)
- [Monitoring
Amazon Q Developer](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/monitoring-overview.html)

**Related examples:**

- [Monitoring
Generative AI Applications using Amazon Bedrock and Amazon CloudWatch Integration](https://aws.amazon.com/blogs/mt/monitoring-generative-ai-applications-using-amazon-bedrock-and-amazon-cloudwatch-integration/)
- [Overseeing
AI Risk in a Rapidly Changing Landscape](https://aws.amazon.com/blogs/enterprise-strategy/overseeing-ai-risk-in-a-rapidly-changing-landscape/)
- [Observability
for SageMaker AI HyperPod Cluster Orchestrated by Amazon EKS](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-eks-cluster-observability.html)
- [SageMaker AI
HyperPod Cluster Resources Monitoring (Slurm)](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-cluster-observability-slurm.html)
- [Logging
Amazon SageMaker AI API Calls Using AWS CloudTrail](https://docs.aws.amazon.com/sagemaker/latest/dg/logging-using-cloudtrail.html)
- [Amazon SageMaker AI HyperPod Now Integrates with Amazon EventBridge](https://aws.amazon.com/about-aws/whats-new/2025/05/amazon-sagemaker-hyperpod-integrates-amazon-eventbridge-status-change-events)
