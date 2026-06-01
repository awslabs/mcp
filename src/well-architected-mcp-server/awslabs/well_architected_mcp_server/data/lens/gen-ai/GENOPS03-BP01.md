---
id: "GENOPS03-BP01"
title: "Implement prompt template management"
pillar: "Operational Excellence"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genops03-bp01.html"
---

# GENOPS03-BP01 Implement prompt template management

Implement and maintain a versioned prompt template management system
to achieve consistent and optimized performance of language models.
This best practice aims to provide a structured approach to managing
prompt templates, which helps teams systematically version, test,
and optimize prompts. By adhering to this practice, you can achieve
greater predictability in model behavior, enhance traceability of
changes, and improve overall operational efficiency. This leads to
more reliable language model deployments, reduced risks associated
with prompt modifications, and the ability to quickly roll back to
previous versions if needed. Ultimately, this best practice helps
you deliver higher-quality outputs and maintain compliance with
security and governance standards.

**Desired outcome:** You have a
robust, versioned prompt template management system in place. Key
processes involve testing and comparing different prompt variants,
capturing baseline model outputs, and regularly reviewing and
optimizing prompts based on performance metrics.

**Benefits of establishing this best
practice:**
[Safely
automate where possible](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - Automate prompt management,
reducing the undifferentiated heavy lifting associated with
traditional prompt management techniques.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Implement versioning for your prompt templates. Test and compare
different prompt variants to identify the most effective one, and
use variables for flexibility. Capture baseline metrics of the
model output and validate whether there are deviations from the
expected results. The baseline should be your functional
performance evaluation, which uses your ground truth data. This
evaluation constitutes the set of metrics you should use for
managing your prompt templates. Versioning should include
hyperparameters or ranges where applicable, as these can influence
the output of the model, similar to the prompt contents, and are
paired with the prompt itself during evaluation.

Amazon Bedrock Prompt Management is designed to help you with the
creation and testing of prompts for foundation models. You can use
Bedrock Prompt Management to create, edit, version, and share
prompts across teams. Its components include the prompts
themselves, their variables to be filled at runtime, variants, and
a visual builder interface. This can be integrated into
applications by specifying the prompt during model inference and
supports adding a prompt node to a flow.

Amazon Bedrock Flows is a feature that allows you to create
and manage advanced workflows without writing code. Using the
visual builder interface, you can link various elements including
foundation models, prompts, agents, knowledge bases, and other AWS
services. Flows supports versioning, rollback, and A/B testing.
You can test your flows directly in the AWS Management Console or
using the
[SDK
APIs](https://docs.aws.amazon.com/bedrock/latest/userguide/sdk-general-information-section.html).

### Implementation steps

- Set up Amazon Bedrock Prompt Management.

Create the initial prompt templates by developing a
foundational set of prompt templates tailored to your
use case
- Incorporate variables within prompts to enhance
flexibility and adaptability
- Implement a robust versioning system to track changes
and iterations of prompt templates

- Implement a baseline performance evaluation.

Compile a dataset of ground truth examples to serve as a
benchmark for model evaluation
- Identify and establish performance metrics relevant to
your application
- Conduct preliminary performance assessments to establish
a baseline

- Create and test prompt variants.

Develop several versions of each prompt to explore
different phrasings and structures
- Use Amazon Bedrock Flows to configure A/B testing
workflows for prompt variants
- Analyze the performance of each prompt variant to
determine the most effective options

- Integrate prompts into applications.

Use the Amazon Bedrock SDK to incorporate prompts during
model inference
- Integrate prompt nodes into Amazon Bedrock Flows
where appropriate to streamline application workflows

- Establish a regular review and optimization process.

Plan periodic performance evaluations to assess model
effectiveness
- Review evaluation outcomes to pinpoint areas requiring
enhancement
- Update and version prompts based on evaluation insights
to continually improve performance

- Set up cross-team collaboration.

Share prompts across teams using Amazon Bedrock Prompt
Management
- Establish and disseminate guidelines for prompt creation
and modification to maintain consistency and quality

## Resources

**Related best practices:**

- [OPS05-BP10](https://docs.aws.amazon.com/wellarchitected/latest/framework/ops_dev_integ_auto_integ_deploy.html)
- [OPS05-BP01](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_dev_integ_version_control.html)

**Related documents:**

- [Amazon Bedrock Prompt Template Examples](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-templates-and-examples.html)
- [AWS re:Invent 2023 - Prompt engineering best practices for LLMs on
Amazon Bedrock (AIM377)](https://www.youtube.com/watch?v=jlqgGkh1wzY)

**Related examples:**

- [Evaluating
prompts at scale with Prompt Management and Prompt Flows for
Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/evaluating-prompts-at-scale-with-prompt-management-and-prompt-flows-for-amazon-bedrock/)

**Related tools:**

- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/)
- [AWS SDK for Python (Boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
