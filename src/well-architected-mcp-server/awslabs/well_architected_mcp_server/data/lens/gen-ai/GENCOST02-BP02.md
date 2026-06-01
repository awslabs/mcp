---
id: "GENCOST02-BP02"
title: "Optimize resource consumption to minimize hosting costs"
pillar: "Cost Optimization"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gencost02-bp02.html"
---

# GENCOST02-BP02 Optimize resource consumption to minimize hosting costs

Hosting a foundation model for inference requires myriad choices,
all of which affect cost. These cost dimensions can be optimized to
reduce cost while meeting performance goals.

**Desired outcome:** When
implemented, this best practice describes a relationship between
cost and performance contextualized in self-hosted foundation model
hosting.

**Benefits of establishing this best
practice:**

- [Measure
overall efficiency](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-dp.html) - It is helpful to understand
inference and hosting costs associated with the performance
requirements of foundation model.
- [Stop
spending money on undifferentiated heavy lifting](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-dp.html) - More
often than not, it is beneficial to opt for a managed or
serverless hosting paradigm, due to the intractability of the
total cost of ownership for foundation model hosting.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Self-hosted model infrastructure should be optimized based on the
model used and the workload's usage pattern. Customers
self-hosting models should also consider optimizing the model's
hosting infrastructure. Consider right-sizing the inference
endpoint to the smallest instance available that allows you to
meet performance goals. In some scenarios, it may be appropriate
to shut down the hosting instance and restart it during relevant
hours. This is particularly useful for workloads with predictable
usage patterns. You may also consider purchasing [Amazon EC2 Reserved
Instances](https://aws.amazon.com/ec2/pricing/reserved-instances/) or Savings Plans to further reduce the cost of a hosted
model endpoint. Before committing to compute reservation, consider
Amazon SageMaker AI Inference Recommender to evaluate if you are
using the ideal inference endpoint type, generation, and size.

In SageMaker AI HyperPod with both Amazon EKS and Slurm
orchestration, use the system's advanced task governance
capabilities and flexible training plans to dynamically
allocate compute resources based on priority and demand,
reducing costs through improved utilization.

For EKS-based HyperPod, implement the managed Kubernetes
orchestration with Hyperpod Task Governance. Configure
automated scaling policies, priority classes, and node
selectors to verify that your production workloads use
cost-effective committed capacity while development tasks use
On-Demand or Spot Instances when appropriate. Use the usage
reporting feature to provide granular visibility into GPU,
CPU, and Neuron Core consumption at both team and task levels,
enabling transparent cost attribution and reducing guesswork
in resource allocation.

For Slurm-based HyperPod, use Slurm's native job scheduling
and resource management features combined with HyperPod's
auto-resume functionality to minimize wasted compute cycles
during hardware failures, potentially reducing total training
time in large clusters. Both systems benefit from implementing
right-sizing strategies through SageMaker AI HyperPod Recipes
that provide pre-configured, benchmarked training stacks
optimized for specific model architectures like Llama and
Mistral, providing optimized performance while minimizing
resource waste.

Additionally, establish flexible training plans that can set
timeline and budget constraints, and allow HyperPod to
automatically find the best combination of capacity blocks and
create cost-optimized execution plans that avoid overspending
by overprovisioning servers for training jobs.

Inference workloads can be optimized using advanced techniques
such as quantization or LoRA adaptation. These advanced
capabilities are available for certain models in Amazon
Bedrock or on self-hosted models on Amazon SageMaker AI. These
advanced inference techniques can further optimize resource
consumption for inference, thus reducing hosting and inference
serving costs.

### Implementation steps

- Identify the nature of the demand for this workload.
- Deploy selected foundation model on acceptable
infrastructure, even if it may be over-provisioned.
- Establish an inference or demand profile for the hosted
workload.
- Optimize the hosting infrastructure in accordance with the
workload's demands, and select the most cost optimized
infrastructure that meets performance requirements.

## Resources

**Related best practices:**

- COST06-BP01
- COST06-BP02
- COST09-BP01

**Related videos and documents:**

- [Tagging
Amazon Bedrock resources](https://docs.aws.amazon.com/bedrock/latest/userguide/tagging.html)
- [Inference
cost optimization best practices](https://docs.aws.amazon.com/sagemaker/latest/dg/inference-cost-optimization.html)
- [Get
Started with Amazon SageMaker AI HyperPod Flexible Training
Plans](https://www.youtube.com/watch?v=Itcw8zhdArY)

**Related examples:**

- [Easily
deploy and manage hundreds of LoRA adapters with SageMaker AI
efficient multi-adapter inference](https://aws.amazon.com/blogs/machine-learning/easily-deploy-and-manage-hundreds-of-lora-adapters-with-sagemaker-efficient-multi-adapter-inference/)
- [Track,
allocate and manage your generative AI cost and usage with
Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/track-allocate-and-manage-your-generative-ai-cost-and-usage-with-amazon-bedrock/)
- [Optimizing
costs of generative AI applications on AWS](https://aws.amazon.com/blogs/machine-learning/optimizing-costs-of-generative-ai-applications-on-aws/)
- [SageMaker AI
Inference Recommender for HuggingFace BERT Sentiment
Analysis](https://github.com/aws/amazon-sagemaker-examples/blob/main/sagemaker-inference-recommender/huggingface-inference-recommender/huggingface-inference-recommender.ipynb)
- [Analyze
Amazon SageMaker AI spend and determine cost optimization
opportunities based on usage, Part 1](https://aws.amazon.com/blogs/machine-learning/part-1-analyze-amazon-sagemaker-spend-and-determine-cost-optimization-opportunities-based-on-usage-part-1/)
- [Maximize
Accelerator Utilization for Model Development with New Amazon SageMaker AI HyperPod Task Governance](https://aws.amazon.com/blogs/aws/maximize-accelerator-utilization-for-model-development-with-new-amazon-sagemaker-hyperpod-task-governance/)
- [Introducing
Amazon SageMaker AI HyperPod to train foundation models at
scale](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-sagemaker-hyperpod-to-train-foundation-models-at-scale/)
- [Best
practices for Amazon SageMaker AI HyperPod task governance](https://aws.amazon.com/blogs/machine-learning/best-practices-for-amazon-sagemaker-hyperpod-task-governance/)
- [Get
started with Amazon SageMaker AI HyperPod task governance](https://www.youtube.com/watch?v=_wDhBAPwhoM)
- [Usage
reporting for cost attribution in SageMaker AI HyperPod](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-usage-reporting.html)
