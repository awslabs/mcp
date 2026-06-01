---
id: "GENSUS03-BP01"
title: "Leverage smaller models to reduce carbon footprint"
pillar: "Sustainability"
risk_level: "LOW"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensus03-bp01.html"
---

# GENSUS03-BP01 Leverage smaller models to reduce carbon footprint

To manage computational demands and costs of deploying large
language models, implement model optimization techniques. This best
practice aims to increase AI operational efficiency by reducing
resource consumption while meeting performance goals. Strategies
like quantization, pruning, and model distillation help lower
operational expenses, improve response times, and promote
environmental sustainability. This approach enables you to deploy
efficient, cost-effective, and eco-friendly AI solutions, allowing
for application scaling without excessive costs or environmental
impact.

**Desired outcome:** After
implementing model optimization practices, you will have
cost-effective and carbon-effective AI solutions.

**Benefits of establishing this best
practice:**
[Optimize
resource utilization](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sustainability-pillar.html) - Minimize environmental impact by
maximizing the efficiency of generative AI resources.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

To effectively reduce the computational requirements of generative
AI models without compromising performance, it is essential to
implement a combination of optimization techniques such as
quantization, pruning, and the adoption of efficient model
architectures. Quantization involves reducing the precision of the
numbers used to represent the model's weights and activations.
This technique can decrease the model size and speed up inference
times with minimal impact on performance. Pruning, on the other
hand, involves removing redundant or unnecessary parameters from
the model. By identifying and alleviating weights that contribute
little to the model's predictions, pruning can lead to more
compact and efficient models.

In addition to these techniques, leveraging efficient model
architectures specifically designed for reduced computational
requirements can further enhance performance. Instead of relying
on large, general-purpose models, fine-tuning smaller models
tailored to specific use cases can often yield comparable results
with less computational resources. This approach allows for more
targeted optimization and can lead to more efficient deployments.

Amazon Bedrock supports this through its model distillation
feature. Model distillation involves training a smaller, more
efficient model to mimic the performance of a larger, more complex
model. This process results in a distilled model that maintains
similar performance levels while requiring fewer resources. By
utilizing such techniques, organizations can reduce computational
costs, making generative AI more accessible and scalable for a
wider range of applications.

With Amazon SageMaker AI, you can improve the performance of your
generative AI models by applying inference optimization techniques
to attain lower resource utilization and costs. Choose which of
the supported optimization techniques to apply, including
quantization, speculative decoding, LoRA and A, and compilation. After your
model is optimized, you can run an evaluation to see performance
metrics for latency, throughput, and price.

### Implementation steps

- Select optimization techniques.

Evaluate considerations between model size, speed, and
accuracy. Evaluate the effect on tasks and overall
performance
- Use SageMaker AI inference optimization techniques like LoRa
and quantization
- Use Amazon Bedrock Model Distillation feature to knowledge
transfer from a larger model to a smaller model

- Evaluate optimized models.

Compare performance with original models
- Assess resource savings and verify accuracy and
functionality taking edge cases into considerations

## Resources

**Related best practices:**

- SUS02-BP01
- SUS05-BP02
- SUS02-BP03

**Related documents:**

- [Impel enhances automative dealership customer experience with fine-tuned LLMs on SageMaker AI](https://aws.amazon.com/blogs/machine-learning/impel-enhances-automotive-dealership-customer-experience-with-fine-tuned-llms-on-amazon-sagemaker/)
- [A
guide to Amazon BedrockModel Distillation (preview)](https://aws.amazon.com/blogs/machine-learning/a-guide-to-amazon-bedrock-model-distillation-preview/)
- [Fine-tune
large language models with Amazon SageMaker AI Autopilot](https://aws.amazon.com/blogs/machine-learning/fine-tune-large-language-models-with-amazon-sagemaker-autopilot/)
- [Inference
optimization for Amazon SageMaker AI models](https://docs.aws.amazon.com/sagemaker/latest/dg/model-optimize.html)
- [Quantum-amenable
pruning of large language models and large vision models using
block coordinate descent](https://aws.amazon.com/blogs/quantum-computing/quantum-amenable-pruning-of-large-language-models-and-large-vision-models-using-block-coordinate-descent/)
- [Improve
the relevance of query responses with a reranked model in
Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank.html)

**Related examples:**

- [LLM
Rank pruning](https://github.com/amazon-science/llm-rank-pruning)
- [Optimizing
Generative AI LLM Inference Deployment on AWS GPUs By
Leveraging Quantization](https://github.com/aws-samples/optimizing-llm-inference-with-quantization)
- [Amazon SageMaker AI inference optimization toolkit for generative AI
using quantization](https://aws.amazon.com/blogs/machine-learning/amazon-sagemaker-launches-the-updated-inference-optimization-toolkit-for-generative-ai/)

**Related tools:**

- [Amazon Bedrock](https://aws.amazon.com/bedrock/?nc2=type_a)
- [Amazon SageMaker AI](https://aws.amazon.com/sagemaker-ai/)
- [AWSCloudWatch](https://aws.amazon.com/cloudwatch/)
