---
id: "COST02-BP05"
title: "Implement cost controls"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you govern usage?"
risk_level: "Medium"
---

# COST02-BP05 Implement cost controls

## Implementation Guidance
A common first step in implementing cost controls is to set up notifications when cost or usage events occur outside of policies. You can act quickly and verify if corrective action is required without restricting or negatively impacting workloads or new activity. After you know the workload and environment limits, you can enforce governance. [AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/) allows you to set notifications and define monthly budgets for your AWS costs, usage, and commitment discounts (Savings Plans and Reserved Instances). You can create budgets at an aggregate cost level (for example, all costs), or at a more granular level where you include only specific dimensions such as linked accounts, services, tags, or Availability Zones.

 Once you set up your budget limits with AWS Budgets, use [AWS Cost Anomaly Detection](https://aws.amazon.com/https://aws.amazon.com/aws-cost-management/aws-cost-anomaly-detection/) to reduce your unexpected cost. AWS Cost Anomaly Detection is a cost management service that uses machine learning to continually monitor your cost and usage to detect unusual spends. It helps you identify anomalous spend and root causes, so you can quickly take action. First, create a cost monitor in AWS Cost Anomaly Detection, then choose your alerting preference by setting up a dollar threshold (such as an alert on anomalies with impact greater than \$11,000). Once you receive alerts, you can analyze the root cause behind the anomaly and impact on your costs. You can also monitor and perform your own anomaly analysis in AWS Cost Explorer.

 Enforce governance policies in AWS through [AWS Identity and Access Management](https://aws.amazon.com/iam/) and [AWS Organizations Service Control Policies (SCP)](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scp.html). IAM allows you to securely manage access to AWS services and resources. Using IAM, you can control who can create or manage AWS resources, the type of resources that can be created, and where they can be created. This minimizes the possibility of resources being created outside of the defined policy. Use the roles and groups created previously and assign [IAM policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html) to enforce the correct usage. SCP offers central control over the maximum available permissions for all accounts in your organization, keeping your accounts stay within your access control guidelines. SCPs are available only in an organization that has all features turned on, and you can configure the SCPs to either deny or allow actions for member accounts by default. For more details on implementing access management, see the [Well-Architected Security Pillar whitepaper](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html).

 Governance can also be implemented through management of [AWS service quotas](https://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html). By ensuring service quotas are set with minimum overhead and accurately maintained, you can minimize resource creation outside of your organization’s requirements. To achieve this, you must understand how quickly your requirements can change, understand projects in progress (both creation and decommission of resources), and factor in how fast quota changes can be implemented. [Service quotas](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html) can be used to increase your quotas when required.

## Implementation Steps
- ** Implement notifications on spend:** Using your defined organization policies, create [AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/) to notify you when spending is outside of your policies. Configure multiple cost budgets, one for each account, which notify you about overall account spending. Configure additional cost budgets within each account for smaller units within the account. These units vary depending on your account structure. Some common examples are AWS Regions, workloads (using tags), or AWS services. Configure an email distribution list as the recipient for notifications, and not an individual's email account. You can configure an actual budget for when an amount is exceeded, or use a forecasted budget for notifying on forecasted usage. You can also preconfigure AWS Budget Actions that can enforce specific IAM or SCP policies, or stop target Amazon EC2 or Amazon RDS instances. Budget Actions can be started automatically or require workflow approval.
- **Implement notifications on anomalous spend:** Use [AWS Cost Anomaly Detection](https://aws.amazon.com/aws-cost-management/aws-cost-anomaly-detection/) to reduce your surprise costs in your organization and analyze root cause of potential anomalous spend. Once you create cost monitor to identify unusual spend at your specified granularity and configure notifications in AWS Cost Anomaly Detection, it sends you alert when unusual spend is detected. This will allow you to analyze root cause behind the anomaly and understand the impact on your cost. Use AWS Cost Categories while configuring AWS Cost Anomaly Detection to identify which project team or business unit team can analyze the root cause of the unexpected cost and take timely necessary actions.
- ** Implement controls on usage: **Using your defined organization policies, implement IAM policies and roles to specify which actions users can perform and which actions they cannot. Multiple organizational policies may be included in an AWS policy. In the same way that you defined policies, start broadly and then apply more granular controls at each step. Service limits are also an effective control on usage. Implement the correct service limits on all your accounts.

## Resources
### Related Documents
- [AWS managed policies for job functions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_job-functions.html)
- [AWS multiple account billing strategy](https://aws.amazon.com/answers/account-management/aws-multi-account-billing-strategy/)
- [Control access to AWS Regions using IAM policies](https://aws.amazon.com/blogs/security/easier-way-to-control-access-to-aws-regions-using-iam-policies/)
- [AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/)
- [AWS Cost Anomaly Detection](https://aws.amazon.com/aws-cost-management/aws-cost-anomaly-detection/)
- [Control Your AWS Costs](https://aws.amazon.com/getting-started/hands-on/control-your-costs-free-tier-budgets/)
### Related Videos
- [How can I use AWS Budgets to track my spending and usage](https://www.youtube.com/watch?v=Ris23gKc7s0)
### Related Examples
- [Example IAM access management policies ](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_examples.html)
- [Example service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_examples.html)
- [AWS Budgets Actions](https://aws.amazon.com/blogs/aws-cloud-financial-management/get-started-with-aws-budgets-actions/)
- [Create IAM Policy to control access to Amazon EC2 resources using Tags](https://aws.amazon.com/premiumsupport/knowledge-center/iam-ec2-resource-tags/)
- [Restrict the access of IAM Identity to specific Amazon EC2 resources](https://aws.amazon.com/premiumsupport/knowledge-center/restrict-ec2-iam/)
- [Slack integrations for Cost Anomaly Detection using Amazon Q Developer in chat applications](https://aws.amazon.com/aws-cost-management/resources/slack-integrations-for-aws-cost-anomaly-detection-using-aws-chatbot/)
