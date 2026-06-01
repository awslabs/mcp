---
id: "GENSEC06-BP01"
title: "Implement data purification filters for model training workflows"
pillar: "Security"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec06-bp01.html"
---

# GENSEC06-BP01 Implement data purification filters for model training workflows

Data poisoning is best handled at the data layer before training or
customization has taken place. Data purification filters can be
introduced to data pipelines when curating a dataset for training or
customization.

**Desired outcome:** When
implemented, this best practice reduces the likelihood of
inappropriate or undesirable data being introduced into a model
training or customization workflow.

**Benefits of establishing this best
practice:**
[Apply
security at all layers](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - Security at all layers reduces the
risk of subtle security vulnerabilities entering an otherwise
advanced workflow.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

*Data poisoning* happens during pre-training,
domain adaptation, and fine-tuning, where
*poisoned* data is introduced, intentionally or
by mistake, into a model. Data poisoning is considered successful
if the model has learned from poisoned data. Protect models from
poisoning during pre-training and ongoing training steps by
isolating your model training environment, infrastructure, and
data. Data should be examined and cleaned for content which may be
considered poisonous before introducing that data to a training
job. There are several ways to accomplish this, all of which are
dependent on the data used to train a model.

For example, consider
using Amazon Transcribe's Toxicity Detection capability for voice
data. For text data, consider using the Amazon Bedrock Guardrails
API to filter data. Trained models can be tested using toxicity
evaluation techniques from fmeval or Amazon SageMaker AI Studio's
model evaluation capability. Carefully consider what your use case
defines as poisonous, and develop mechanisms for surfacing this
kind of data before it is introduced to a model through pre- and
post-training steps.

When using Amazon SageMaker AI HyperPod with both Amazon EKS and
Slurm, integrate automated data validation and cleansing steps
into your data pipeline before training begins.

Start by using tools or scripts that scan incoming datasets
for inappropriate, biased, or irrelevant content with AWS
services like Amazon Bedrock Guardrails or custom validation
logic. Apply these filters as a preprocessing step in your
workflow, and pass only clean and relevant data to the
distributed training jobs.

For Amazon EKS-based HyperPod, incorporate these checks into
your Kubernetes jobs or data ingestion pipelines, possibly
using containerized data validation services.

For Slurm-based HyperPod, run data purification scripts as a
prerequisite batch job before launching the main training
task.

Always log and monitor the filtering process to catch
anomalies and continuously update your filters based on new
threats or data issues. This proactive approach helps
safeguard model quality and security across both orchestration
systems.

### Implementation steps

- Identify the data intended for model pre-training or model
customization.
- Consult your organization's AI policy or data cards to identify relevant filters for the data.
- Develop filters to check for data which may be considered
poisonous to the model.

Examples include data which is biased, factually
incorrect, hateful, or violent.
- Other examples include data which is irrelevant to the
models intended purpose.

- Consider a guardrail from Amazon Bedrock Guardrails or a
third-party solution to check for less discrete signals of
poisoning.
- Run these checks on the data intended for model pre-training
and model customization, remediating issues as they are
discovered.
- Consider a relevance test or filter on data used for model customization workloads.

## Resources

**Related best practices:**

- SEC07-BP02

**Related documents:**

- [Amazon Transcribe Toxicity Detection](https://aws.amazon.com/transcribe/toxicity-detection/)
- [Use
the ApplyGuardrail API in Your Application](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-independent-api.html)
- [Command-line
tool for submitting and managing jobs on HyperPod clusters
orchestrated by EKS](https://github.com/aws/sagemaker-hyperpod-cli)
- [Ready-to-use
training recipes and scripts for both EKS and Slurm
orchestration, including data pipeline integration](https://github.com/aws/sagemaker-hyperpod-recipes)

**Related examples:**

- [Implement
Model Independent Safety Measures with Amazon Bedrock
Guardrails](https://aws.amazon.com/blogs/machine-learning/implement-model-independent-safety-measures-with-amazon-bedrock-guardrails/)
- [Blog:
Unified Data Preparation](https://aws.amazon.com/blogs/machine-learning/part-2-unified-data-preparation-model-training-and-deployment-with-amazon-sagemaker-data-wrangler-and-amazon-sagemaker-autopilot/)
- [Scalable
Training Platform with SageMaker AI HyperPod](https://aws.amazon.com/blogs/machine-learning/scalable-training-platform-with-amazon-sagemaker-hyperpod-for-innovation-a-video-generation-case-study/)

**Related tools:**

- [Guardrails
AI](https://github.com/guardrails-ai/guardrails)
- [OWASP
Data Poisoning Attack](https://owasp.org/www-project-machine-learning-security-top-10/docs/ML02_2023-Data_Poisoning_Attack.html)
