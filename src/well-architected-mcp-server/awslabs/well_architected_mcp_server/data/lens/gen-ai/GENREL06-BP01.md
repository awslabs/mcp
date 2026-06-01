---
id: "GENREL06-BP01"
title: "Design for fault-tolerance for high-performance distributed computation tasks"
pillar: "Reliability"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genrel06-bp01.html"
---

# GENREL06-BP01 Design for fault-tolerance for high-performance distributed computation tasks

Fault-tolerant infrastructure identifies issues in long-running,
high-performance distributed computation tasks and remediates them
before they can disrupt the task. Because these tasks are expensive
and time-consuming, use fault-tolerant infrastructure to reliably
perform model customization jobs.

**Desired outcome:** When
implemented, this best practice improves the reliability of your
model customization workloads, automating recovery during
fine-tuning, pre-training, and other model customization workloads.

**Benefits of establishing this best
practice:**
[Automatically
recover from failure](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html) - Fault-tolerant infrastructure can
automatically recover from failure, improving the reliability of
long-running, high-performance, distributed computation tasks like
model customization.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Model pre-training, continuous pre-training, fine-tuning, and
distillation are some of the many high-performance distributed
computation tasks sometimes required to optimize foundation
models for generative AI workloads. These tasks require the
orchestration of dozens or hundreds of virtual machines,
running workloads over days, weeks, months or longer. These
tasks are particularly susceptible to disruptions, which could
delay or stop training progress. Consider a managed or
automated process that provisions and orchestrates the
infrastructure on your behalf, handles errors, and preserves
the workload's integrity.

Amazon SageMaker AI HyperPod clusters allow customers to
pre-train or fine-tune large language models using managed
infrastructure. Amazon EC2 UltraClusters facilitate large
language model hosting for purpose-built machine learning
accelerators. Additionally, Amazon Bedrock offers managed
fine-tuning, continuous pre-training, or model distillation
for a selection of third-party models.

Amazon SageMaker AI HyperPod, with both Amazon EKS and Slurm
orchestration, establishes comprehensive checkpointing
mechanisms that automatically save training state at regular
intervals to persistent storage like Amazon S3 or FSx for Lustre.

For EKS-based HyperPod, use fault tolerance capabilities by
implementing application-level checkpointing in your training
scripts, and store checkpoints on shared persistent volumes
that survive pod restarts and node failures. Configure
Kubernetes health checks and restart policies to automatically
detect and recover from failed training pods while preserving
progress from the last checkpoint.

For Slurm-based HyperPod, use the auto-resume functionality to
provide zero-touch resiliency infrastructure that
automatically recovers training jobs from the last saved
checkpoint when hardware failures occur. Configure your
training jobs to run inside exclusive allocations using salloc
or sbatch, and verify that your entrypoint scripts maintain
environment consistency across node replacements. Both systems
benefit from SageMaker AI HyperPod's built-in cluster health
monitoring that continuously checks GPU health with DCGM
policies, network connectivity with EFA health checks, and
automatically replaces faulty nodes. The multi-head node
support in Slurm further enhances fault tolerance by providing
backup head nodes that automatically take over if the primary
head node fails.

When implementing fault-tolerant distributed training
manually, evaluate options that can recover the training and
customization progress. Create training job recovery points by
checkpointing model training. Keep track of training progress,
and determine when to halt training based on observed metrics.
Consider leveraging performant storage solutions (like Amazon FSx for Lustre) that provide distributed compute tasks rapid
access to large data volumes at scale. Managed training and
model customization solutions provide these capabilities, but
you can also consider self-hosting for some model training and
customization initiatives.

Use managed services and purpose-built infrastructure to
handle the complexity and resource requirements of distributed
model customization workloads. AWS offers several solutions
that can help improve the reliability and efficiency of these
tasks:

- **Amazon SageMaker AI
HyperPod:** A managed service that automates the
provisioning and orchestration of distributed training
infrastructure, including handling node failures,
checkpointing, and other fault-tolerance mechanisms.
HyperPod is optimized for large language model training
and can use specialized hardware like AWS Trainium
instances.
- **Amazon Bedrock:**
Provides managed workflows for fine-tuning, continued
pre-training, and model distillation, abstracting away the
underlying infrastructure management and failure handling.
- **AWS Batch:** A
fully-managed batch processing service that can run
distributed computational tasks, including model
customization, with automatic scaling, retry logic, and
resource optimization.

When implementing fault tolerance manually, focus on
strategies like checkpointing, progress tracking, and
automated recovery. Use high-performance storage solutions
like Amazon FSx for Lustre to provide rapid access to training
data. Configure your workflow to handle node failures, spot
instance interruptions, and other disruptions gracefully.

Continuously monitor the distributed workloads for
performance, resource utilization, and failures. Use Amazon CloudWatch to set alerts and thresholds, and use Amazon EventBridge to run automated remediation actions. Analyze logs
and metrics to identify bottlenecks and optimize the
distributed architecture over time.

### Implementation steps

- Evaluate managed services like SageMaker AI HyperPod,
Bedrock, and Batch for your model customization needs.
- If implementing a custom distributed workflow, provision
high-performance storage and compute resources.
- Implement checkpointing, progress tracking, and
automated retry mechanisms to handle failures.
- Configure monitoring, alerting, and automated
remediation for the distributed workloads.
- Continuously analyze performance, costs, and reliability
to optimize the distributed architecture.

## Resources

**Related best practices:**

- REL10-BP02
- REL11-BP01
- REL11-BP03

**Related documents:**

- [Amazon SageMaker AI HyperPod](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod.html)
- [Customize
your model to improve its performance for your use case](https://docs.aws.amazon.com/bedrock/latest/userguide/custom-models.html)
- [Resilience-related
Kubernetes labels by SageMaker AI HyperPod](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-eks-resiliency-node-labels.html)

**Related examples:**

- [Speed
up training on Amazon SageMaker AI using Amazon FSx for Lustre
and Amazon EFS file systems](https://aws.amazon.com/blogs/machine-learning/speed-up-training-on-amazon-sagemaker-using-amazon-efs-or-amazon-fsx-for-lustre-file-systems/)
- [Customize
models in Amazon Bedrock with your own data using fine-tuning
and continued pre-training](https://aws.amazon.com/blogs/aws/customize-models-in-amazon-bedrock-with-your-own-data-using-fine-tuning-and-continued-pre-training/)
- [Amazon BedrockModel Customization Workshop Notebooks](https://github.com/aws-samples/amazon-bedrock-customization-workshop)
- [Amazon SageMaker AI Hyperpod Recipes](https://github.com/aws/sagemaker-hyperpod-recipes)
- [Introducing Amazon SageMaker AI HyperPod: a purpose-built infrastructure for distributed training
at scale](https://aws.amazon.com/blogs/aws/introducing-amazon-sagemaker-hyperpod-a-purpose-built-infrastructure-for-distributed-training-at-scale/)
- [Introducing
Amazon SageMaker AI HyperPod, a purpose-built infrastructure
for distributed training at scale](https://aws.amazon.com/blogs/aws/introducing-amazon-sagemaker-hyperpod-a-purpose-built-infrastructure-for-distributed-training-at-scale/)
- [Ray
jobs on Amazon SageMaker AI HyperPod: scalable and resilient
distributed AI](https://aws.amazon.com/blogs/machine-learning/ray-jobs-on-amazon-sagemaker-hyperpod-scalable-and-resilient-distributed-ai/)
- [SageMaker AI
HyperPod cluster resiliency](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-resiliency-slurm.html)
- [Reduce
ML training costs with Amazon SageMaker AI HyperPod](https://aws.amazon.com/blogs/machine-learning/reduce-ml-training-costs-with-amazon-sagemaker-hyperpod/)
