---
id: "COST02-BP04"
title: "Implement groups and roles"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you govern usage?"
risk_level: "Low"
---

# COST02-BP04 Implement groups and roles

## Implementation Guidance
User roles and groups are fundamental building blocks in the design and implementation of secure and efficient systems. Roles and groups help organizations balance the need for control with the requirement for flexibility and productivity, ultimately supporting organizational objectives and user needs. As recommended in [Identity and access management](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/identity-and-access-management.html) section of AWS Well-Architected Framework Security Pillar, you need robust identity management and permissions in place to provide access to the right resources for the right people under the right conditions. Users receive only the access necessary to complete their tasks. This minimizes the risk associated with unauthorized access or misuse.

 After you develop policies, you can create logical groups and user roles within your organization. This allows you to assign permissions, control usage, and help implement robust access control mechanisms, preventing unauthorized access to sensitive information. Begin with high-level groupings of people. Typically, this aligns with organizational units and job roles (for example, a systems administrator in the IT Department, financial controller, or business analysts). The groups categorize people that do similar tasks and need similar access. Roles define what a group must do. It is easier to manage permissions for groups and roles than for individual users. Roles and groups assign permissions consistently and systematically across all users, preventing errors and inconsistencies.

 When a user’s role changes, administrators can adjust access at the role or group level, rather than reconfiguring individual user accounts. For example, a systems administrator in IT requires access to create all resources, but an analytics team member only needs to create analytics resources.

## Implementation Steps
- ** Implement groups: **Using the groups of users defined in your organizational policies, implement the corresponding groups, if necessary. For best practices on users, groups and authentication, see the [Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html) of the AWS Well-Architected Framework.
- ** Implement roles and policies: **Using the actions defined in your organizational policies, create the required roles and access policies. For best practices on roles and policies, see the [Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html) of the AWS Well-Architected Framework.

## Resources
### Related Documents
- [AWS managed policies for job functions](https://docs.aws.amazon.com/iam/latest/UserGuide/access_policies_job-functions.html)
- [AWS multiple account billing strategy](https://aws.amazon.com/answers/account-management/aws-multi-account-billing-strategy/)
- [AWS Well-Architected Framework Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- [AWS Identity and Access Management (IAM) ](https://aws.amazon.com/iam/)
- [AWS Identity and Access Management policies ](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_managed-vs-inline.html)
### Related Videos
- [ Why use Identity and Access Management ](https://www.youtube.com/watch?v=SXSqhTn2DuE)
### Related Examples
- [Control access to AWS Regions using IAM policies](https://aws.amazon.com/blogs/security/easier-way-to-control-access-to-aws-regions-using-iam-policies/)
- [ Starting your Cloud Financial Management journey: Cloud cost operations ](https://aws.amazon.com/blogs/aws-cloud-financial-management/op-starting-your-cloud-financial-management-journey/)
