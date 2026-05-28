---
id: "SEC03-BP01"
title: "Define access requirements"
framework: "WAF"
domain: "Security"
capability: "How do you manage permissions for people and machines?"
risk_level: "High"
---

# SEC03-BP01 Define access requirements

## Anti-Patterns
- Hard-coding or storing secrets in your application.
- Granting custom permissions for each user.
- Using long-lived credentials.

## Implementation Guidance
 Each component or resource of your workload needs to be accessed by administrators, end users, or other components. Have a clear definition of who or what should have access to each component, choose the appropriate identity type and method of authentication and authorization.

Regular access to AWS accounts within the organization should be provided using [federated access](https://aws.amazon.com/identity/federation/) or a centralized identity provider. You should also centralize your identity management and ensure that there is an established practice to integrate AWS access to your employee access lifecycle. For example, when an employee changes to a job role with a different access level, their group membership should also change to reflect their new access requirements.

 When defining access requirements for non-human identities, determine which applications and components need access and how permissions are granted. Using IAM roles built with the least privilege access model is a recommended approach. [AWS Managed policies](https://docs.aws.amazon.com/singlesignon/latest/userguide/security-iam-awsmanpol.html) provide predefined IAM policies that cover most common use cases.

AWS services, such as [AWS Secrets Manager](https://aws.amazon.com/blogs/security/identify-arrange-manage-secrets-easily-using-enhanced-search-in-aws-secrets-manager/) and [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html), can help decouple secrets from the application or workload securely. In Secrets Manager, you can establish automatic rotation for your credentials. You can use Systems Manager to reference parameters in your scripts, commands, SSM documents, configuration, and automation workflows by using the unique name that you specified when you created the parameter.

 You can use [AWS IAM Roles Anywhere](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/introduction.html) to obtain [temporary security credentials in IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html) for workloads that run outside of AWS. Your workloads can use the same [IAM policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html) and [IAM roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html) that you use with AWS applications to access AWS resources.

 Where possible, prefer short-term temporary credentials over long-term static credentials. For scenarios in which you need users with programmatic access and long-term credentials, use [access key last used information](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_RotateAccessKey) to rotate and remove access keys.

Users need programmatic access if they want to interact with AWS outside of the AWS Management Console. The way to grant programmatic access depends on the type of user that's accessing AWS.

To grant users programmatic access, choose one of the following options.

****

| Which user needs programmatic access? | To | By |
| --- | --- | --- |
|  Workforce identity (Users managed in IAM Identity Center)  | Use temporary credentials to sign programmatic requests to the AWS CLI, AWS SDKs, or AWS APIs. |  Following the instructions for the interface that you want to use. [\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/sec_permissions_define.html)  |
| IAM | Use temporary credentials to sign programmatic requests to the AWS CLI, AWS SDKs, or AWS APIs. | Following the instructions in [Using temporary credentials with AWS resources](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_use-resources.html) in the IAM User Guide. |
| IAM | (Not recommended)Use long-term credentials to sign programmatic requests to the AWS CLI, AWS SDKs, or AWS APIs. |  Following the instructions for the interface that you want to use. [\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/sec_permissions_define.html)  |

## Resources
### Related Documents
- [Attribute-based access control (ABAC)](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction_attribute-based-access-control.html)
- [AWS IAM Identity Center](https://aws.amazon.com/iam/identity-center/)
- [IAM Roles Anywhere](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/introduction.html)
- [AWS Managed policies for IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/security-iam-awsmanpol.html)
- [AWS IAM policy conditions](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)
- [IAM use cases](https://docs.aws.amazon.com/IAM/latest/UserGuide/IAM_UseCases.html)
- [Remove unnecessary credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#remove-credentials)
- [Working with Policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_manage.html)
- [How to control access to AWS resources based on AWS account, OU, or organization](https://aws.amazon.com/blogs/security/how-to-control-access-to-aws-resources-based-on-aws-account-ou-or-organization/)
- [Identify, arrange, and manage secrets easily using enhanced search in AWS Secrets Manager](https://aws.amazon.com/blogs/security/identify-arrange-manage-secrets-easily-using-enhanced-search-in-aws-secrets-manager/)
### Related Videos
- [Become an IAM Policy Master in 60 Minutes or Less](https://youtu.be/YQsK4MtsELU)
- [Separation of Duties, Least Privilege, Delegation, and CI/CD](https://youtu.be/3H0i7VyTu70)
- [Streamlining identity and access management for innovation](https://www.youtube.com/watch?v=3qK0b1UkaE8)
