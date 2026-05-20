---
id: "OPS05-BP03"
title: "Use configuration management systems"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you reduce defects, ease remediation, and improve flow into production?"
risk_level: "Medium"
---

# OPS05-BP03 Use configuration management systems

## Desired Outcome
You configure, validate, and deploy as part of your continuous integration, continuous delivery (CI/CD) pipeline. You monitor to validate configurations are correct. This minimizes any impact to end users and customers.

## Anti-Patterns
- You manually update the web server configuration across your fleet and a number of servers become unresponsive due to update errors.
- You manually update your application server fleet over the course of many hours. The inconsistency in configuration during the change causes unexpected behaviors.
- Someone has updated your security groups and your web servers are no longer accessible. Without knowledge of what was changed you spend significant time investigating the issue extending your time to recovery.
- You push a pre-production configuration into production through CI/CD without validation. You expose users and customers to incorrect data and services.

## Implementation Guidance
 Configuration management systems are used to track and implement changes to application and environment configurations. Configuration management systems are also used to reduce errors caused by manual processes, make configuration changes repeatable and auditable, and reduce the level of effort.

 On AWS, you can use [AWS Config](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html) to continually monitor your AWS resource configurations [across accounts and Regions](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html). It helps you to track their configuration history, understand how a configuration change would affect other resources, and audit them against expected or desired configurations using [AWS Config Rules](https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config.html) and [AWS Config Conformance Packs](https://docs.aws.amazon.com/config/latest/developerguide/conformance-packs.html).

 For dynamic configurations in your applications running on Amazon EC2 instances, AWS Lambda, containers, mobile applications, or IoT devices, you can use [AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html) to configure, validate, deploy, and monitor them across your environments.

## Implementation Steps
1.  Identify configuration owners.

   1.  Make configurations owners aware of any compliance, governance, or regulatory needs.

1.  Identify configuration items and deliverables.

   1.  Configuration items are all application and environmental configurations affected by a deployment within your CI/CD pipeline.

   1.  Deliverables include success criteria, validation, and what to monitor.

1.  Select tools for configuration management based on your business requirements and delivery pipeline.

1.  Consider weighted deployments such as canary deployments for significant configuration changes to minimize the impact of incorrect configurations.

1.  Integrate your configuration management into your CI/CD pipeline.

1.  Validate all changes pushed.

## Resources
### Related Best Practices
- [OPS06-BP01 Plan for unsuccessful changes](ops_mit_deploy_risks_plan_for_unsucessful_changes.md)
- [OPS06-BP02 Test deployments](ops_mit_deploy_risks_test_val_chg.md)
- [OPS06-BP03 Employ safe deployment strategies](ops_mit_deploy_risks_deploy_mgmt_sys.md)
- [OPS06-BP04 Automate testing and rollback](ops_mit_deploy_risks_auto_testing_and_rollback.md)
### Related Documents
- [AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)
- [AWS Landing Zone Accelerator ](https://aws.amazon.com/solutions/implementations/landing-zone-accelerator-on-aws/)
- [AWS Config](https://aws.amazon.com/config/)
- [ What is AWS Config? ](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)
- [AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)
- [ What is AWS CloudFormation? ](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)
- [AWS Developer Tools](https://aws.amazon.com/products/developer-tools/)
- [AWS CodeBuild](https://aws.amazon.com/codebuild/)
- [AWS CodePipeline](https://aws.amazon.com/codepipeline/)
- [AWS CodeDeploy](https://aws.amazon.com/codedeploy/)
### Related Videos
- [AWS re:Invent 2022 - Proactive governance and compliance for AWS workloads ](https://youtu.be/PpUnH9Y52X0?si=82wff87KHXcc6nbT)
- [AWS re:Invent 2020: Achieve compliance as code using AWS Config](https://youtu.be/m8vTwvbzOfw?si=my4DP0FLq1zwKjho)
- [ Manage and Deploy Application Configurations with AWS AppConfig](https://youtu.be/ztIxMY3IIu0?si=ovYGsxWOBysyQrg0)
