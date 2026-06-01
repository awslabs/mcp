---
id: "GENSUS01-BP02"
title: "Use efficient model customization services"
pillar: "Sustainability"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensus01-bp02.html"
---

# GENSUS01-BP02 Use efficient model customization services

To maximize efficiency and sustainability in large-scale generative
AI model deployments, adopt best practices for distributed training
and parameter-efficient fine-tuning. These techniques optimize
resource utilization and reduce energy consumption, leading to cost
savings and enhanced performance. This helps maintain a balance
between computational demands and environmental considerations,
promoting responsible cloud resource use.

**Desired outcome:** After
implementing this practice, your organization can create an
environmentally-sustainable infrastructure for training,
customizing, and hosting generative AI workloads.

**Benefits of establishing this best
practice:**
[Optimize
resource utilization](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sustainability-pillar.html) - Minimize environmental impact through
efficient use of generative AI model customization resources.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Amazon Bedrock offers managed model customization features for
fine-tuning and continued pre-training to improve the model's
domain knowledge. It optimizes the infrastructure management,
scaling, and maintenance, allowing developers to focus on model
performance rather than the underlying infrastructure.

Amazon SageMaker AI offers several features to train generative AI
models efficiently. SageMaker AI HyperPod is designed specifically
for large-scale generative AI model training. HyperPod provides
pre-tested training stacks for popular generative AI models, which
helps users start their training processes with confidence. It
offers optimized distributed training and enables the efficient
use of multiple instances for large-scale model training. This
distributed approach speeds up training times, making it feasible
to train even advanced models in a reasonable timeframe.

Users can choose from a variety of instance types, including GPU
and AWS Trainium instances. AWS Trainium instances deliver a
reduction in energy consumption compared to comparable instances
for training large deep learning models, including large language
models (LLMs). This makes training more cost-effective and
efficient.

Parameter-efficient fine tuning (PEFT) techniques, such as
low-rank adaptation (LoRA), can be applied when using Trainium
with HyperPod. These techniques make the fine-tuning of LLMs more
efficient by reducing the number of parameters that need to be
updated, which speeds up the fine-tuning process and reduces time
and cost.

Managed spot training is a feature that allows the use of spare
Amazon EC2 capacity which can lead to more efficient resource
utilization across the infrastructure. This means that users can
get lower-cost, surplus computing power while meeting quality and
speed of training goals.

SageMaker AI Debugger helps detect and stop training jobs early if
issues are identified, minimizing wasted compute resources. This
feature helps verify that users are only paying for the resources
they actually need, further optimizing the cost and efficiency of
their generative AI model training processes.

### Implementation steps

- Select the right AWS services.

Amazon Bedrock has managed model customization where
resource utilization is handled by AWS
- Amazon SageMaker AI offers advanced training features and
full control of the underlying infrastructure choices

- Set up SageMaker AI HyperPod for large-scale distributed
training.

Use pre-tested stacks for popular models to streamline
setup
- Consider AWS Trainium instances for reduced energy
consumption compared to traditional instances
- Apply parameter-efficient fine-tuning with HyperPod for
fine-tuning large language models, reducing the
computational and energy requirements

- Use managed spot training.

Implement managed spot training to utilize spare Amazon EC2 capacity, leading to better underlying resource
utilization
- Set up the checkpointing feature to handle spot instance
interruptions and restart from the last point of
completion

- Enable SageMaker AI Debugger.

Use Debugger to monitor and optimize training job
resource utilization
- Configure rules to identify and halt training jobs early
in case of issues, minimizing wasted compute resources

- Optimize resource utilization and cost.

Analyze usage patterns to adjust instance types and
counts
- Use auto scaling features
- Use cost allocation tags to track detailed resource
consumption and for billing analysis

## Resources

**Related best practices:**

- SUS02-BP01
- SUS05-BP02

**Related documents:**

- [Customize
your model to improve its performance for your use case](https://docs.aws.amazon.com/bedrock/latest/userguide/custom-models.html)
- [Customize
models in Amazon Bedrock with your own data using fine-tuning
and continued pre-training](https://aws.amazon.com/blogs/aws/customize-models-in-amazon-bedrock-with-your-own-data-using-fine-tuning-and-continued-pre-training/)
- [Distributed training in Amazon SageMaker AI](https://docs.aws.amazon.com/sagemaker/latest/dg/distributed-training.html)
- [Parameter-Efficient
Fine-Tuning (PEFT) on SageMaker AI HyperPod with AWS
Trainium](https://aws.amazon.com/blogs/machine-learning/peft-fine-tuning-of-llama-3-on-sagemaker-hyperpod-with-aws-trainium/)

**Related examples:**

- [Bedrock
Model Customization Workshop Notebooks](https://github.com/aws-samples/amazon-bedrock-customization-workshop)
- [SageMaker AI
HyperPod recipe repository](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-recipe-repository.html)
- [Guidance
for Optimizing MLOps for Sustainability on AWS](https://aws.amazon.com/solutions/guidance/optimizing-mlops-for-sustainability-on-aws/)

**Related tools:**

- [Amazon SageMaker AI](https://aws.amazon.com/sagemaker/)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [AWS Trainium](https://aws.amazon.com/ai/machine-learning/trainium/)
- [Amazon SageMaker AI HyperPod](https://aws.amazon.com/sagemaker-ai/hyperpod/)
- [Amazon SageMaker AIDebugger](https://docs.aws.amazon.com/sagemaker/latest/dg/train-debugger.html)
- [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
