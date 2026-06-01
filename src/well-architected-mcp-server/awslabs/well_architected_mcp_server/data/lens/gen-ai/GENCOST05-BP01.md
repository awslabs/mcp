---
id: "GENCOST05-BP01"
title: "Create stopping conditions to control long-running workflows"
pillar: "Cost Optimization"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gencost05-bp01.html"
---

# GENCOST05-BP01 Create stopping conditions to control long-running workflows

Agentic workflows can be long-running, which can incur additional cost
to your application. Develop controls to limit agents from running
for extended periods of time without stopping.

**Desired outcome:** Maximum costs
for an agent's runtime can be predicted based on the implemented
stopping conditions.

**Benefits of establishing this best
practice:**
[Measure
overall efficiency](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-dp.html) - Agentic workflows can be long-running, which can add additional cost to your workload. By establishing stopping conditions for long-running agentic workflows, you can optimize resources, improve user experience, and optimize workload costs.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

For generative AI prompt flows where you lack control over the
duration of the workflow, consider introducing a time-out
mechanism or regaining control over the flow. This scenario is
particularly common within agentic architectures. Agent
architectures assist customers by taking on additional tasks.
Sometimes these tasks can run for an extended duration, which may
incur additional cost considerations, especially when they call
external resources. Consider introducing a timeout over the agent
to limit long-running processes from incurring costs
unnecessarily. Additionally, evaluate asynchronous workflows
orchestrated through events. Asynchronous workflows create
opportunities to interrupt or halt long-running events after an
extended duration. Consider the entire architecture before
determining the best place to interrupt long-running workflows for
cost savings.

### Implementation steps

- Estimate the maximum time needed for an agent to complete
its runtime.

Include model response times, tool execution times, and network latency in the estimation.

- Implement stopping conditions that enable an agent to run to
the maximum duration.

Stopping conditions may be a timeout mechanism like the
one in Amazon Bedrock.
- Alternatively, stopping conditions may be implemented in
the prompt flow layer or within a software abstraction
layer.

- Re-architect your workflows to facilitate stopping conditions.

Set timeouts on external tools such as Lambda functions or API endpoints, verify that your prompts understand how to handle timeout responses.
- Set token limits on model responses to simulate timeout functionality by stopping models from printing long-running responses.

## Resources

**Related best practices:**

- [COST01-BP06](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_cloud_financial_management_proactive_process.html)

**Related documents:**

- [AWS re:Invent 2023
- Simplify generative AI app development with Agents for
Amazon Bedrock (AIM353)](https://www.youtube.com/watch?v=JNZPW82uv7w)
- [User
Guide: Amazon Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)

**Related examples:**

- [Best
practices for building robust generative AI applications with
Amazon Bedrock Agents - Part 1](https://aws.amazon.com/blogs/machine-learning/best-practices-for-building-robust-generative-ai-applications-with-amazon-bedrock-agents-part-1/)
- [Best
practices for building robust generative AI applications with
Amazon Bedrock Agents - Part 2](https://aws.amazon.com/blogs/machine-learning/best-practices-for-building-robust-generative-ai-applications-with-amazon-bedrock-agents-part-2/)
