---
id: "REL08-BP01"
title: "Use runbooks for standard activities such as deployment"
pillar: "Reliability"
risk_level: "HIGH"
capability: "How do you implement change?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_tracking_change_management_planned_changemgmt.html"
description: "Runbooks are the predefined procedures to achieve specific outcomes. Use runbooks to perform standard activities, whether done manually or automatically. Examples include deploying a workload, patching a workload, or making DNS modifications."
area: ["Change management", "Implement change"]
---

# REL08-BP01 Use runbooks for standard activities such as deployment

Runbooks are the predefined procedures to achieve specific outcomes.
Use runbooks to perform standard activities, whether done manually
or automatically. Examples include deploying a workload, patching a
workload, or making DNS modifications.

For example, put processes in place
to [ensure
rollback safety during deployments](https://aws.amazon.com/builders-library/ensuring-rollback-safety-during-deployments). Ensuring that you can
roll back a deployment without any disruption for your customers is
critical in making a service reliable.

For runbook procedures, start with a valid effective manual process,
implement it in code, and invoke it to automatically run where
appropriate.

Even for sophisticated workloads that are highly automated, runbooks
are still useful
for [running
game days](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/test-reliability.html#GameDays) or meeting rigorous reporting and auditing
requirements.

Note that playbooks are used in response to specific incidents, and
runbooks are used to achieve specific outcomes. Often, runbooks are
for routine activities, while playbooks are used for responding to
non-routine events.

**Common anti-patterns:**

- Performing unplanned changes to configuration in production.
- Skipping steps in your plan to deploy faster, resulting in a
failed deployment.
- Making changes without testing the reversal of the change.

**Benefits of establishing this best
practice:** Effective change planning increases your
ability to successfully run the change because you are aware of
all the systems impacted. Validating your change in test
environments increases your confidence.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

- Provide consistent and prompt responses to well-understood events
by documenting procedures in runbooks.
- Use the principle of infrastructure as code to define your
infrastructure. By using AWS CloudFormation (or a trusted third
party) to define your infrastructure, you can use version control
software to version and track changes.

Use AWS CloudFormation (or a trusted third-party provider) to define your infrastructure.

[What is AWS CloudFormation?](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)

- Create templates that are singular and decoupled, using good software design
principles.

Determine the permissions, templates, and responsible parties for
implementation.

[Controlling access with AWS Identity and Access Management](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-template.html)

- Use a hosted source code management system based on a popular technology such as Git to store your source code and infrastructure as code (IaC) configuration.

## Resources

**Related documents:**

- [APN
Partner: partners that can help you create automated
deployment solutions](https://aws.amazon.com/partners/find/results/?keyword=devops)
- [AWS Marketplace: products that can be used to automate your
deployments](https://aws.amazon.com/marketplace/search/results?searchTerms=DevOps)
- [What
is AWS CloudFormation?](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)

**Related examples:**

- [Automating
operations with Playbooks and Runbooks](https://wellarchitectedlabs.com/operational-excellence/200_labs/200_automating_operations_with_playbooks_and_runbooks/)
