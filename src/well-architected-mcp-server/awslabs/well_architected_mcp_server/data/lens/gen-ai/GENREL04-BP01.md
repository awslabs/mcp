---
id: "GENREL04-BP01"
title: "Implement a prompt catalog"
pillar: "Reliability"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genrel04-bp01.html"
---

# GENREL04-BP01 Implement a prompt catalog

Prompt catalogs store and manage prompts and prompt versions. They
act as a reliable store for prompts for generative AI workloads.

**Desired outcome:** When
implemented, this best practice improves the reliability of your
generative AI workload by creating a central store for prompts that
can be used for generative AI workloads.

**Benefits of establishing this best
practice:**
[Manage
change through automation](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html) - Implementing a prompt catalog
helps to automate the process of deploying and rolling back prompt
versions.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Prompt catalogs function as a centralized system for
developing, testing, and managing prompts. Implement a prompt
catalog to maintain different versions of prompts. Prompts
should be released to a live version once passing the
appropriate testing thresholds and benchmarks. In the case
where a prompt results in unexpected or undesirable behavior,
a prompt catalog enables the ability to roll back to the
previous version.

Additionally, maintain versioned information on hyperparameter
ranges for prompts. Prompt behavior can change drastically
when tuning hyperparameters such as temperature, top_p, or
top_k. Value ranges for these hyperparameters should be paired
with and validated against prompt versions as part of the
prompt engineering process.

Prompt catalogs should maintain test results for a prompt
against several model versions. A given foundation model can
have several versions, and prompt test results for each model
version can vary accordingly. Consider developing a catalog
that maintains prompt versions for each of the available
models.

### Implementation steps

- Design catalog structure:

Define prompt metadata schema (like version, author, and purpose)
- Create categorization system for different prompt types
- Establish naming conventions and tagging standards
- Define access control requirements

- Implement version control:

Set up version tracking for prompts
- Create changelog management process
- Define rollback procedures
- Establish backup and recovery processes

- Create testing framework:

Define success criteria for prompts
- Establish validation procedures
- Create test suites for different use cases
- Set up automated testing pipelines

- Configure prompt metadata:

Document hyperparameter ranges
- Track performance metrics
- Record model compatibility
- Maintain usage statistics

- Establish governance processes:

Define approval workflows
- Create audit trails
- Set up review procedures
- Implement quality controls
- Codify in your organizations AI usage or policy document

## Resources

**Related best practices:**

- REL07-BP01
- REL08-BP02
- REL08-BP04

**Related documents:**

- [AWS re:Invent 2023
- Prompt Engineering Best Practices for LLMs on Amazon Bedrock
(AIM377)](https://www.youtube.com/watch?v=jlqgGkh1wzY)

**Related examples:**

- [Amazon Bedrock Prompt Management is now Available in GA](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-prompt-management-is-now-available-in-ga/)
