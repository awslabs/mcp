---
id: "GENOPS04-BP01"
title: "Automate generative AI application lifecycle with infrastructure as code (IaC)"
pillar: "Operational Excellence"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genops04-bp01.html"
---

# GENOPS04-BP01 Automate generative AI application lifecycle with infrastructure as code (IaC)

Implementing and managing IaC is crucial for consistent,
version-controlled, and automated infrastructure deployment across
environments. This practice streamlines deployment, reduces errors,
and enhances team collaboration. IaC helps customers achieve
efficiency, reliability, and scalability in infrastructure
management, which allows for rapid iteration, straightforward
rollback, and improved governance and results in secure deployments.

**Desired outcome:** After
implementing the practice of automating the lifecycle management of
generative AI workloads using IaC, customers have version control
infrastructure automated through CI/CD pipelines.

**Benefits of establishing this best
practice:**
[Safely
automate where possible](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - Define your entire workload and its
operations (applications, infrastructure, configuration, and
procedures) as code, facilitating infrastructure level change
management, infrastructure version control, and advanced paradigms
such as self-healing infrastructure.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Automate your application development and migration through stages
using IaC principles. When selecting your tool stack, consider
your team's skills and project requirements. Use tools such as AWS Cloud Development Kit (AWS CDK), AWS CloudFormation, or Terraform
to define and manage the infrastructure resources required for
your application. These resources may include Amazon Bedrock,
Amazon API Gateway, AWS Lambda functions, and AWS Data Pipelines, all of which help you create a reproducible and
version-controlled stack.

Store your IaC templates in a version control system like Git.
This practice facilitates collaboration among team members, allows
for tracking changes over time, and enables rolling back to
previous versions if necessary.

Implement a CI/CD pipeline using AWS CodePipeline, Jenkins, or a
similar tool. This pipeline should initiate on code changes, run
tests on your IaC templates, and automatically deploy
infrastructure changes.

Manage your IaC templates to handle multiple environments such as
development, testing and staging, and production. To maintain
consistency across environments, use the same templates with
different parameters.

For Hyperpod, use AWS CloudFormation, AWS CDK, or Terraform to
define clusters, VPCs, security groups, EKS node groups,
networking policies, and Amazon SageMaker AI resources.

For Amazon EKS, describe your Kubernetes deployments, secrets
management, and ML workflows in YAML or Helm charts, and then
manage those using CI/CD pipelines to automatically provision
and update infrastructure.

For Slurm, automate creation and scaling of compute nodes,
tracker scripts, and cluster configuration using the same IaC
tools.

HyperPod Recipes serve as the cornerstone for implementing
operational task automation by providing pre-built automation
frameworks that reduce the need for manual operational tasks
in distributed training environments. These recipes deliver
IaC templates that automatically provision, configure, and
manage complex training workflows across both EKS and Slurm
orchestrated clusters, directly addressing the core principle
of reducing manual effort and minimizing human error in
operational activities.

Establish practices and controls to help you maintain
compliance of your resources, like using AWS Config to track
resource configurations. Implement Service Catalog for
standardized resource provisioning, and regularly audit your
IaC templates for security best practices and compliance.

Be mindful of the time and cost involved in model training and
customization when automating these activities for your
workload, use historical data to determine when training and
customization might be needed for your workload.

### Implementation steps

- Select your IaC tool stack.

Evaluate AWS CDK, AWS CloudFormation, or Terraform
- Consider team skills and project needs
- Assess learning curve and maintainability

- Define your infrastructure resources.

Include each component, such as Amazon Bedrock, Amazon API Gateway, AWS Lambda, and AWS Data Pipelines
- Create reproducible, version-controlled stacks
- Use modular design for reusability

- Version control your IaC templates.

Use a code repository Git tool
- Implement branching strategy aligned with environments

- Implement a CI/CD pipeline.

Consider AWS CodePipeline or Jenkins for orchestration
- Configure initiation events for code changes
- Set up automated testing for IaC templates
- Enable automatic deployment of changes
- Implement approval gates for production deployments

- Manage multiple environments.

Use the same templates with different parameters for
development, test, and production
- Implement environment-specific security controls

- Establish governance and compliance.

Use AWS Config for tracking resource configurations and
automate remediations
- Implement Service Catalog for standardized
provisioning
- Set up automated compliance checks and reporting

- Regularly audit your IaC templates.

Focus on security best practices
- Conduct periodic third-party security assessments

## Resources

**Related best practices:**

- OPS05-BP10
- OPS06-BP03
- OPS06-BP04
- OPS05-BP08
- OPS05-BP01

**Related documents:**

- [Operationalize
generative AI applications on AWS](https://aws.amazon.com/blogs/gametech/operationalize-generative-ai-applications-on-aws-part-ii-architecture-deep-dive/)
- [AWS CloudFormation Amazon Bedrock resources](https://docs.aws.amazon.com/bedrock/latest/userguide/creating-resources-with-cloudformation.html)
- [AWS re:Invent 2024 - Generative AI in action: From prototype to
production (AIM276)](https://www.youtube.com/watch?v=aFQFiVOh3P0)
- [SageMaker AI
HyperPod Recipes Official Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-recipes.html)
- [SageMaker AI
HyperPod Recipe Repository Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-recipe-repository.html)

**Related examples:**

- [Walkthrough:
Building a pipeline for test and production stacks](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/continuous-delivery-codepipeline-basic-walkthrough.html)
- [AWS CDK Examples](https://github.com/aws-samples/aws-cdk-examples)
- [AWS CDK Developer Guide](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- [Terraform
AWS Provider Examples](https://github.com/terraform-providers/terraform-provider-aws/tree/main/examples)
- [Accelerate
Foundation Model Training and Fine-tuning with New Amazon SageMaker AI HyperPod Recipes](https://aws.amazon.com/blogs/aws/accelerate-foundation-model-training-and-fine-tuning-with-new-amazon-sagemaker-hyperpod-recipes/)
- [Amazon SageMaker AI model endpoint creation with CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-model.html#aws-resource-sagemaker-model--examples)

**Related tools:**

- [AWS CloudFormation](https://aws.amazon.com/cloudformation/)
- [AWS CDK](https://aws.amazon.com/cdk/)
- [AWS CodePipeline](https://aws.amazon.com/codepipeline/)
- [AWS Config](https://aws.amazon.com/config/)
- [Service Catalog](https://aws.amazon.com/servicecatalog/)
