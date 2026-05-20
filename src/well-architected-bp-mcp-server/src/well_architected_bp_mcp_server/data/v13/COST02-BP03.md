---
id: "COST02-BP03"
title: "Implement an account structure"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you govern usage?"
risk_level: "High"
---

# COST02-BP03 Implement an account structure

## Implementation Guidance
 AWS Organizations allows you to create multiple AWS accounts which can help you centrally govern your environment as you scale your workloads on AWS. You can model your organizational hierarchy by grouping AWS accounts in organizational unit (OU) structure and creating multiple AWS accounts under each OU. To create an account structure, you need to decide which of your AWS accounts will be the management account first. After that, you can create new AWS accounts or select existing accounts as member accounts based on your designed account structure by following [management account best practices](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices_mgmt-acct.html) and [member account best practices](https://docs.aws.amazon.com/organizations/latest/userguide/best-practices_member-acct.html).

 It is advised to always have at least one management account with one member account linked to it, regardless of your organization size or usage. All workload resources should reside only within member accounts and no resource should be created in management account. There is no one size fits all answer for how many AWS accounts you should have. Assess your current and future operational and cost models to ensure that the structure of your AWS accounts reflects your organization’s goals. Some companies create multiple AWS accounts for business reasons, for example:
- Administrative or fiscal and billing isolation is required between organization units, cost centers, or specific workloads.
- AWS service limits are set to be specific to particular workloads.
- There is a requirement for isolation and separation between workloads and resources.

 Within [AWS Organizations](https://aws.amazon.com/organizations/), [consolidated billing](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/consolidated-billing.html) creates the construct between one or more member accounts and the management account. Member accounts allow you to isolate and distinguish your cost and usage by groups. A common practice is to have separate member accounts for each organization unit (such as finance, marketing, and sales), or for each environment lifecycle (such as development, testing and production), or for each workload (workload a, b, and c), and then aggregate these linked accounts using consolidated billing.

 Consolidated billing allows you to consolidate payment for multiple member AWS accounts under a single management account, while still providing visibility for each linked account’s activity. As costs and usage are aggregated in the management account, this allows you to maximize your service volume discounts, and maximize the use of your commitment discounts (Savings Plans and Reserved Instances) to achieve the highest discounts.

 The following diagram shows how you can use AWS Organizations with organizational units (OU) to group multiple accounts, and place multiple AWS accounts under each OU. It is recommended to use OUs for various use cases and workloads which provides patterns for organizing accounts.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/aws-organizations-ou-grouping.png)

 [AWS Control Tower](https://aws.amazon.com/controltower/) can quickly set up and configure multiple AWS accounts, ensuring that governance is aligned with your organization’s requirements.

## Implementation Steps
- **Define separation requirements: **Requirements for separation are a combination of multiple factors, including security, reliability, and financial constructs. Work through each factor in order and specify whether the workload or workload environment should be separate from other workloads. Security promotes adhesion to access and data requirements. Reliability manages limits so that environments and workloads do not impact others. Review the security and reliability pillars of the Well-Architected Framework periodically and follow the provided best practices. Financial constructs create strict financial separation (different cost center, workload ownerships and accountability). Common examples of separation are production and test workloads being run in separate accounts, or using a separate account so that the invoice and billing data can be provided to the individual business units or departments in the organization or stakeholder who owns the account.
- **Define grouping requirements:** Requirements for grouping do not override the separation requirements, but are used to assist management. Group together similar environments or workloads that do not require separation. An example of this is grouping multiple test or development environments from one or more workloads together.
- **Define account structure: **Using these separations and groupings, specify an account for each group and maintain separation requirements. These accounts are your member or linked accounts. By grouping these member accounts under a single management or payer account, you combine usage, which allows for greater volume discounts across all accounts, which provides a single bill for all accounts. It's possible to separate billing data and provide each member account with an individual view of their billing data. If a member account must not have its usage or billing data visible to any other account, or if a separate bill from AWS is required, define multiple management or payer accounts. In this case, each member account has its own management or payer account. Resources should always be placed in member or linked accounts. The management or payer accounts should only be used for management.

## Resources
### Related Documents
- [Using Cost Allocation Tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html)
- [AWS managed policies for job functions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_job-functions.html)
- [AWS multiple account billing strategy](https://aws.amazon.com/answers/account-management/aws-multi-account-billing-strategy/)
- [Control access to AWS Regions using IAM policies](https://aws.amazon.com/blogs/security/easier-way-to-control-access-to-aws-regions-using-iam-policies/)
- [AWS Control Tower](https://aws.amazon.com/controltower/)
- [AWS Organizations](https://aws.amazon.com/organizations/)
- Best practices for [management accounts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices_mgmt-acct.html) and [member accounts](https://docs.aws.amazon.com/organizations/latest/userguide/best-practices_member-acct.html)
- [Organizing Your AWS Environment Using Multiple Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/organizing-your-aws-environment.html)
- [Turning on shared reserved instances and Savings Plans discounts](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ri-turn-on-process.html)
- [Consolidated billing](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/consolidated-billing.html)
- [Consolidated billing](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/consolidated-billing.html)
### Related Examples
- [Splitting the CUR and Sharing Access](https://wellarchitectedlabs.com/Cost/Cost_and_Usage_Analysis/300_Splitting_Sharing_CUR_Access/README.html)

- [Defining an AWS Multi-Account Strategy for telecommunications companies](https://aws.amazon.com/blogs/industries/defining-an-aws-multi-account-strategy-for-telecommunications-companies/)
- [Best Practices for Optimizing AWS accounts](https://aws.amazon.com/blogs/architecture/new-whitepaper-provides-best-practices-for-optimizing-aws-accounts/)
- [Best Practices for Organizational Units with AWS Organizations](https://aws.amazon.com/blogs/mt/best-practices-for-organizational-units-with-aws-organizations/?org_product_gs_bp_OUBlog)
### Related Videos
- [ Introducing AWS Organizations](https://www.youtube.com/watch?v=T4NK8fv8YdI)
- [ Set Up a Multi-Account AWS Environment that Uses Best Practices for AWS Organizations](https://www.youtube.com/watch?v=uOrq8ZUuaAQ)
