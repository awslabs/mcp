---
id: "GENOPS05-BP01"
title: "Learn when to customize models"
pillar: "Operational Excellence"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genops05-bp01.html"
---

# GENOPS05-BP01 Learn when to customize models

Prioritize prompt engineering and RAG before model customization to
optimize resources and enhance performance in developing generative
AI solutions. This best practice aims to guide you in making
informed decisions about when and how to customize AI models, which
helps you verify that they achieve the best balance between
efficiency and effectiveness. By starting with prompt engineering
and RAG, you can leverage existing model capabilities to meet their
needs, reducing the time, cost, and complexity associated with model
customization. This approach allows organizations to quickly iterate
on solutions, minimize resource consumption, and focus on achieving
desired outcomes with minimal upfront investment.

**Desired outcome:** You have an
approach to decide when to customize models.

**Benefits of establishing this best
practice:**
[Use
managed services](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - Manage the undifferentiated heavy lifting
associated with large-scale, memory-intensive, distributed computing
tasks such as model customization.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Consider these guidelines when deciding whether to fine-tune,
domain adapt, or pre-train a custom foundation model. Review the
considerations between model performance, resource requirements,
and maintenance costs for each approach.

Start with the least resource-intensive option (prompt
engineering), and progressively move to more advanced methods if
needed. Well-crafted prompts can often achieve the desired results
without modifying the model.

Evaluate RAG to customize the model's behavior by allowing it to
use external knowledge sources through a retrieval mechanism,
which effectively tailors its responses to specific domains or
contexts without retraining the core model itself.

Choose continued pre-training or fine-tuning when:

- You have a
specific task or use case that requires improved performance
- You have the labeled data relevant to your task
- You need the model
to understand domain-specific language (for example, medical or
legal terminology)
- You want to enhance the model's accuracy for
your application

Build a custom foundation model (typically the highest option in
resources and cost) when:

- None of the available pre-trained
models meet your specific requirements
- You have a vast amount of
proprietary data to train on
- You need complete control over the
model architecture and training process.

Amazon Bedrock's built-in tools for model evaluation to assess the
performance improvements after customization. Amazon Bedrock
offers managed RAG, agents, fine-tuning, and continued
pre-training. For greater control, use Amazon SageMaker AI, including
features to build a custom model using HyperPod with distributed
data and model parallelism training capabilities.

### Implementation steps

- Begin with prompt engineering.

Experiment with prompt structures, and test various prompt
formats to identify the most effective approach
- Use Amazon Bedrock's prompt engineering tools to
streamline the process
- Use Amazon SageMaker AI or Amazon Bedrock's evaluation tools
to assess prompt effectiveness

- Evaluate Retrieval-Augmented Generation (RAG) if needed.

Use vector databases such as Amazon OpenSearch Service for
enhanced knowledge retrieval
- Combine RAG with your selected model in Amazon Bedrock, or
consider the managed RAG feature Knowledge Bases
- Measure performance gains and response relevance

- Consider fine-tuning or continued pre-training.

Use Amazon Bedrock managed fine-tuning and pre-training
features
- Prepare labeled data specific to your task or domain
- Monitor improvements after customization

- Build a custom foundation model.

Use Amazon SageMaker AI HyperPod for FM training
- Decide between Slurm or Amazon EKS as your orchestrator
- Use SageMaker AI distributed data parallelism (SMDDP) for
data parallelism
- Use SageMaker AI model parallelism (SMP) for model
parallelism techniques

- Regularly update and retrain your model.

Track model effectiveness over time
- Update models with fresh data as it becomes available
- Use Amazon SageMaker AI Model Monitor for ongoing assessment

- Consider trade-offs in your workload.

Evaluate the cost for each approach
- Balance complexity and efficiency

## Resources

**Related best practices:**

- OPS04-BP01

**Related documents:**

- [Amazon Bedrock capabilities to enhance data processing and
retrieval](https://aws.amazon.com/blogs/aws/new-amazon-bedrock-capabilities-enhance-data-processing-and-retrieval/)
- [Customize
models in Amazon Bedrock with your own data using fine-tuning
and continued pre-training](https://aws.amazon.com/blogs/aws/customize-models-in-amazon-bedrock-with-your-own-data-using-fine-tuning-and-continued-pre-training/)
- [Amazon SageMaker AI HyperPod - Amazon SageMaker AI](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod.html)
- [Run
distributed training workloads with Slurm on HyperPod - Amazon SageMaker AI](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-run-jobs-distributed-training-workload.html)
- [SageMaker AI
HyperPod recipe repository - Amazon SageMaker AI](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-recipe-repository.html)

**Related examples:**

- [Amazon Bedrock Agents](https://aws.amazon.com/bedrock/agents/)
- [Amazon Bedrock Knowledge Bases](https://aws.amazon.com/bedrock/knowledge-bases/)

**Related tools:**

- [Amazon SageMaker AI](https://aws.amazon.com/sagemaker/)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/)
- [Amazon Elastic Kubernetes Service (Amazon EKS)](https://aws.amazon.com/eks/)
