---
id: "OPS02-BP01"
title: "Resources have identified owners"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you structure your organization to support your business outcomes?"
risk_level: "High"
effort: "Low"
---

# OPS02-BP01 Resources have identified owners

## Desired Outcome
- Resources have identified owners using metadata or a central register.
- Team members can identify who owns resources.
- Accounts have a single owner where possible.

## Anti-Patterns
- The alternate contacts for your AWS accounts are not populated.
- Resources lack tags that identify what teams own them.
- You have an ITSM queue without an email mapping.
- Two teams have overlapping ownership of a critical piece of infrastructure.

## Implementation Guidance
 Define what ownership means for the resource use cases in your environment. Ownership can mean who oversees changes to the resource, supports the resource during troubleshooting, or who is financially accountable. Specify and record owners for resources, including name, contact information, organization, and team.

 **Customer example**

 AnyCompany Retail defines ownership as the team or individual that owns changes and support for resources. They leverage AWS Organizations to manage their AWS accounts. Alternate account contacts are configuring using group inboxes. Each ITSM queue maps to an email alias. Tags identify who own AWS resources. For other platforms and infrastructure, they have a wiki page that identifies ownership and contact information.

## Implementation Steps
1.  Start by defining ownership for your organization. Ownership can imply who owns the risk for the resource, who owns changes to the resource, or who supports the resource when troubleshooting. Ownership could also imply financial or administrative ownership of the resource.

1.  Use [AWS Organizations](https://aws.amazon.com/organizations/) to manage accounts. You can manage the alternate contacts for your accounts centrally.

   1.  Using company owned email addresses and phone numbers for contact information helps you to access them even if the individuals whom they belong to are no longer with your organization. For example, create separate email distribution lists for billing, operations, and security and configure these as Billing, Security, and Operations contacts in each active AWS account. Multiple people will receive AWS notifications and be able to respond, even if someone is on vacation, changes roles, or leaves the company.

   1.  If an account is not managed by [AWS Organizations](https://aws.amazon.com/organizations/), alternate account contacts help AWS get in contact with the appropriate personnel if needed. Configure the account's alternate contacts to point to a group rather than an individual.

1.  Use tags to identify owners for AWS resources. You can specify both owners and their contact information in separate tags.

   1.  You can use [AWS Config](https://aws.amazon.com/config/) rules to enforce that resources have the required ownership tags.

   1.  For in-depth guidance on how to build a tagging strategy for your organization, see [AWS Tagging Best Practices whitepaper](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html).

1.  Use [Amazon Q Business](https://aws.amazon.com/q/business/), a conversational assistant that uses generative AI to enhance workforce productivity, answer questions, and complete tasks based on information in your enterprise systems.

   1.  Connect Amazon Q Business to your company's data source. Amazon Q Business offers prebuilt connectors to over 40 supported data sources, including Amazon Simple Storage Service (Amazon S3), Microsoft SharePoint, Salesforce, and Atlassian Confluence. For more information, see [Amazon Q Business connectors](https://aws.amazon.com/q/business/connectors/).

1.  For other resources, platforms, and infrastructure, create documentation that identifies ownership. This should be accessible to all team members.

## Resources
### Related Best Practices
- [OPS02-BP02 Processes and procedures have identified owners](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ops_model_def_proc_owners.html)
- [OPS02-BP04 Mechanisms exist to manage responsibilities and ownership](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ops_model_def_responsibilities_ownership.html)
### Related Documents
- [AWS Account Management - Updating contact information](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-update-contact.html)
- [AWS Organizations - Updating alternative contacts in your organization](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_update_contacts.html)
- [AWS Tagging Best Practices whitepaper](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html)
- [Build private and secure enterprise generative AI apps with Amazon Q Business and AWS IAM Identity Center](https://aws.amazon.com/blogs/machine-learning/build-private-and-secure-enterprise-generative-ai-apps-with-amazon-q-business-and-aws-iam-identity-center/)
- [Amazon Q Business, now generally available, helps boost workforce productivity with generative AI](https://aws.amazon.com/blogs/aws/amazon-q-business-now-generally-available-helps-boost-workforce-productivity-with-generative-ai/)
- [AWS Cloud Operations & Migrations Blog - Implementing automated and centralized tagging controls with AWS Config and AWS Organizations](https://aws.amazon.com/blogs/mt/implementing-automated-and-centralized-tagging-controls-with-aws-config-and-aws-organizations/)
- [AWS Security Blog - Extend your pre-commit hooks with AWS CloudFormation Guard](https://aws.amazon.com/blogs/security/extend-your-pre-commit-hooks-with-aws-cloudformation-guard/)
- [AWS DevOps Blog - Integrating AWS CloudFormation Guard into CI/CD pipelines](https://aws.amazon.com/blogs/devops/integrating-aws-cloudformation-guard/)
### Related Workshops
- [AWS Workshop - Tagging](https://catalog.workshops.aws/tagging/)
### Related Examples
- [AWS Config Rules - Amazon EC2 with required tags and valid values](https://github.com/awslabs/aws-config-rules/blob/master/python/ec2_require_tags_with_valid_values.py)
### Related Services
- [AWS Config Rules - required-tags](https://docs.aws.amazon.com/config/latest/developerguide/required-tags.html)
- [AWS Organizations](https://aws.amazon.com/organizations/)
