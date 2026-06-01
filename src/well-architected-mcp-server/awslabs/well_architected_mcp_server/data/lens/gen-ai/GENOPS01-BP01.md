---
id: "GENOPS01-BP01"
title: "Periodically evaluate functional performance"
pillar: "Operational Excellence"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genops01-bp01.html"
---

# GENOPS01-BP01 Periodically evaluate functional performance

Implement periodic evaluations using stratified sampling and custom
metrics to maintain the performance and reliability of large
language models. This practice verifies that models remain accurate
and relevant over time by regularly assessing their performance
against ground truth data and specific evaluation criteria. By
employing stratified sampling, organizations can obtain a
representative subset of data that reflects the diversity of
real-world inputs, leading to more reliable performance metrics.
Custom metrics allow for tailored assessments that align with
specific business goals and user expectations. This practice helps
customers achieve consistent model performance, detect and address
model drift promptly, and integrate evaluation results into
continuous improvement processes.

**Desired outcome:** When
implemented, this best practice improves the ability to identify and
remediate performance degradation issues in model responses.

**Benefits of establishing this best
practice:**

- [Implement
observability for actionable insights](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - Model responses
to prompts can be observed using key performance indicators
(KPIs) to determine adherence to or deviation from acceptable
performance levels.
- [Anticipate
failure](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - Periodic review of the model's performance
levels helps you proactively identify deviations in its
performance. This is because foundation models are inherently
non-deterministic with a realistic chance of failure.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Evaluations can be conducted by periodically running ground truth
data and applying sampling techniques to run metrics for
monitoring purposes. Feed your prompts into the model to generate
outputs, compare those outputs to the known ground truth values,
and analyze the results to track the model's performance over
time, identifying potential drifts or degradation.

You can employ stratified sampling techniques to verify diverse
data representation within the sample set. Divide your ground
truth data into relevant categories (for example, different user
personas), and randomly sample from each category to provide a
balanced representation in the evaluation set. Consider
periodically updating your ground truth dataset as the inputs and
usage of your workload change over time. Address data drift where
actual usage diverges from your initial ground truth set.

You can use the model evaluation feature built-in with Amazon Bedrock or open-source libraries like
[fmeval](https://github.com/aws/fmeval) or
[ragas](https://docs.ragas.io/en/stable/).
Use Amazon Bedrock model invocation logging to collect metadata,
requests, and responses for model invocations in your account.

For Amazon SageMaker AI, you can set up manual evaluations for a
human workforce using Studio, automatically evaluate your model
with an algorithm using Studio, or automatically evaluate your
model with a customized workflow using the fmeval library.

The fmeval library provides a framework for defining and using
custom metrics. By creating a custom metric class, you can
encapsulate the logic for calculating a specific evaluation
criterion tailored to your use case. Use this to continuously
assess your language models using both standard metrics provided
by fmeval and your own specialized metrics.

Your organization’s AI policy should define the effective minimum performance levels for generative AI workloads, as well as how to validate performance on an ongoing basis. Consider identifying a single-threaded workload owner responsible for the operational considerations pertaining to ongoing performance evaluations. Run these evaluations when new candidate models are available, or when model customization techniques are applied. For example, fine-tuned and customized models should be subject to the same evaluation criteria and cadence as non-customized models.

### Implementation steps

- Create a ground truth dataset.

Verify that you have diverse data representation
- Consider various user personas and use cases

- Apply stratified sampling techniques.

Categorize ground truth data into relevant groups
- Randomly sample from each group to achieve balanced
representation

- Establish periodic evaluation processes.

For Amazon Bedrock:

Use the built-in model evaluation feature
- Implement model invocation logging

- For Amazon SageMaker AI:

Configure manual evaluations using Amazon SageMaker AI
Studio.
- Set up automatic evaluations using Amazon SageMaker AI
Studio or the fmeval library

- Define custom metrics.

Use the fmeval library to create custom metric classes
- Encapsulate logic for calculating specific evaluation
criteria

- Perform model evaluations.

Input prompts into the model
- Generate outputs and compare them to ground truth values
- Analyze results to track performance over time

- Monitor for performance drifts.

Identify potential degradation in model performance
- Address data drift where actual usage diverges from the
initial ground truth

- Regularly update the ground truth dataset.

Reflect changes in workload inputs and usage patterns
- Maintain the relevance of evaluation data

**Additional recommendations**

- Use open-source libraries.

Consider using libraries like ragas for additional
evaluation capabilities
- Explore complementary metrics and evaluation techniques

- Implement automated workflows.

Integrate evaluation processes into CI/CD pipelines
- Set up alerts for significant performance changes

## Resources

**Related best practices:**

- OPS11-BP11

**Related documents:**

- [Amazon SageMaker AI Model Evaluation](https://docs.aws.amazon.com/sagemaker/latest/dg/model-optimize-evaluate.html)
- [Evaluating
Models in Amazon Bedrock](https://aws.amazon.com/bedrock/evaluations/)
- [Data
and model quality monitoring with Amazon SageMaker AI Model
Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html)

**Related videos:**

- [AWS re:Invent 2024 - Streamline RAG and model evaluation with
Amazon Bedrock (AIM359)](https://www.youtube.com/watch?v=7BP9nwFlFws)

**Related examples:**

- [SageMaker AI
Model Evaluation Examples](https://docs.aws.amazon.com/sagemaker/latest/dg/ex1-test-model.html)
- [Bedrock
Model Evaluation Demo](https://aws.amazon.com/awstv/watch/1a5442fac30/)
- [Examples
with fmeval](https://github.com/aws/fmeval/tree/main/examples)

**Related tools:**

- [Amazon SageMaker AI Model Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html)
- [fmeval
library](https://github.com/aws/fmeval)
- [Amazon CloudWatch](https://docs.aws.amazon.com/sagemaker/latest/dg/monitoring-cloudwatch.html)
- [AWS Step Functions](https://aws.amazon.com/blogs/aws/build-generative-ai-apps-using-aws-step-functions-and-amazon-bedrock/)
