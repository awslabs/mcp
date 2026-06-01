---
id: "GENREL03-BP01"
title: "Use logic to manage prompt flows and gracefully recover from failure"
pillar: "Reliability"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genrel03-bp01.html"
---

# GENREL03-BP01 Use logic to manage prompt flows and gracefully recover from failure

Leverage conditions, loops, and other logical structures at the
prompt management or application layer to reduce the risk of an
unreliable experience.

**Desired outcome:** When
implemented, this best practice improves the reliability of your
generative AI workload by reducing the likelihood of performance
degradation logical errors in your prompt flows.

**Benefits of establishing this best
practice:**
[Automatically
recover from failure](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html) - Implementing recovery logic in
generative AI workflows helps to reduce potentially blocking
failures, while encouraging generative AI applications to gracefully
recover automatically.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Define expected behavior for generative AI applications
before, during, and after prompts. Create layers of
abstraction between users and models to facilitate retries,
error handling, and graceful failures. For multi-step prompt
flows, implement logic statements to check if your prompts
contain the expected information. Apply similar logic to
verify your model's respond with expected content.

For prompt flows containing data from external sources,
implement logic to verify the relevant data from the external
source exists. Define a fallback action or default modality in
the absence of relevant data. Apply similar reasoning to model
responses enriched with embeddings from a vector search
engine. Consider applying checks on the model's response to
identify the relevance of the returned data or a fallback
action if no data is returned at all.

Agentic workflows commonly make calls to external systems.
Develop agents with error handling in mind. Consider how
errors are propagated back up to agents. Upon receiving an
error, an agent should take appropriate action to retry or
gracefully fail. One way to accomplish this is to have the
agent classify responses from external systems as actionable
or not. Actionable responses are anticipated and
well-understood responses (for example, a database query
returning at least one result). An inactionable response
traditionally requires error handling at the software layer
(for example, error codes or empty responses). Agents can be
prompted to classify responses in these cases and take action
appropriately. This method may serve to reduce non-determinism
and increase reliability of agent workflows.

When developing multistep prompt flows or prompt chains,
consider using Amazon Bedrock Flows to orchestrate multistep
prompts. Bedrock Flows enables graceful failure and recovery
for long prompt chains, which allows your applications to take
appropriate action on failure. Bedrock Flows has nodes for
controlling flow logic, which include iterator nodes and
condition nodes. Customers may consider using these nodes to
implement graceful recovery instead of developing a custom
abstraction layer.

### Implementation steps

- Establish error classification system:

Categorize common failure types
- Define severity levels
- Create response templates for each error category
- Set up automated detection mechanisms

- Implement recovery mechanisms:

Design retries strategies with exponential backoff
- Create fallback prompt templates
- Develop circuit breaker implementations
- Set up automated recovery workflows

- Configure monitoring and alerting:

Track recovery success rates
- Monitor remediation effectiveness
- Set up alerts for repeated failures
- Implement performance tracking

- Create continuous improvement process:

Analyze failure patterns
- Update remediation strategies
- Refine prompt templates
- Optimize recovery workflows

## Resources

**Related best practices:**

- [REL05-BP01](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_graceful_degradation.html)

**Related documents:**

- [Demo
- Amazon Bedrock Flows](https://www.youtube.com/watch?v=_Bmk6peAHao)
- [Build
an end-to-end generative AI workflow with Amazon Bedrock
Flows](https://docs.aws.amazon.com/bedrock/latest/userguide/flows.html)

**Related examples:**

- [Amazon Bedrock Flows is now generally available with enhanced safety
and traceability](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-flows-is-now-generally-available-with-enhanced-safety-and-traceability/)
- [Simplifying
the Prompts Lifecycle with Prompt Management and Prompt Flows
for Amazon Bedrock Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/c81935bc-0b43-4bd6-bd01-db45f847d6bd/en-US)
