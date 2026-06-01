---
id: "GENPERF03-BP01"
title: "Use managed solutions for model hosting and customization"
pillar: "Performance Efficiency"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genperf03-bp01.html"
---

# GENPERF03-BP01 Use managed solutions for model hosting and customization

There are several industry-leading model providers, with new
model families, sizes, and capabilities being introduced
regularly. As foundation model capabilities expand, additional
operational requirements are required for hosting the models,
serving inference, and providing models access to data sources
and external systems. Alleviate operational burden on your
generative AI workload by using managed solutions where
appropriate.

**Desired outcome:** When
implemented, this best practice facilitates model hosting and
customization for highly performant generative AI workloads.

**Benefits of establishing this best
practice:**
[Use
serverless architectures](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html) - Serverless architectures
enhance the performance of infrastructure-bound workloads,
without the operational overhead.

**Level of risk exposed if this best
practice is not established:** Medium

## Implementation guidance

Amazon Bedrock is the primary method for managed model hosting
on AWS. Customers select from a variety of models from
industry-leading model families, using their selected model
through an API. You can use Bedrock's
[Custom
Model Import](https://aws.amazon.com/bedrock/custom-model-import/) capability to host your own models within
Bedrock's hosting layer. These options help you host
foundation models using managed hosting options.

If you prefer more control than Amazon Bedrock, but less
operational overhead than native Amazon EC2, you can host on
managed model endpoints using Amazon SageMaker AI's model
endpoints. Hosting on Amazon SageMaker AI managed model
endpoints provides more flexibility than Bedrock's fully
managed hosting and less operational overhead than a
completely self-managed hosting solution.

These principles similarly apply to model customization
workloads as well. Amazon Bedrock offers fully managed model
customization workloads for foundation models, including
continuous pre-training, fine-tuning, and distillation. Use
these managed model customization workflows to reap the
benefits of model customization without having to manage these
complex workflows yourself.

More advanced model customization workflows can be run on
managed model endpoints within Amazon SageMaker AI as well.
You maintain more control over these endpoints, enabling
advanced model customization at inference time, such as LoRA,
all without increasing the operational burden on your
endpoint.

When you want to build your own proprietary foundation models
using your own data, you can do so using AWS compute
infrastructure. The operational overhead required to manage a
fleet of EC2 instances performing distributed training over
long-periods of time can distract engineering teams from the
primary goal of creating a foundation model.

Consider managed alternatives such as
[Amazon SageMaker AI HyperPod](https://aws.amazon.com/sagemaker-ai/hyperpod/), which you can use for managed
infrastructure for long-running foundation model training
workloads. This simplifies the model training process and
helps your customers deliver foundation models using managed
infrastructure.

Foundation models often require customization to suit your
domain. The recommended approach to initially adapt a domain
is through prompt engineering without altering model weights.
You can use RAG, which augments the model's outputs with
relevant information grounded from supplied domain specific
sources. Where these options are not sufficient, consider
customizing models using managed model customization
workflows.

You can bring open-source models from model hubs like
HuggingFace to your AWS environment through
[Amazon SageMaker AI JumpStart](https://aws.amazon.com/sagemaker-ai/jumpstart/). Models imported from services
like HuggingFace are hosted on Amazon SageMaker AI Inference
Endpoints. Then, you can manage the underlying infrastructure
manually. Manual infrastructure hosting requires owners to
manage endpoints and preserve the model's performance for the
duration of the model's usefulness.

Instead of manually optimizing model infrastructure and
uptime, consider importing the model to a managed model
hosting service like Amazon Bedrock using Amazon Bedrock
Custom Model Import. This capability automates the performance
management and maintenance of hosted models in your AWS
environment, reducing the undifferentiated heavy lifting of
model hosting.

Consider using managed data integrations for generative AI
workloads such as retrieval-augmented generation or generative
business intelligence. A federated data access layer helps
facilitate the scaling of your data-driven generative AI
workloads. Consult your organization's AI usage or data
governance policy to provide your generative AI workflows
appropriate access to data.

When using Amazon SageMaker AI HyperPod with both Amazon EKS and
Slurm orchestration, use the system's built-in managed
capabilities to optimize high-performance compute resources
and reduce operational overhead during model development
workflows.

For Amazon EKS-based HyperPod, use the managed Kubernetes
orchestration with automated scaling, deep health checks, and
resiliency features that automatically detect and replace
faulty nodes. Configure containerized workloads using the
SageMaker AI HyperPod recipes that provide pre-configured
training stacks with built-in support for model parallelism,
automated distributed checkpointing, and optimized performance
on NVIDIA H100, A100, and AWS Trainium accelerators. Implement
task governance capabilities that automatically manage task
queues and prioritize critical training jobs while efficiently
allocating compute resources.

For Slurm-based HyperPod, take advantage of the managed
cluster provisioning and lifecycle configuration support that
customizes computing environments with Amazon SageMaker AI
distributed training libraries for optimal performance. Both
systems benefit from the managed resiliency infrastructure
that monitors cluster instances, automatically detects
hardware failures, and replaces faulty components with minimal
downtime—reducing total training time by up to 32% in large
clusters.

Additionally, integrate with the new observability
capabilities through Amazon Managed Grafana and Prometheus for
unified monitoring dashboards that reduce troubleshooting time
from days to minutes, which helps your training workloads
achieve peak performance while minimizing operational
complexity.

### Implementation steps

- Determine the level of control your team needs to exert
over the hosting solution.
- For fully managed hosting workload, use API-based
hosting solutions such as Amazon Bedrock.
- For managed hosting with more control over the endpoint,
use Amazon SageMaker AI model endpoints.
- Apply the same logic to model customization workflows.
- Model training workloads should be done Amazon SageMaker AI
HyperPod.
- Provide hosted models access to the appropriate data
using a robust permissions model and federated data
access.

## Resources

**Related best practices:**

- [PERF02-BP01](https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_compute_hardware_select_best_compute_options.html)

**Related documents:**

- [Amazon SageMaker AI HyperPod](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod.html)
- [Customize
your model to improve its performance for your use case](https://docs.aws.amazon.com/bedrock/latest/userguide/custom-models.html)
- [Observability
for Amazon SageMaker AI HyperPod cluster orchestrated by Amazon EKS](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-eks-cluster-observability.html)
- [SageMaker AI
HyperPod cluster resources monitoring](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-cluster-observability-slurm.html)

**Related examples:**

- [Amazon Bedrock
Model Customization Workshop](https://github.com/aws-samples/amazon-bedrock-customization-workshop)
- [Efficient and cost-effective multi-tenant LoRA serving with Amazon SageMaker AI](https://aws.amazon.com/blogs/machine-learning/efficient-and-cost-effective-multi-tenant-lora-serving-with-amazon-sagemaker/)
- [Choosing
Between Amazon SageMaker AI Training Jobs and Amazon SageMaker AI HyperPod: A Quick Decision-Making Guide for ML Workloads](https://repost.aws/articles/ARqYgZU7-kTjOYeoi8pZ94ZA/choosing-between-amazon-sagemaker-training-jobs-and-amazon-sagemaker-hyperpod-a-quick-decision-making-guide-for-ml-workloads)
- [Introducing Amazon SageMaker AI HyperPod to train foundation models at scale](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-sagemaker-hyperpod-to-train-foundation-models-at-scale/)
- [Customize
models in Amazon Bedrock with your own data using fine-tuning
and continued pre-training](https://aws.amazon.com/blogs/aws/customize-models-in-amazon-bedrock-with-your-own-data-using-fine-tuning-and-continued-pre-training/)
- [Accelerate
foundation model development with one-click observability in Amazon SageMaker AI HyperPod](https://aws.amazon.com/blogs/machine-learning/accelerate-foundation-model-development-with-one-click-observability-in-amazon-sagemaker-hyperpod/)
- [Amazon SageMaker AI HyperPod launches model deployments to accelerate the generative AI model development lifecycle](https://aws.amazon.com/blogs/machine-learning/amazon-sagemaker-hyperpod-launches-model-deployments-to-accelerate-the-generative-ai-model-development-lifecycle/)
- [Implementing
inference observability on HyperPod clusters](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-model-deployment-observability.html)
