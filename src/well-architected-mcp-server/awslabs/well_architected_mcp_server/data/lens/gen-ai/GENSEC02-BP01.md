---
id: "GENSEC02-BP01"
title: "Implement guardrails to mitigate harmful or incorrect model responses"
pillar: "Security"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec02-bp01.html"
---

# GENSEC02-BP01 Implement guardrails to mitigate harmful or incorrect model responses

Guardrails are powerful, expansive techniques associated with
reducing the risk of harmful, biased or incorrect model responses.
This best practice discusses why and how to implement guardrails in
generative AI workloads, as well as other complementary techniques.

**Desired outcome:** When
implemented, this best practice reduces the risk of a foundation
model returning harmful, biased or incorrect responses to a user. In
the case where a model does return an undesirable response, this
best practice defines a fallback action which enables the
application to continue without faltering.

**Benefits of establishing this best
practice:** [Automate
security best practices](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - Guardrails automate the
identification and remediation of undesirable model output.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Guardrails use and combine complex techniques to identify
undesirable model output, ranging from keyword identification and
regular expression matching to automated reasoning and
constitutional AI. Implementing all of these techniques manually
would be difficult and time-consuming. Consider using the Amazon Bedrock Guardrails API to scale the implementation of guardrails
in your generative AI workloads. Open-source guardrail and constitutional AI libraries exist as well for self-hosted models on Amazon SageMaker AI endpoints. Your organization’s AI policy should identify best practices for guardrail implementation for all model tasks and hosting paradigms in use across the organization.

There are several techniques to mitigating the generation of
harmful, biased, or factually incorrect responses from a
foundation model. Prompt engineering techniques like
chain-of-thought, logic-of-thought, and few-shot prompting
encourage a model to reason out the steps to generating a
response. Performant models can identify logic errors and correct
themselves before generating the actual response. RAG
architectures encourage models to search through knowledge bases
to identify factual information. Documents in a knowledge base are
used to contextualize and inform the final response, thus reducing
the chances of an incorrect generation. This approach requires
factually correct information to be present and searchable in the
knowledge base. You can apply guardrails to filter responses on
content, topic, or sensitive information. Be sure to define a
fallback behavior if a guardrail is tripped. For example, you may
precede the model's response with a disclaimer, or refuse to print
the model response. Both Amazon Bedrock and Amazon Q Business
feature guardrail capabilities to mitigate responses containing
hallucinations and references to hate, violence and abuse. Amazon Q Business provides administration controls to block certain
phrases and topics (for example, investment advice). Amazon Bedrock
Guardrails is available as an SDK, meaning you can apply
guardrails in custom generative AI workloads that are self-hosted.
Consider SDK alternatives like Amazon Bedrock Guardrails or the
Guardrails.AI package.

Guardrails are part of the solution to response validation.
Depending on the use case, response validation techniques can be
extended to incorporate human review, model-as-a-judge, or agent
actions. Human review, while the most time-consuming, provides the
greatest confidence that model responses are valid and
appropriate. Human review should be reserved for the most critical
model responses, and human reviewers should be highly trained.
Model-as-a-judge techniques are also effective at determining if a
model response requires intervention. Foundation models can be
powerful classifiers; they can classify model responses and take
action accordingly. One of those actions could be an agent flow,
which routes the response review to the appropriate process, be it
a simple output disclaimer or a full human review.

### Implementation steps

- Amazon Bedrock Guardrails:

Navigate to the Amazon Bedrock service and choose
Guardrails, Create Guardrail.
- Enter guardrail details, including a name and the message
for blocked prompts and responses.
- Configure content filter sensitivity based on categories
and known prompt attacks.
- Specify a list of denied topics.
- Specify word filters or provide custom words list.
- Specify sensitive information filters for PII or using
regular expressions.
- Configure automated reasoning checks for contextual
grounding and response relevance.

- Amazon Q Business guardrails:

Navigate to the Amazon Q Business service and choose
Admin Controls and Guardrails.
- Edit Global Controls for blocked words, response
personalization, LLM interaction, and data source
querying.
- Create topic controls supplying example messages which
trigger rules that control behavior.

## Resources

**Related best practices:**

- [SEC07-BP02](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_data_classification_define_protection.html)

**Related documents:**

- [Test
a guardrail](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-test.html)
- [Use
the ApplyGuardrail API in Your Application](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-independent-api.html)
- [Admin
controls and guardrails in Amazon Q Business](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/guardrails.html)
- [Amazon Transcribe Toxicity Detection](https://aws.amazon.com/transcribe/toxicity-detection/)

**Related examples:**

- [Implement
Model Independent Safety Measures with Amazon Bedrock
Guardrails](https://aws.amazon.com/blogs/machine-learning/implement-model-independent-safety-measures-with-amazon-bedrock-guardrails/)

**Related tools:**

- [Guardrails
AI](https://github.com/guardrails-ai/guardrails)
