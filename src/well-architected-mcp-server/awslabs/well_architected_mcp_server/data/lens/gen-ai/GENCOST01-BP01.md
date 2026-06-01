---
id: "GENCOST01-BP01"
title: "Right-size model selection to optimize inference costs"
pillar: "Cost Optimization"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gencost01-bp01.html"
---

# GENCOST01-BP01 Right-size model selection to optimize inference costs

Foundation model costs vary greatly across the various foundation
model providers, model families and sizes, and model hosting
paradigms. It can be advantageous to use cost as a factor when
selecting models. Understand the models available to you, as well as
the requirements of your workload, to make an informed, cost-aware
decision.

**Desired outcome:** When
implemented, this best practice helps you manage spend on foundation
model inference without guessing at the capacity requirements for a
foundation model.

**Benefits of establishing this best
practice:** [Measure
overall efficiency](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-dp.html) - It is helpful to understand inference
and hosting costs associated with the performance requirements of
foundation model.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Foundation models have several cost-dimensions, some of which
change depending on the hosting paradigm (managed or self-hosted).
Traditionally, managed models charge for consumption measured in
token input and token output. Self-hosted models charge using
traditional infrastructure costs.

For managed models hosted on Amazon Bedrock, different models
charge differently for the number of tokens input and output.
Oftentimes, newer and larger models may have higher cost compared
to older or smaller models. Self-hosted models on Amazon EC2 or
Amazon SageMaker AI inference endpoints charge based on uptime, as
well as additional costs storage and network costs.

When optimizing for cost, consider testing with a smaller model
first, and gradually increase model size and capabilities until an
acceptable model is selected. The criteria for an acceptable model
will change based on the use case of the workload. By starting
with the smallest model, you improve the chances of selecting a
model with the most cost-effective token input and output cost.
Alternatively, optimize self-hosted model infrastructure based on the model used and the workload's usage pattern. Consult the model card or technical documentation for recommendations on instance size and capacity, right-sizing based on usage patterns.

Deploy multiple models to a single, multi-model endpoint where appropriate. Right-size as an ongoing activity. As newer models become
available, the workload needs change, and as prompting and
orchestration are refined, smaller, more cost-effective models
should be evaluated against your workload's needs to continually
optimize.

Consider decomposing your workload and routing to
different sized models based on the specific needs of each
inference request. Route less complicated inferences to smaller,
more cost-effective models while assessing quality to maintain
high quality across variably complicated inference requests. For
managed models hosted on Amazon Bedrock, consider intelligent
prompt routing for dynamic routing between models in the same
model family. Alternatively, weight the benefits of developing a
custom prompt routing layer. In some cases, real-time inference may not be required. In those instances, elect for a less expensive inference paradigm such as batch inference.

### Implementation steps

- Identify the minimum performance requirements for a
foundation model.
- Determine the models available which meet that minimum
performance bar.
- Select the most cost-efficient model based on the
prioritized cost dimensions (like hosting paradigm, model
size, or token cost).
- Continuously evaluate model selection to validate the
highest performance is being achieved at the lowest possible
price-point.

## Resources

**Related best practices:**

- [COST01-BP02](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_cloud_financial_management_partnership.html)
- [COST05-BP01](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_select_service_requirements.html)
- [COST06-BP01](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_type_size_number_resources_cost_modeling.html)
- [COST07-BP03](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_pricing_model_third_party.html)
- [COST09-BP01](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_manage_demand_resources_cost_analysis.html)

**Related documents:**

- [Tagging
Amazon Bedrock resources](https://docs.aws.amazon.com/bedrock/latest/userguide/tagging.html)

**Related examples:**

- [Track,
allocate and manage your generative AI cost and usage with
Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/track-allocate-and-manage-your-generative-ai-cost-and-usage-with-amazon-bedrock/)
- [Optimizing
costs of generative AI applications on AWS](https://aws.amazon.com/blogs/machine-learning/optimizing-costs-of-generative-ai-applications-on-aws/)
