---
id: "SEC01-BP06"
title: "Automate deployment of standard security controls"
framework: "WAF"
domain: "Security"
capability: "How do you securely operate your workload?"
risk_level: "Medium"
---

# SEC01-BP06 Automate deployment of standard security controls

## Desired Outcome
IaC templates capture standardized security controls and commit them to a version control system.  CI/CD pipelines are in places that detect changes and automate testing and deploying your AWS environments.  Guardrails are in place to detect and alert on misconfigurations in templates before proceeding to deployment.  Workloads are deployed into environments where standard controls are in place.  Teams have access to deploy approved service configurations through a self-service mechanism.  Secure backup and recovery strategies are in place for control configurations, scripts, and related data.

## Anti-Patterns
- Making changes to your standard security controls manually, through a web console or command-line interface.
- Relying on individual workload teams to manually implement the controls a central team defines.
- Relying on a central security team to deploy workload-level controls at the request of a workload team.
- Allowing the same individuals or teams to develop, test, and deploy security control automation scripts without proper separation of duties or checks and balances.

## Implementation Guidance
 When following the practices described in [SEC01-BP01 Separate workloads using accounts](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_multi_accounts.html), you will end up with multiple AWS accounts for different environments that you manage using AWS Organizations.  While each of these environments and workloads may need distinct security controls, you can standardize some security controls across your organization.  Examples include integrating centralized identity providers, defining networks and firewalls, and configuring standard locations for storing and analyzing logs.  In the same way you can use *infrastructure as code* (IaC) to apply the same rigor of application code development to infrastructure provisioning, you can use IaC to define and deploy your standard security controls as well.

 Wherever possible, define your security controls in a declarative way, such as in [AWS CloudFormation](https://aws.amazon.com/cloudformation/), and store them in a source control system.  Use DevOps practices to automate the deploying your controls for more predictable releases, automated testing using tools like [AWS CloudFormation Guard](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html), and detecting drift between your deployed controls and your desired configuration.  You can use services such as [AWS CodePipeline](https://aws.amazon.com/codepipeline/), [AWS CodeBuild](https://aws.amazon.com/codebuild/), and [AWS CodeDeploy](https://aws.amazon.com/codedeploy/) to construct a CI/CD pipeline. Consider the guidance in [Organizing Your AWS Environment Using Multiple Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/deployments-ou.html) to configure these services in their own accounts that are separate from other deployment pipelines.

 You can also define templates to standardize defining and deploying AWS accounts, services, and configurations.  This technique allows a central security team to manage these definitions and provide them to workload teams through a self-service approach.  One way to achieve this is by using [Service Catalog](https://aws.amazon.com/servicecatalog/), where you can publish templates as *products* that workload teams can incorporate into their own pipeline deployments.  If you are using [AWS Control Tower](https://aws.amazon.com/controltower/), some templates and controls are available as a starting point.  Control Tower also provides the [Account Factory](https://docs.aws.amazon.com/controltower/latest/userguide/af-customization-page.html) capability, allowing workload teams to create new AWS accounts using the standards you define.  This capability helps remove dependencies on a central team to approve and create new accounts when they are identified as needed by your workload teams.  You may need these accounts to isolate different workload components based on reasons such as the function they serve, the sensitivity of data being processed, or their behavior.

## Implementation Steps
1.  Determine how you will store and maintain your templates in a version control system.

1.  Create CI/CD pipelines to test and deploy your templates.  Define tests to check for misconfigurations and that templates adhere to your company standards.

1.  Build a catalog of standardized templates for workload teams to deploy AWS accounts and services according to your requirements.

1.  Implement secure backup and recovery strategies for your control configurations, scripts, and related data.

## Resources
### Related Best Practices
- [OPS05-BP01 Use version control](https://docs.aws.amazon.com/wellarchitected/latest/framework/ops_dev_integ_version_control.html)
- [OPS05-BP04 Use build and deployment management systems](https://docs.aws.amazon.com/wellarchitected/latest/framework/ops_dev_integ_build_mgmt_sys.html)
- [REL08-BP05 Deploy changes with automation](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_tracking_change_management_automated_changemgmt.html)
- [SUS06-BP01 Adopt methods that can rapidly introduce sustainability improvements](https://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_dev_a2.html)
### Related Documents
- [Organizing Your AWS Environment Using Multiple Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/deployments-ou.html)
### Related Examples
- [Automate account creation, and resource provisioning using Service Catalog, AWS Organizations, and AWS Lambda](https://aws.amazon.com/blogs/mt/automate-account-creation-and-resource-provisioning-using-aws-service-catalog-aws-organizations-and-aws-lambda/)
- [Strengthen the DevOps pipeline and protect data with AWS Secrets Manager, AWS KMS, and AWS Certificate Manager](https://aws.amazon.com/blogs/security/strengthen-the-devops-pipeline-and-protect-data-with-aws-secrets-manager-aws-kms-and-aws-certificate-manager/)
### Related Tools
- [AWS CloudFormation Guard](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html)
- [Landing Zone Accelerator on AWS](https://github.com/awslabs/landing-zone-accelerator-on-aws)
