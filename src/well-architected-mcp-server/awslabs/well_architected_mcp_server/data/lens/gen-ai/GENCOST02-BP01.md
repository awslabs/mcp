---
id: "GENCOST02-BP01"
title: "Balance cost and performance when selecting inference paradigms"
pillar: "Cost Optimization"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gencost02-bp01.html"
---

# GENCOST02-BP01 Balance cost and performance when selecting inference paradigms

Hosting a foundation model for inference requires many choices, and
many of these decisions can affect the cost of your workload. One of
these choices includes the selection of a managed, serverless
deployment of a foundation model against a self-hosted option.

**Desired outcome:** When
implemented, this best practice describes a relationship between
cost and performance contextualized against model hosting and
inference paradigms. This relationship helps you evaluate
cost-benefit choices associated with the selection of an inference
paradigm.

**Benefits of establishing this best
practice:**

- [Measure
overall efficiency](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-dp.html) - It is helpful to understand
inference and hosting costs associated with the performance
requirements of foundation model.
- [Lower
spend on undifferentiated heavy lifting](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-dp.html) - More often than
not, it is beneficial to opt for a managed or serverless hosting
paradigm, due to the intractability of the total cost of
ownership for foundation model hosting.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Throughput sensitive workloads often require additional resources
to service inference requests at the rate they are being
submitted. Provisioned throughput, available through Amazon Bedrock, provides increased throughput capability for large
language models supporting generative AI workloads. If your
workload requires provisioned throughput to meet its performance
requirements, consider preferring longer commitment terms for
better unit costs. Validate your scaling requirements with shorter
duration commitments to avoid over-provisioning your workload.
Provisioned throughput is available for purchase in Amazon Bedrock. If the model you are using has throughput performance
needs or continuous model inference scale supports provisioned
throughput, consider purchasing a short-term. Test the improvement
and determine if the provisioned throughput improves your
application's performance. If there is a strong case for
provisioned throughput, consider purchasing a six-month plan, as
the unit cost for six months is usually lower than purchasing
month-over-month.

Consider a scenario where you want to serve inference capabilities for a single model for small, periodic workloads. Evaluate the cost of hosting this model on an Amazon SageMaker AI inference endpoint. Compare these costs against the cost of importing the model to Amazon Bedrock using Amazon Bedrock's Custom Model Import feature and using API-based inference. Evaluate the cost to deploy this model using either paradigm and compare them with respect to the total cost of ownership. Where performance trade-offs are negligible, deploy to the most cost-effective inference paradigm.

### Implementation steps

- Identify the nature of the demand for this workload.
- Compare the demand to the available hosting options, and
remove the high-cost options that do not satisfy the
workloads hosting requirements.
- Select and test the available optinos that satisfy the workload requirements for latency, throughput, and response quality.
- Implement the most appropriate, lower-cost hosting option for your model serving paradigm (for example, managed or self-hosted).

## Resources

**Related best practices:**

- [COST06-BP01](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_type_size_number_resources_cost_modeling.html)
- [COST06-BP02](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_type_size_number_resources_data.html)
- [COST09-BP01](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_manage_demand_resources_cost_analysis.html)

**Related documents:**

- [Tagging
Amazon Bedrock resources](https://docs.aws.amazon.com/bedrock/latest/userguide/tagging.html)
- [Inference
cost optimization best practices](https://docs.aws.amazon.com/sagemaker/latest/dg/inference-cost-optimization.html)

**Related examples:**

- [Track,
allocate and manage your generative AI cost and usage with
Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/track-allocate-and-manage-your-generative-ai-cost-and-usage-with-amazon-bedrock/)
- [Optimizing
costs of generative AI applications on AWS](https://aws.amazon.com/blogs/machine-learning/optimizing-costs-of-generative-ai-applications-on-aws/)
- [Analyze
Amazon SageMaker AI spend and determine cost optimization
opportunities based on usage, Part 1](https://aws.amazon.com/blogs/machine-learning/part-1-analyze-amazon-sagemaker-spend-and-determine-cost-optimization-opportunities-based-on-usage-part-1/)
