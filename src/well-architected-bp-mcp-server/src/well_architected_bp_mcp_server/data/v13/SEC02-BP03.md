---
id: "SEC02-BP03"
title: "Store and use secrets securely"
framework: "WAF"
domain: "Security"
capability: "How do you manage authentication for people and machines?"
risk_level: "High"
---

# SEC02-BP03 Store and use secrets securely

## Desired Outcome
Implementing a mechanism for securely managing application credentials that achieves the following goals:
- Identifying what secrets are required for the workload.
- Reducing the number of long-term credentials required by replacing them with short-term credentials when possible.
- Establishing secure storage and automated rotation of remaining long-term credentials.
- Auditing access to secrets that exist in the workload.
- Continual monitoring to verify that no secrets are embedded in source code during the development process.
- Reduce the likelihood of credentials being inadvertently disclosed.

## Anti-Patterns
- Not rotating credentials.
- Storing long-term credentials in source code or configuration files.
- Storing credentials at rest unencrypted.

## Implementation Guidance
 In the past, credentials used to authenticate to databases, third-party APIs, tokens, and other secrets might have been embedded in source code or in environment files. AWS provides several mechanisms to store these credentials securely, automatically rotate them, and audit their usage.

 The best way to approach secrets management is to follow the guidance of remove, replace, and rotate. The most secure credential is one that you do not have to store, manage, or handle. There might be credentials that are no longer necessary to the functioning of the workload that can be safely removed.

 For credentials that are still required for the proper functioning of the workload, there might be an opportunity to replace a long-term credential with a temporary or short-term credential. For example, instead of hard-coding an AWS secret access key, consider replacing that long-term credential with a temporary credential using IAM roles.

 Some long-lived secrets might not be able to be removed or replaced. These secrets can be stored in a service such as [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html), where they can be centrally stored, managed, and rotated on a regular basis.

 An audit of the workload's source code and configuration files can reveal many types of credentials. The following table summarizes strategies for handling common types of credentials:

|  Credential type  |  Description  |  Suggested strategy  |
| --- | --- | --- |
|  IAM access keys  |  AWS IAM access and secret keys used to assume IAM roles inside of a workload  |  Replace: Use [IAM roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios.html) assigned to the compute instances (such as [Amazon EC2](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2.html) or [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html)) instead. For interoperability with third parties that require access to resources in your AWS account, ask if they support [AWS cross-account access](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios_third-party.html). For mobile apps, consider using temporary credentials through [Amazon Cognito identity pools (federated identities)](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-identity.html). For workloads running outside of AWS, consider [IAM Roles Anywhere](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/introduction.html) or [AWS Systems Manager Hybrid Activations](https://docs.aws.amazon.com/systems-manager/latest/userguide/activations.html). For containers see [Amazon ECS task IAM role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html) or [Amazon EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html).  |
|  SSH keys  |  Secure Shell private keys used to log into Linux EC2 instances, manually or as part of an automated process  |  Replace: Use [AWS Systems Manager](https://aws.amazon.com/blogs/mt/vr-beneficios-session-manager/) or [EC2 Instance Connect](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Connect-using-EC2-Instance-Connect.html) to provide programmatic and human access to EC2 instances using IAM roles.  |
|  Application and database credentials  |  Passwords – plain text string  |  Rotate: Store credentials in [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html) and establish automated rotation if possible.  |
|  Amazon RDS and Aurora Admin Database credentials  |  Passwords – plain text string  |  Replace: Use the [Secrets Manager integration with Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-secrets-manager.html) or [Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-secrets-manager.html). In addition, some RDS database types can use IAM roles instead of passwords for some use cases (for more detail, see [IAM database authentication](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html)).  |
|  OAuth tokens  |  Secret tokens – plain text string  |  Rotate: Store tokens in [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html) and configure automated rotation.  |
|  API tokens and keys  |  Secret tokens – plain text string  |  Rotate: Store in [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html) and establish automated rotation if possible.  |

 A common anti-pattern is embedding IAM access keys inside source code, configuration files, or mobile apps. When an IAM access key is required to communicate with an AWS service, use [temporary (short-term) security credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html). These short-term credentials can be provided through [IAM roles for EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html) instances, [execution roles](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html) for Lambda functions, [Cognito IAM roles](https://docs.aws.amazon.com/cognito/latest/developerguide/iam-roles.html) for mobile user access, and [IoT Core policies](https://docs.aws.amazon.com/iot/latest/developerguide/iot-policies.html) for IoT devices. When interfacing with third parties, prefer [delegating access to an IAM role](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios_third-party.html) with the necessary access to your account's resources rather than configuring an IAM user and sending the third party the secret access key for that user.

 There are many cases where the workload requires the storage of secrets necessary to interoperate with other services and resources. [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html) is purpose built to securely manage these credentials, as well as the storage, use, and rotation of API tokens, passwords, and other credentials.

 AWS Secrets Manager provides five key capabilities to ensure the secure storage and handling of sensitive credentials: [encryption at rest](https://docs.aws.amazon.com/secretsmanager/latest/userguide/security-encryption.html), [encryption in transit](https://docs.aws.amazon.com/secretsmanager/latest/userguide/data-protection.html), [comprehensive auditing](https://docs.aws.amazon.com/secretsmanager/latest/userguide/monitoring.html), [fine-grained access control](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access.html), and [extensible credential rotation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html). Other secret management services from AWS Partners or locally developed solutions that provide similar capabilities and assurances are also acceptable.

 When you retrieve a secret, you can use the Secrets Manager client side caching components to cache it for future use. Retrieving a cached secret is faster than retrieving it from Secrets Manager. Additionally, because there is a cost for calling Secrets Manager APIs, using a cache can reduce your costs. For all of the ways you can retrieve secrets, see [Get secrets](https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets.html).

**Note**
 Some languages may require you to implement your own in-memory encryption for client side caching.

## Implementation Steps
1.  Identify code paths containing hard-coded credentials using automated tools such as [Amazon CodeGuru](https://aws.amazon.com/codeguru/features/).

   1.  Use Amazon CodeGuru to scan your code repositories. Once the review is complete, filter on Type=Secrets in CodeGuru to find problematic lines of code.

1.  Identify credentials that can be removed or replaced.

   1.  Identify credentials no longer needed and mark for removal.

   1.  For AWS Secret Keys that are embedded in source code, replace them with IAM roles associated with the necessary resources. If part of your workload is outside AWS but requires IAM credentials to access AWS resources, consider [IAM Roles Anywhere](https://aws.amazon.com/blogs/security/extend-aws-iam-roles-to-workloads-outside-of-aws-with-iam-roles-anywhere/) or [AWS Systems Manager Hybrid Activations](https://docs.aws.amazon.com/systems-manager/latest/userguide/activations.html).

1.  For other third-party, long-lived secrets that require the use of the rotate strategy, integrate Secrets Manager into your code to retrieve third-party secrets at runtime.

   1.  The CodeGuru console can automatically [create a secret in Secrets Manager](https://aws.amazon.com/blogs/aws/codeguru-reviewer-secrets-detector-identify-hardcoded-secrets/) using the discovered credentials.

   1.  Integrate secret retrieval from Secrets Manager into your application code.

      1.  Serverless Lambda functions can use a language-agnostic [Lambda extension](https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets_lambda.html).

      1.  For EC2 instances or containers, AWS provides example [client-side code for retrieving secrets from Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets.html) in several popular programming languages.

1.  Periodically review your code base and re-scan to verify no new secrets have been added to the code.

   1.  Consider using a tool such as [git-secrets](https://github.com/awslabs/git-secrets) to prevent committing new secrets to your source code repository.

1.  [Monitor Secrets Manager activity](https://docs.aws.amazon.com/secretsmanager/latest/userguide/monitoring.html) for indications of unexpected usage, inappropriate secret access, or attempts to delete secrets.

1.  Reduce human exposure to credentials. Restrict access to read, write, and modify credentials to an IAM role dedicated for this purpose, and only provide access to assume the role to a small subset of operational users.

## Resources
### Related Best Practices
- [SEC02-BP02 Use temporary credentials](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_identities_unique.html)
- [SEC02-BP05 Audit and rotate credentials periodically](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_identities_audit.html)
### Related Documents
- [Getting Started with AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/getting-started.html)
- [Identity Providers and Federation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers.html)
- [Amazon CodeGuru Introduces Secrets Detector](https://aws.amazon.com/blogs/aws/codeguru-reviewer-secrets-detector-identify-hardcoded-secrets/)
- [How AWS Secrets Manager uses AWS Key Management Service](https://docs.aws.amazon.com/kms/latest/developerguide/services-secrets-manager.html)
- [Secret encryption and decryption in Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/security-encryption.html)
- [Secrets Manager blog entries](https://aws.amazon.com/blogs/security/tag/aws-secrets-manager/)
- [Amazon RDS announces integration with AWS Secrets Manager](https://aws.amazon.com/about-aws/whats-new/2022/12/amazon-rds-integration-aws-secrets-manager/)
### Related Videos
- [Best Practices for Managing, Retrieving, and Rotating Secrets at Scale](https://youtu.be/qoxxRlwJKZ4)
- [Find Hard-Coded Secrets Using Amazon CodeGuru Secrets Detector](https://www.youtube.com/watch?v=ryK3PN--oJs)
- [Securing Secrets for Hybrid Workloads Using AWS Secrets Manager](https://www.youtube.com/watch?v=k1YWhogGVF8)
### Related Workshops
- [Store, retrieve, and manage sensitive credentials in AWS Secrets Manager](https://catalog.us-east-1.prod.workshops.aws/workshops/92e466fd-bd95-4805-9f16-2df07450db42/en-US)
- [AWS Systems Manager Hybrid Activations](https://mng.workshop.aws/ssm/capability_hands-on_labs/hybridactivations.html)
