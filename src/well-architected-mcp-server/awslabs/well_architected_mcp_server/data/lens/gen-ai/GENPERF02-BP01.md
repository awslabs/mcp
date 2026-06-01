---
id: "GENPERF02-BP01"
title: "Load test model endpoints"
pillar: "Performance Efficiency"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genperf02-bp01.html"
---

# GENPERF02-BP01 Load test model endpoints

Hosting architecture is a significant factor in determining the
performance efficiency of a foundation model. Load test model
endpoints to determine a baseline level of performance. Load
tests should evaluate foundation model performance under average
workload throughput, as well as extremes. Capturing a
comprehensive understanding of model endpoint performance under
a variety of workload demands helps improve architectural
decision-making in regard to performance efficiency and endpoint
selection.

**Desired outcome:** When
implemented, this best practice helps you identify the optimal
load of a foundation model endpoint. This baseline should be
used to inform monitoring and alerting at the upper-threshold of
acceptable performance limitations for your workload.

**Benefits of establishing this best
practice:**
[Experiment
more often](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html) - Load testing model endpoints assists in the
ongoing performance of foundation models at scale.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Workloads have unique performance requirements, such as low
latency, rapid scalability, or intermittent demand scaling.
Methods for achieving clearly defined performance requirements
should be outlined in your organization's AI policy.
Generalize guidelines for implementing real-time or batch
inference, with clear processes defined for testing and
scaling workloads with exceptional performance demands.

One mechanism for implementing this is a test suite, designed
to simulate the heaviest expected load to an application
before anticipated performance degradation. Test models and
model endpoints against these requirements to determine if
additional architectural considerations are required to bridge
the gap between performance needs and observed performance
results. Consider using a ground truth data set to standardize
results across multiple models.

On Amazon Bedrock, review the published metrics for inference
latency and throughput before testing if they are available.
If these metrics are not available, benchmark the model
against a golden dataset provided by you or curated by a
third-party. The golden dataset should effectively test the
model for the task in question. Use the performance benchmarks
for that model to influence the model selection process. If a
model has throughput limitations, consider introducing
provisioned throughput capabilities or using cross-Region
inference endpoints. Identify the performance bottleneck and
architect accordingly.

On Amazon SageMaker AI, test inference endpoints with respect
to the inference endpoint instance type and size. Load test
inference endpoints as you might load test other
high-performance compute options. Depending on the model being
hosted, there may be an opportunity to modify inference
parameters to optimize performance or to use advanced model
customization techniques such as quantization or LoRa.
Research the inference options available to the model you are
hosting, and test the effect of different inference parameters
on your performance criteria.

For SageMaker AI hosted models, you can optimize memory, I/O,
and computation by selecting an appropriate serving stack and
instance type. SageMaker AI large model inference (LMI) deep
learning containers provide options for request batching,
quantization options, and support for the newest versions of
vLLM, a performance optimized library for LLM serving and
inference. You can use these capabilities to balance
performance with other workload metrics like complexity and
cost.

To improve performance bottlenecks on a foundation model,
consider optimizing the flow of prompts. Some low latency and
real-time application use cases with repeated prompts may
benefit from prompt caching using Amazon Bedrock prompt
caching. Prompt caching can improve the latency and
performance of model endpoints by reducing the load on those
endpoints for regularly submitted prompts. Instead of the
model servicing each prompt, a cached response is returned
instead, reducing the load on the foundation model.
Additionally, implementing streaming model responses can also
improve a user's perceived latency on responses not in the
cache.

Consider the usage requirements of some generative AI
workloads, batch inference may be a potent alternative to
traditional inference requests for model endpoints. Batch
inference is more efficient for processing large volumes of
prompts, especially when evaluating, experimenting, or
performing offline analysis on foundation models. You can use
this to aggregate responses and analyze them in batches. If
higher latency is acceptable in your scenario, batch inference
may be a better choice than real-time invoke model. Batch
processing by definition introduce additional latency compared
to real-time inference, so you should use it in scenarios
where load testing permits long-running job executions.

### Implementation steps

- Reference your organization's AI policy for information
concerning appropriate performance metrics for model
endpoint load testing.
- Develop a load testing harness that prompts a foundation
model at configurable rates. Consider incorporating the
ability test against internal golden datasets and
external third-party benchmarking data.
- Collect performance information from the model from the
load test, carefully evaluating where the bottleneck
exists. Bottlenecks in the model's ability to serve
inference requests may be addressed through model
customization techniques or increasing the size and
power of the inference endpoint. Bottlenecks inherited
from usage patterns may benefit from cross-Region
inference, prompt caching, or an entirely different
inference paradigm.

## Resources

**Related best practices:**

- PERF05-BP04
- [MLPER-01](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlper-01.html)
- [MLPER-03](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlper-03.html)
- [MLPER-05](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlper-05.html)
- [MLPER-07](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlper-07.html)

**Related documents:**

- [Monitor
the health and performance of Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring.html)
- [Supercharge
your LLM performance with Amazon SageMaker AI Large Model
Inference container v15](https://aws.amazon.com/blogs/machine-learning/supercharge-your-llm-performance-with-amazon-sagemaker-large-model-inference-container-v15/)
- [Model
management for LoRA fine-tuned models using Llama2 and Amazon SageMaker AI](https://aws.amazon.com/blogs/machine-learning/model-management-for-lora-fine-tuned-models-using-llama2-and-amazon-sagemaker/)
- [Efficient
and cost-effective multi-tenant LoRA serving with Amazon SageMaker AI](https://aws.amazon.com/blogs/machine-learning/efficient-and-cost-effective-multi-tenant-lora-serving-with-amazon-sagemaker/)

**Related examples:**

- [Load
testing applications](https://docs.aws.amazon.com/prescriptive-guidance/latest/load-testing/welcome.html)
- [Deploy
models with DJL Serving](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-models-frameworks-djl-serving.html)
- [The
large model inference (LMI) container documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/large-model-inference-container-docs.html)
- [Amazon Bedrock model evaluation is now generally available](https://aws.amazon.com/blogs/aws/amazon-bedrock-model-evaluation-is-now-generally-available/)
- [Best
practices for load testing Amazon SageMaker AI real-time
inference endpoints](https://aws.amazon.com/blogs/machine-learning/best-practices-for-load-testing-amazon-sagemaker-real-time-inference-endpoints/)

**Related tools:**

- [Bedrock
Latency Benchmarking](https://github.com/gilinachum/bedrock-latency)
- [vLLM](https://docs.vllm.ai/en/latest/)
