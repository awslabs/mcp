---
id: "GENSEC05-BP01"
title: "Implement least privilege access and permissions boundaries for agentic workflows"
pillar: "Security"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec05-bp01.html"
---

# GENSEC05-BP01 Implement least privilege access and permissions boundaries for agentic workflows

Implementing least privilege and permissions bounded agents limits
the scope of agentic workflows and helps stop them from taking
actions beyond their intended purpose on behalf of the user. This
best practice describes how to reduce the risk of excessive agency.

**Desired outcome:** When
implemented, you can limit and constrain agents from assuming
excessive autonomy. This helps prevent agents from performing
unauthorized or unintended actions in automated scenarios.

**Benefits of establishing this best
practice:**

- [Implement
a strong identity foundation](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - Least privilege access
permissions enable agents to operate as authorized users within a
defined and limited context.
- [Apply
security at all layers](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - Applying least privilege access
permissions on agents improves security for agent architectures at
the agent layer.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Agents are designed to automate processes or call external
functions using the reasoning capabilities of generative AI.
Managed generative AI services such as Amazon Q Business can
automate common business processes using agents, such as opening a
ticket through a chat interface. Agents introduce a risk called
*excessive agency*, where an agent determines
the best solution to a problem is to take broader actions beyond
its scope. This is not inherently malicious but rather an
unintended consequence of automation, especially since the agent
has little knowledge beyond the prompt as to what behaviors are
permitted or not.

Consider developing permissions boundaries on foundation model
requests and agentic workflows. For individual prompts to a
foundation model, the permission boundary for the role making the
model request should only provide access to the systems,
guardrails, and data sources necessary to generate a response.
This is also true for agentic workflows. In Amazon Bedrock, agents
have execution roles. Amazon Bedrock Flows have service roles. The
roles attached to agents and prompt flows should be developed with
least privilege access principles in mind. This is especially true
concerning roles that facilitate access to data sources like
Amazon Kendra or compute resources like AWS Lambda functions. Permission boundaries and least privilege access for an agent should be shared across models, particularly where multiple models or agents are servicing a prompt.

Additionally, consider creating developer roles specific to the
tasks being conducted. For example, consider creating separate IAM
roles for the prompt engineer creating an agentic workflow and the
security engineer creating the agent workflows IAM service role.
Create a logical separation of duties to help to reduce excessive
agency for resources. Additionally, consider defining permission
boundaries for roles. A permission boundary sets the maximum
permissions which can be given to a role. These techniques can be
implemented at the account level. A combination of these
techniques may be the best approach, depending on your
environment's specific implementation needs. Define permission boundaries and policy documents like this in your organization’s AI policy document, with clear instructions on how to modify these as workload requirements change.

### Implementation steps

- Review your organization's identity and access management
guidelines to determine the best path to create least
privileged roles.

Some organizations use service control policies to have
central control over the maximum available permissions
for the IAM users and IAM roles.
- Review your organization's recommended templates or
procedures to create IAM roles or users. Use existing
templates and previously created policies if available.

- When creating IAM roles for agents, define a scoped policy
with least privilege access.

Specify intended resource ARNs for the defined
permission and API actions.
- Consider defining conditions to further restrict the
allowed action to trusted traffic, such as requests
coming from a specific VPC.

- Attach the policy document to a role assumable by a specific
set agents.

Permissions boundaries can be applied at the role level
to prevent inadvertent authorization to additional
services.
- Condition statements can be applied at the role's trust
policy instead of the policy document consult your
security specialist when building role and policy
conditions.

- Implement user confirmation for the agent, requiring users
to confirm agent actions and mitigating the risk of
excessive agency.

## Resources

**Related best practices:**

- SEC02-BP01
- SEC02-BP02
- SEC02-BP06
- SEC03-BP01
- SEC03-BP02

**Related documents:**

- [AWS re:Invent 2023-Use new IAM Access Analyzer features on your
jouney to least privilege](https://www.youtube.com/watch?v=JpemUkU8INA)
- [OWASP
Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Amazon Bedrock User Guide - User Confirmation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-userconfirmation.html)

**Related examples:**

- [Techniques
for Writing Least Privilege IAM Policies](https://aws.amazon.com/blogs/security/techniques-for-writing-least-privilege-iam-policies/)
- [When
and Where to use IAM Permissions Boundaries](https://aws.amazon.com/blogs/security/when-and-where-to-use-iam-permissions-boundaries/)
- [Example
Permissions Boundaries](https://github.com/aws-samples/example-permissions-boundary)
- [Overseeing
AI Risk in a Rapidly Changing Landscape](https://aws.amazon.com/blogs/enterprise-strategy/overseeing-ai-risk-in-a-rapidly-changing-landscape/)
- [Design
secure generative AI application workflows with Amazon Verified Permissions and Amazon Bedrock Agents](https://aws.amazon.com/blogs/machine-learning/design-secure-generative-ai-application-workflows-with-amazon-verified-permissions-and-amazon-bedrock-agents/)
