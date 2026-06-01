---
id: "OPS02-BP02"
title: "Processes and procedures have identified owners"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How do you structure your organization to support your business outcomes?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ops_model_def_proc_owners.html"
description: "Understand who has ownership of the definition of individual processes and procedures, why those specific process and procedures are used, and why that ownership exists. Understanding the reasons that specific processes and procedures are used aids in identification of improvement opportunities."
area: ["Organization", "Operating model", "Relationships and ownership"]
relatedIds: ["OPS02-BP01", "OPS02-BP04", "OPS11-BP04"]
---

# OPS02-BP02 Processes and procedures have identified owners

Understand who has ownership of the definition of individual
processes and procedures, why those specific process and procedures
are used, and why that ownership exists. Understanding the reasons
that specific processes and procedures are used aids in
identification of improvement opportunities.

**Desired outcome:** Your
organization has a well defined and maintained set of process and
procedures for operational tasks. The process and procedures are
stored in a central location and available to your team members.
Process and procedures are updated frequently, by clearly assigned
ownership. Where possible, scripts, templates, and automation
documents are implemented as code.

**Common anti-patterns:**

- Processes are not documented. Fragmented scripts may exist on
isolated operator workstations.
- Knowledge of how to use scripts is held by a few individuals or
informally as team knowledge.
- A legacy process is due for an update, but ownership of the
update is unclear, and the original author is no longer part of
the organization.
- Processes and scripts are not discoverable, so they are not
readily available when required (for example, in response to an
incident).

**Benefits of establishing this best
practice:**

- Processes and procedures boost your efforts to operate your
workloads.
- New team members become effective more quickly.
- Reduced time to mitigate incidents.
- Different team members (and teams) can use the same processes
and procedures in a consistent manner.
- Teams can scale their processes with repeatable processes.
- Standardized processes and procedures help mitigate the impact
of transferring workload responsibilities between teams.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

- Processes and procedures have identified owners who are
responsible for their definition.

Identify the operations activities conducted in support of
your workloads. Document these activities in a
discoverable location.
- Uniquely identify the individual or team responsible for
the specification of an activity. They are responsible to
verify that it can be successfully performed by an
adequately skilled team member with the correct
permissions, access, and tools. If there are issues with
performing that activity, the team members performing it
are responsible for providing the detailed feedback
necessary for the activity to be improved.
- Capture ownership in the metadata of the activity artifact
through services like AWS Systems Manager, through
documents, and AWS Lambda. Capture resource ownership
using tags or resource groups, specifying ownership and
contact information. Use AWS Organizations to create
tagging polices and capture ownership and contact
information.

- Over time, these procedures should be evolved to be runnable
as code, reducing the need for human intervention.

For example, consider AWS Lambda functions, CloudFormation
templates, or AWS Systems Manager automation docs.
- Perform version control in appropriate repositories.
- Include suitable resource tagging so owners and
documentation can readily be identified.

**Customer example**

AnyCompany Retail defines ownership as the team or individual that
owns processes for an application or groups of applications (that
share common architetural practices and technologies). Initially,
the process and procedures are documented as step-by-step guides
in the document management system, discoverable using tags on the
AWS account that hosts the application and on specific groups of
resources within the account. They leverage AWS Organizations to
manage their AWS accounts. Over time, these processes are
converted to code, and resources are defined using infrastructure
as code (such as CloudFormation or AWS Cloud Development Kit (AWS CDK)
templates). The operational processes become automation documents
in AWS Systems Manager or AWS Lambda functions, which can be
initiated as scheduled tasks, in response to events such as AWS
CloudWatch alarms or AWS EventBridge events, or started by
requests within an IT service management (ITSM) platform. All
process have tags to identify ownership. Documentation for the
automation and process is maintained within the wiki pages
generated by the code repository for the process.

### Implementation steps

- Document the existing processes and procedures.

Review and keep them up-to-date.
- Identify an owner for each process or procedure.
- Place them under version control.
- Where possible, share processes and procedures across
workloads and environments that share architectural
designs.

- Establish mechanisms for feedback and improvement.

Define policies for how frequently processes should be
reviewed.
- Define processes for reviewers and approvers.
- Implement issues or a ticketing queue for feedback to be
provided and tracked.
- Whereever possible, processes and procedures should have
pre-approval and risk classification from a change
approval board (CAB).

- Verify that processes and procedures are accessible and
discoverable by those who need to run them.

Use tags to indicate where the process and procedures
can be accessed for the workload.
- Use meaningful error and event messaging to indicate the
appropriate processes or procedures to address an issue.
- Use wikis and document management, and make processes
and procedures searchable consistently accross the
organization.

- Use [Amazon Q Business](https://aws.amazon.com/q/business/), a conversational assistant that uses generative AI to enhance workforce productivity, answer questions, and complete tasks based on information in your enterprise systems.

Connect Amazon Q Business to your company's data source. Amazon Q Business offers prebuilt connectors to over 40 supported data sources, including Amazon S3, Microsoft SharePoint, Salesforce, and Atlassian Confluence. For more information, see [Amazon Q connectors](https://aws.amazon.com/q/business/connectors/).

- Automate when appropriate.

Automations should be developed when services and
technologies provide an API.
- Educate adequately on processes. Develop the user
stories and requirements to automate those processes.
- Measure the use of your processes and procedures
successfully, and create issues or tickets to support iterative
improvement.

**Level of effort for the implementation
plan:** Medium

## Resources

**Related best practices:**

- [OPS02-BP01
Resources have identified owners](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ops_model_def_resource_owners.html)
- [OPS02-BP04
Mechanisms exist to manage responsibilities and
ownership](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ops_model_def_responsibilities_ownership.html)
- [OPS11-BP04
Perform knowledge management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_knowledge_management.html)

**Related documents:**

- [AWS Whitepaper - Introduction to DevOps on AWS](https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/automation.html)
- [AWS Whitepaper - Best Practices for Tagging AWS Resources](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html)
- [AWS Whitepaper - Organizing Your AWS Environment Using Multiple
Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/organizing-your-aws-environment.html)
- [AWS Cloud Operations and Migrations Blog - Using Amazon Q Business to streamline your operations](https://aws.amazon.com/blogs/mt/streamline-operations-using-amazon-q-for-business/)
- [AWS Cloud Operations & Migrations Blog - Build a Cloud
Automation Practice for Operational Excellence: Best Practices
from AWS Managed Services](https://aws.amazon.com/blogs/mt/build-a-cloud-automation-practice-for-operational-excellence-best-practices-from-aws-managed-services/)
- [AWS Cloud Operations & Migrations Blog - Implementing
automated and centralized tagging controls with AWS Config and
AWS Organizations](https://aws.amazon.com/blogs/mt/implementing-automated-and-centralized-tagging-controls-with-aws-config-and-aws-organizations/)
- [AWS Security Blog - Extend your pre-commit hooks with AWS CloudFormation Guard](https://aws.amazon.com/blogs/security/extend-your-pre-commit-hooks-with-aws-cloudformation-guard/)
- [AWS DevOps Blog - Integrating AWS CloudFormation Guard into CI/CD
pipelines](https://aws.amazon.com/blogs/devops/integrating-aws-cloudformation-guard/)

**Related workshops:**

- [AWS Well-Architected Operational Excellence Workshop](https://catalog.workshops.aws/well-architected-operational-excellence/en-US/)
- [AWS Workshop - Tagging](https://catalog.workshops.aws/tagging/)

**Related videos:**

- [How
to automate IT Operations on AWS](https://www.youtube.com/watch?v=GuWj_mlyTug)
- [AWS re:Invent 2020 - Automate anything with AWS Systems Manager](https://www.youtube.com/watch?v=AaI2xkW85yE)
- [AWS re:Inforce 2022 - Automating patch management and compliance
using AWS (NIS306)](https://www.youtube.com/watch?v=gL3baXQJvc0)
- [Supports You - Diving Deep into AWS Systems Manager](https://www.youtube.com/watch?v=xHNLNTa2xGU)

**Related services:**

- [AWS Systems Manager - Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)
- [AWS Service Management Connector](https://aws.amazon.com/service-management-connector/)
