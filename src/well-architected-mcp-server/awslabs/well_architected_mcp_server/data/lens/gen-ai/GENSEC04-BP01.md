---
id: "GENSEC04-BP01"
title: "Implement a secure prompt catalog"
pillar: "Security"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec04-bp01.html"
---

# GENSEC04-BP01 Implement a secure prompt catalog

Prompt catalogs facilitate the engineering, testing, versioning and
storage of prompts. Implementing a prompt catalog improves the
security of system and user prompts.

**Desired outcome:** By implementing
this best practice, you can securely store and manage your prompts
and quickly access those prompts from a central location. Prompt
catalog access can be protected with identity-based permissions.

**Benefits of establishing this best
practice:**
[Apply
security at all layers](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - Prompt catalogs implement security
at the prompt management layer of the generative AI workload.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Prompt catalogs are secure, centralized storage for prompts and
prompt versions. Building a prompt catalog is possible using
traditional database architectures. However, prompt catalogs are
not meant for the same use as databases. Taking a prompt version
and dynamically adding it to a prompt flow are common scenarios
and functions which could be handled at the catalog layer. Thoroughly define the governance and management of a prompt catalog in your organization AI policy document, and include details such as intended prompt usage and process details for modifying prompts.

Consider storing prompts in a managed prompt catalog. Amazon Bedrock's Prompt Management catalog enables customers to create
prompts, test them against several foundation models, and manage
version lifecycles. The Amazon Bedrock Prompt Management catalog makes it
straightforward to develop prompt testing capabilities, especially
as new models become available for customers to use. Amazon Bedrock
Prompt Management API actions can be secured through IAM policy
documents. Develop roles with least privilege access to prompt
actions like CreatePromptVersion or
GetPrompt. Consider developing roles specific
to prompt engineering or agent workflow testing tasks. Developing
roles which enforce a separation of duties helps implement a
least privilege security architecture around prompt development
and lifecycle management.

Amazon Bedrock Prompt Management features an automated prompt
optimization feature which optimizes the prompt. Consider using
automated prompt optimization before cataloging prompts into the
Prompt Management catalog. When evaluating prompts at scale,
consider using Amazon Bedrock Flows. Flows
facilitate the testing of prompts in a highly orchestrated manner.
Evaluate if prompt flows can be leveraged to test prompts before
they are catalogued.

### Implementation steps

- Navigate to Amazon Bedrock Prompt Management and create a
prompt.
- Define the name, description, and encryption of that prompt.
- Draft the prompt, specifying variables and hyperparameters.
- Test the prompt against one or more foundation models.
- Save an acceptable version of the prompt.
- Revisit prompt engineering and testing regularly to verify
your prompts behave as expected.

Consider extending CI/CD workflows to incorporate prompt
engineering.

## Resources

**Related best practices:**

- [SEC08-BP03](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_protect_data_rest_automate_protection.html)

**Related documents:**

- [Construct
and Store Reusable Prompts with Prompt Management in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-management.html)

**Related examples:**

- [Implementing
Advanced Prompt Engineering with Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/implementing-advanced-prompt-engineering-with-amazon-bedrock/)
- [Build
and scale generative AI applications with Amazon Bedrock](https://workshops.aws/categories/Prompt%20Engineering)
