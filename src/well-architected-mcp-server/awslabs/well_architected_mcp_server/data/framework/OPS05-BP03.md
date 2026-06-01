---
id: "OPS05-BP03"
title: "Use configuration management systems"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How do you reduce defects, ease remediation, and improve flow into production?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_dev_integ_conf_mgmt_sys.html"
---

# OPS05-BP03 Use configuration management systems

Use configuration management systems to make and track configuration changes. These systems reduce errors caused by manual processes and reduce the level of effort to deploy changes.

Static configuration management sets values when initializing a resource that are expected to remain consistent throughout the resource’s lifetime. Dynamic configuration management sets values at initialization that can or are expected to change during the lifetime of a resource. For example, you could set a feature toggle to activate functionality in your code through a configuration change, or change the level of log detail during an incident.

Configurations should be deployed in a known and consistent state. You should use automated inspection to continually monitor resource configurations across environments and regions. These controls should be defined as code and management automated to ensure rules are consistently appplied across environments. Changes to configurations should be updated through agreed change control procedures and applied consistently, honoring version control. Application configuration should be managed independently of application and infrastructure code. This allows for consistent deployment across multiple environments. Configuration changes do not result in rebuilding or redeploying the application.

**Desired outcome:** You configure, validate, and deploy as part of your continuous integration, continuous delivery (CI/CD) pipeline. You monitor to validate configurations are correct. This minimizes any impact to end users and customers.

**Common anti-patterns:**

- You manually update the web server configuration across your
fleet and a number of servers become unresponsive due to update
errors.
- You manually update your application server fleet over the
course of many hours. The inconsistency in configuration during
the change causes unexpected behaviors.
- Someone has updated your security groups and your web servers
are no longer accessible. Without knowledge of what was changed
you spend significant time investigating the issue extending
your time to recovery.
- You push a pre-production configuration into production through CI/CD without validation. You expose users and customers to incorrect data and services.

**Benefits of establishing this best
practice:** Adopting configuration management systems reduces the level of effort to make and track changes, and the frequency of errors caused by manual procedures. Configuration management systems provide assurances with regards to governance, compliance, and regulatory requirements.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Configuration management systems are used to track and implement changes to application and environment configurations. Configuration management systems are also used to reduce errors caused by manual processes, make configuration changes repeatable and auditable, and reduce the level of effort.

On AWS, you can use
[AWS Config](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html) to continually monitor your AWS resource
configurations
[across
accounts and Regions](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html). It helps you to track their
configuration history, understand how a configuration change would
affect other resources, and audit them against expected or desired
configurations using
[AWS Config Rules](https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config.html) and
[AWS Config Conformance Packs](https://docs.aws.amazon.com/config/latest/developerguide/conformance-packs.html).

For dynamic configurations in your applications running on
Amazon EC2 instances, AWS Lambda, containers, mobile applications, or IoT devices, you can use
[AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html) to configure, validate, deploy, and monitor them across your environments.

### Implementation steps

- Identify configuration owners.

Make configurations owners aware of any compliance, governance, or regulatory needs.

- Identify configuration items and deliverables.

Configuration items are all application and environmental configurations affected by a deployment within your CI/CD pipeline.
- Deliverables include success criteria, validation, and what to monitor.

- Select tools for configuration management based on your business requirements and delivery pipeline.
- Consider weighted deployments such as canary deployments for significant configuration changes to minimize the impact of incorrect configurations.
- Integrate your configuration management into your CI/CD pipeline.
- Validate all changes pushed.

## Resources

**Related best practices:**

- [OPS06-BP01 Plan for unsuccessful changes](./ops_mit_deploy_risks_plan_for_unsucessful_changes.html)
- [OPS06-BP02 Test deployments](./ops_mit_deploy_risks_test_val_chg.html)
- [OPS06-BP03 Employ safe deployment strategies](./ops_mit_deploy_risks_deploy_mgmt_sys.html)
- [OPS06-BP04 Automate testing and rollback](./ops_mit_deploy_risks_auto_testing_and_rollback.html)

**Related documents:**

- [AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)
- [AWS Landing Zone Accelerator](https://aws.amazon.com/solutions/implementations/landing-zone-accelerator-on-aws/)
- [AWS Config](https://aws.amazon.com/config/)
- [What is AWS Config?](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)
- [AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)
- [What is AWS CloudFormation?](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)
- [AWS Developer Tools](https://aws.amazon.com/products/developer-tools/)
- [AWS CodeBuild](https://aws.amazon.com/codebuild/)
- [AWS CodePipeline](https://aws.amazon.com/codepipeline/)
- [AWS CodeDeploy](https://aws.amazon.com/codedeploy/)

**Related videos:**

- [AWS re:Invent 2022 - Proactive governance and compliance for AWS workloads](https://youtu.be/PpUnH9Y52X0?si=82wff87KHXcc6nbT)
- [AWS re:Invent 2020: Achieve compliance as code using AWS Config](https://youtu.be/m8vTwvbzOfw?si=my4DP0FLq1zwKjho)
- [Manage and Deploy Application Configurations with AWS AppConfig](https://youtu.be/ztIxMY3IIu0?si=ovYGsxWOBysyQrg0)
