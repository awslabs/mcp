---
id: "GENPERF01-BP01"
title: "Define a ground truth data set of prompts and responses"
pillar: "Performance Efficiency"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genperf01-bp01.html"
---

# GENPERF01-BP01 Define a ground truth data set of prompts and responses

*Ground truth data* facilitates model testing
for use case specific scenarios and should be developed and
curated for generative AI workloads. Ground truth data is a
curated set of prompts and responses that describe the ideal
workflow with a model.

**Desired outcome:** When
implemented, this best practice enables the measurement of a
model's performance for a set of tasks, accelerating model
evaluation and enabling model customization workflows.

**Benefits of establishing this best
practice:**
[Experiment
more often](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html) - Ground truth testing facilitates rapid
experimentation and customization for models on tasks specific
to your workload's unique requirements.

**Level of risk exposed if this best
practice is not established:** Medium

## Implementation guidance

*Ground truth data*, also known as a
*golden dataset*, is data considered to be
of the highest quality in regard to a specific use case.
Ground truth data for generative AI workloads are oftentimes
prompt-response pairs. For a simple workflow, a golden dataset
might be dozens, hundreds, thousands or more sample prompts
and their corresponding expected responses. There may be
several prompts containing variations of the same ask, with
several responses describing variations of an acceptable
response. More complex workflows like retrieval augmented
generation or agentic workflows may require variations on this
paradigm.

Ground truth data is vital for the efficient testing of
data-driven and generative AI workloads. Develop ground truth
data for your generative AI applications to facilitate the
rigorous and uniform testing of large language models. When
equipped with a ground truth dataset for a use case, you can
automate the testing and evaluation of models. New models can
quickly be evaluated to determine if their performance for a
specific use case meets the current model's high bar.

Ground truth prompts should be clear and succinct, grouped
together by variations of the same ask. Ground truth responses
should similarly be clear and succinct, covering a range of
acceptable responses. When developing a ground truth data set,
don't be overly concerned with slight differences in prompts
that essentially ask a model to perform the same task. Prompts
in the ground truth data set should be specific to the kinds
of tasks you expect a model to solve. Consider ground truth
data as a living artifact, one that changes and extends based
on the use cases being tested and the usage paradigms being
implemented.

Prompt-responses pairs are the core of a ground truth dataset,
but ground truth data needs additional meta-data to be viable
for the extent of generative AI usage paradigms that could be
tested. For example, agent workflows perform tasks on behalf
of a requester, using its judgment to discern how to interpret
a response from an external system. An agent workflow may
synthesize several intermediary responses before the language
model delivers a final response to the user. Ground truth data
should be able to capture an ideal prompt flow, tracing the
workflow of the agent through various systems. This same
practice could be applied to workflows interacting with
multiple models.

Develop ground truth data in accordance with your
organization's AI policy. For example, if your organization's
AI policy prohibits testing models against production data,
your golden dataset should contain references to data which is
functionally equivalent to production data. Develop mock data
sets for testing, and mock endpoints for testing agentic
flows. The golden dataset should contain the instructions
required for a testing harness to run tests autonomously
against any model endpoint available, including self-hosted
language models.

In addition to facilitating rapid model testing and
evaluation, golden datasets can be used to quickly fine-tune
models or distill student models from teacher models. Model
customization workflows require high-quality data for
customization. Maintaining a robust golden dataset for each
use case can accelerate your ability to customize models.

### Implementation steps

- Define a series of prompts and their expected responses.

Consider using Amazon SageMaker Ground Truth or similar
to scale the curation of this dataset.
- Enrich prompt-response pairs with relevant meta-data in
accordance with your organization's AI policy.

- Store the data in a way which facilitates a
dictionary-style lookup of the data.

The first several layers could be organizational,
referring to abstractions like language, business
domain, or use case.
- The last layer includes the prompt-response pairs, where
the prompt is the key and the expected response is the
value.
- Store the data in an object-store such as Amazon S3.

- Create a data dictionary to facilitate access to the
ground truth data.

Crawl the object-store using an AWS Glue Crawler to
build the data dictionary.

- Develop a testing harness that can automatically test
models as they are made available using the ground truth
data.

Query segments of the ground-truth dataset using a
federated query solution such as Amazon Athena.
- Incorporate mock production data and tooling for more
advanced workflows such as agents or RAG.

- Define test scenarios corresponding to your golden
dataset and adhere to your organization's AI policy.

Define metrics to test models against as may be required
by your organization's AI policy.
- Track model performance across various tests and
metrics, carefully evaluating the trade-offs across
models.

## Resources

**Related best practices:**

- PERF05-BP01
- PERF05-BP03
- [MLPER03](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlper-03.html)
- [MLPER04](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlper-04.html)
- [MLPER16](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlper-16.html)

**Related documents:**

- [Understand
options for evaluating large language models with SageMaker AI
Clarify](https://docs.aws.amazon.com/sagemaker/latest/dg/clarify-foundation-model-evaluate.html)
- [Customize
your model to improve its performance for your use case](https://docs.aws.amazon.com/bedrock/latest/userguide/custom-models.html)
- [Amazon SageMaker AI JumpStart Foundation Models](https://docs.aws.amazon.com/sagemaker/latest/dg/jumpstart-foundation-models.html)
- [Automate
data labeling](https://docs.aws.amazon.com/sagemaker/latest/dg/sms-automated-labeling.html)

**Related examples:**

- [Customize
models in Amazon Bedrock with your own data using fine-tuning
and continued pre-training](https://aws.amazon.com/blogs/aws/customize-models-in-amazon-bedrock-with-your-own-data-using-fine-tuning-and-continued-pre-training/)
- [High-quality
human feedback for your generative AI applications from Amazon SageMaker Ground Truth Plus](https://aws.amazon.com/blogs/machine-learning/high-quality-human-feedback-for-your-generative-ai-applications-from-amazon-sagemaker-ground-truth-plus/)
