---
id: "OPS05-BP08"
title: "Use multiple environments"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How do you reduce defects, ease remediation, and improve flow into production?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_dev_integ_multi_env.html"
description: "Use multiple environments to experiment, develop, and test your workload. Use increasing levels of controls as environments approach production to gain confidence your workload operates as intended when deployed."
area: ["Prepare", "Design for operations"]
---

# OPS05-BP08 Use multiple environments

Use multiple environments to experiment, develop, and test your
workload. Use increasing levels of controls as environments approach
production to gain confidence your workload operates as intended
when deployed.

**Desired outcome:** You have multiple environments that reflect your compliance and governance needs. You test and promote code through environments on your path to production.

- Your organization does this through the establishment of a landing zone, which provides governance, controls, account automations, networking, security, and operational observability. Manage these landing zone capabilities by using multiple environments. A common example is a sandbox organization for developing and testing changes to an [AWS Control Tower](https://aws.amazon.com/controltower/)-based landing zone, which includes [AWS IAM Identity Center](https://aws.amazon.com/iam/identity-center/) and policies such as [service control policies (SCPs)](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html). All of these elements can significantly impact the access to and operation of AWS accounts within the landing zone.
- In addition to these services, your teams extend the landing zones capabilites with solutions published by AWS and AWS partners or as custom solutions developed within your organization. Examples of solutions published by AWS include [Customizations for AWS Control Tower (CfCT)](https://aws.amazon.com/solutions/implementations/customizations-for-aws-control-tower/) and [AWS Control Tower Account Factory for Terraform (AFT)](https://docs.aws.amazon.com/controltower/latest/userguide/aft-overview.html).
- Your organization applies the same principles of testing, promoting code, and policy changes for the landing zone through environments on your path to production. This strategy provides a stable and secure landing zone environment for your application and workload teams.

**Common anti-patterns:**

- You are performing development in a shared development
environment and another developer overwrites your code changes.
- The restrictive security controls on your shared development
environment are preventing you from experimenting with new
services and features.
- You perform load testing on your production systems and cause an
outage for your users.
- A critical error resulting in data loss has occurred in
production. In your production environment, you attempt to
recreate the conditions that lead to the data loss so that you
can identify how it happened and prevent it from happening
again. To prevent further data loss during testing, you are
forced to make the application unavailable to your users.
- You are operating a multi-tenant service and are unable to
support a customer request for a dedicated environment.
- You may not always test, but when you do, you test in your production environment.
- You believe that the simplicity of a single environment
overrides the scope of impact of changes within the environment.
- You upgrade a key landing zone capability, but the change impairs your team's ability to vend accounts for either new projects or your existing workloads.
- You apply new controls to your AWS accounts, but the change impacts your workload team's ability to deploy changes within their AWS accounts.

**Benefits of establishing this best
practice:** When you deploy multiple environments, you can support multiple simultaneous development, testing, and production environments without creating conflicts between developers or user communities. For complex capabilities such as landing zones, it significantly reduces the risk of changes, simplifies the improvement process, and reduces the risk of critical updates to the environment. Organizations that use landing zones naturally benefit from multi-accounts in their AWS environment, with account structure, governance, network, and security configurations. Over time, as your organization grows, the landing zone can evolve to secure and organize your workloads and resources.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Use multiple environments and provide developers sandbox environments with minimized controls to aid in experimentation. Provide individual development environments to help work in parallel, increasing development agility. Implement more rigorous controls in the environments approaching production to allow developers to innovate. Use infrastructure as code and configuration management systems to deploy environments that are configured consistent with the controls present in production to ensure systems operate as expected when deployed. When environments are not in use, turn them off to avoid costs associated with idle resources (for example, development systems on evenings and weekends). Deploy production equivalent environments when load testing to improve valid results.

Teams such as platform engineering, networking, and security operations often manage capabilies at the organization level with distinct requirements. A separation of accounts alone is insufficient to provide and maintain separate environments for experimentation, development, and testing. In such cases, create separate instances of AWS Organizations.

## Resources

**Related documents:**

- [Instance Scheduler on AWS](https://aws.amazon.com/solutions/implementations/instance-scheduler-on-aws/)
- [What
is AWS CloudFormation?](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)
- [Organizing Your AWS Environment Using Multiple Accounts - Multiple organizations - Test changes to your overall AWS environment](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/multiple-organizations.html#test-changes-to-your-overall-aws-environment)
- [AWS Control Tower Guide](https://catalog.workshops.aws/control-tower)
