---
id: "GENREL03-BP02"
title: "Implement timeout mechanisms on agentic workflows"
pillar: "Reliability"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genrel03-bp02.html"
---

# GENREL03-BP02 Implement timeout mechanisms on agentic workflows

Implement controls to detect and terminate long-running unexpected
workflows.

**Desired outcome:** When
implemented, this best practice improves the reliability of your
generative AI workload by freeing resources that might have been
consumed by unexpected long-running execution loops.

**Benefits of establishing this best
practice:**
[Automatically
recover from failure](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html) - Implementing agent timeouts helps to
reduce the likelihood of blocking failures on agentic workflows and
executions.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Agentic workflows act on behalf of a user by making calls to
external systems. External systems may themselves perform
several time-consuming tasks which the agent is not aware of,
resulting in idle agents that could run for an extended
period. To maintain a reliable agentic system, implement
controls to manage agentic timeout.

One approach to controlling agentic runtime or lifecycle is to
implement runtime timeouts on the external infrastructure. For
example, if an agent makes a call to a function through an
Action Group, consider applying a timeout to the corresponding
function. The timeout should be set to include the maximum
allowable time needed to complete a process, accounting for
additional latency for edge cases such as cold starts. You may
consider rounding this value up to avoid unnecessary early
terminations.

Alternatively, consider connecting agentic workflows to an
event system, developing an asynchronous process management
architecture. Introducing an asynchronous event system gives
users the most flexibility and visibility into agent process
lifecycle or flow. By requiring the compute underpinning an
Action Group to publish events, workload owners maintain
insight into where an agent may encounter stalled flow or
process. Consider using events to publish agent updates and
act appropriately to stop long-running invocations.

Error handling at the agent layer should be transparent to
users. When errors occur, communicate clear details about the
issue while maintaining system security by avoiding exposure
of sensitive internal information. The response should outline
specific next steps so that users can complete their tasks
independently if the agent remains unavailable. This approach
promotes operational resilience while maintaining security
best practices, as users receive actionable guidance without
compromising system integrity.

### Implementation steps

- Create an agent workflow configuration:

Define maximum runtime thresholds
- Set up timeout controls at function and workflow levels
- Configure event publishing for process monitoring

- Implement timeout mechanisms:

Add timeouts at the agent layer to terminate sessions waiting for user input
- Configure timeouts on external compute resources
- Set up dead letter queues for timed-out processes

- Establish monitoring and alerting:

Track agent execution times
- Monitor timeout frequency
- Alert on repeated timeouts

- Define recovery procedures:

Create graceful termination processes
- Implement cleanup routines for timed-out sessions
- Set up automated retry mechanisms where appropriate

## Resources

**Related best practices:**

- REL05-BP05

**Related documents:**

- [AWS re:Invent 2023
- Simplify generative AI app development with Agents for
Amazon Bedrock (AIM353)](https://www.youtube.com/watch?v=JNZPW82uv7w)
- [Automate tasks in
your application using AI agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)

**Related examples:**

- [Best
practices for building robust generative AI applications with
Amazon Bedrock Agents - Part 1](https://aws.amazon.com/blogs/machine-learning/best-practices-for-building-robust-generative-ai-applications-with-amazon-bedrock-agents-part-1/)
- [Best
practices for building robust generative AI applications with
Amazon Bedrock Agents - Part 2](https://aws.amazon.com/blogs/machine-learning/best-practices-for-building-robust-generative-ai-applications-with-amazon-bedrock-agents-part-2/)
