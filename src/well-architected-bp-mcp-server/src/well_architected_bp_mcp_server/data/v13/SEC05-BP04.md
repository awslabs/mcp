---
id: "SEC05-BP04"
title: "Automate network protection"
framework: "WAF"
domain: "Security"
capability: "How do you protect your network resources?"
risk_level: "Medium"
---

# SEC05-BP04 Automate network protection

## Desired Outcome
You define network protections with templates and commit them into a version control system.  Automated pipelines are initiated when new changes are made that orchestrates their testing and deployment.  Policy checks and other static tests are in place to validate changes before deployment.  You deploy changes into a staging environment to validate the controls are operating as expected.  Deployment into your production environments is also performed automatically once controls are approved.

## Anti-Patterns
- Relying on individual workload teams to each define their complete network stack, protections, and automations.  Not publishing standard aspects of the network stack and protections centrally for workload teams to consume.
- Relying on a central network team to define all aspects of the network, protections, and automations.  Not delegating workload-specific aspects of the network stack and protections to that workload's team.
- Striking the right balance between centralization and delegation between a network team and workload teams, but not applying consistent testing and deployment standards across your IaC templates and CI/CD pipelines.  Not capturing required configurations in tooling that checks your templates for adherence.

## Implementation Guidance
 A number of network protection controls described in [SEC05-BP02 Control traffic flows within your network layers](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_network_protection_layered.html) and [SEC05-BP03 Implement inspection-based protection](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_network_protection_inspection.html) come with managed rules systems that can update automatically based on the latest threat intelligence.  Examples of protecting your web endpoints include [AWS WAF managed rules](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups.html) and [AWS Shield Advanced automatic application layer DDoS mitigation](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-automatic-app-layer-response.html). Use [AWS Network Firewall managed rule groups](https://docs.aws.amazon.com/network-firewall/latest/developerguide/nwfw-managed-rule-groups.html) to stay up to date with low-reputation domain lists and threat signatures as well.

 Beyond managed rules, we recommend you use DevOps practices to automate deploying your network resources, protections, and the rules you specify.  You can capture these definitions in [AWS CloudFormation](https://aws.amazon.com/cloudformation/) or another *infrastructure as code* (IaC) tool of your choice, commit them to a version control system, and deploy them using CI/CD pipelines.  Use this approach to gain the traditional benefits of DevOps for managing your network controls, such as more predictable releases, automated testing using tools like [AWS CloudFormation Guard](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html), and detecting drift between your deployed environment and your desired configuration.

 Based on the decisions you made as part of [SEC05-BP01 Create network layers](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_network_protection_create_layers.html), you may have a central management approach to creating VPCs that are dedicated for ingress, egress, and inspection flows.  As described in the [AWS Security Reference Architecture (AWS SRA)](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture), you can define these VPCs in a dedicated [Network infrastructure account](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/network.html).  You can use similar techniques to centrally define the VPCs used by your workloads in other accounts, their security groups, AWS Network Firewall deployments, Route 53 Resolver rules and DNS Firewall configurations, and other network resources.  You can share these resources with your other accounts with the [AWS Resource Access Manager](https://docs.aws.amazon.com/ram/latest/userguide/what-is.html).  With this approach, you can simplify the automated testing and deployment of your network controls to the Network account, with only one destination to manage.  You can do this in a hybrid model, where you deploy and share certain controls centrally and delegate other controls to the individual workload teams and their respective accounts.

## Implementation Steps
1.  Establish ownership over which aspects of the network and protections are defined centrally, and which your workload teams can maintain.

1.  Create environments to test and deploy changes to your network and its protections.  For example, use a Network Testing account and a Network Production account.

1.  Determine how you will store and maintain your templates in a version control system.  Store central templates in a repository that is distinct from workload repositories, while workload templates can be stored in repositories specific to that workload.

1.  Create CI/CD pipelines to test and deploy templates.  Define tests to check for misconfigurations and that templates adhere to your company standards.

## Resources
### Related Best Practices
- [SEC01-BP06 Automate deployment of standard security controls](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_automate_security_controls)
### Related Documents
- [AWS Security Reference Architecture - Network account](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/network.html)
### Related Examples
- [AWS Deployment Pipeline Reference Architecture](https://pipelines.devops.aws.dev/)
- [NetDevSecOps to modernize AWS networking deployments](https://aws.amazon.com/blogs/networking-and-content-delivery/netdevsecops-to-modernize-aws-networking-deployments/)
- [Integrating AWS CloudFormation security tests with AWS Security Hub and AWS CodeBuild reports](https://aws.amazon.com/blogs/security/integrating-aws-cloudformation-security-tests-with-aws-security-hub-and-aws-codebuild-reports/)
### Related Tools
- [AWS CloudFormation](https://aws.amazon.com/cloudformation/)
- [AWS CloudFormation Guard](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html)
- [cfn\$1nag](https://github.com/stelligent/cfn_nag)
