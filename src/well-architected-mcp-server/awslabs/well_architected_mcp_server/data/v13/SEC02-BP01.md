---
id: "SEC02-BP01"
title: "Use strong sign-in mechanisms"
framework: "WAF"
domain: "Security"
capability: "How do you manage authentication for people and machines?"
risk_level: "High"
---

# SEC02-BP01 Use strong sign-in mechanisms

## Desired Outcome
Reduce the risks of unintended access to credentials in AWS by using strong sign-in mechanisms for [AWS Identity and Access Management (IAM)](https://aws.amazon.com/iam/) users, the [AWS account root user](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html), [AWS IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/what-is.html), and third-party identity providers. This means requiring MFA, enforcing strong password policies, and detecting anomalous login behavior.

## Anti-Patterns
- Not enforcing a strong password policy for your identities including complex passwords and MFA.
- Sharing the same credentials among different users.
- Not using detective controls for suspicious sign-ins.

## Implementation Guidance
 There are several ways for human identities to sign in to AWS. It is an AWS best practice to rely on a centralized identity provider using federation (direct SAML 2.0 federation between AWS IAM and the centralized IdP or using AWS IAM Identity Center) when authenticating to AWS. In this case, establish a secure sign-in process with your identity provider or Microsoft Active Directory.

 When you first open an AWS account, you begin with an AWS account root user. You should only use the account root user to set up access for your users (and for [tasks that require the root user](https://docs.aws.amazon.com/accounts/latest/reference/root-user-tasks.html)). It's important to turn on multi-factor authentication (MFA) for the account root user immediately after opening your AWS account and to secure the root user using the [AWS best practice guide](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_aws_account.html).

 AWS IAM Identity Center is designed for workforce users, and you can create and manage user identities within the service and secure the sign-in process with MFA. AWS Cognito, on the other hand, is designed for customer identity and access management (CIAM), which provides user pools and identity providers for external user identities in your applications.

 If you create users in AWS IAM Identity Center, secure the sign-in process in that service and [turn on MFA](https://docs.aws.amazon.com/singlesignon/latest/userguide/enable-mfa.html). For external user identities in your applications, you can use [Amazon Cognito user pools](https://docs.aws.amazon.com/cognito/index.html) and secure the sign-in process in that service or through one of the supported identity providers in Amazon Cognito user pools.

 Additionally, for users in AWS IAM Identity Center, you can use [AWS Verified Access](https://docs.aws.amazon.com/verified-access/latest/ug/what-is-verified-access.html) to provide an additional layer of security by verifying the user's identity and device posture before they are granted access to AWS resources.

 If you are using [AWS Identity and Access Management (IAM)](https://aws.amazon.com/iam/) users, secure the sign-in process using IAM.

 You can use both AWS IAM Identity Center and direct IAM federation simultaneously to manage access to AWS. You can use IAM federation to manage access to the AWS Management Console and services and IAM Identity Center to manage access to business applications like Quick Suite or Amazon Q Business.

 Regardless of the sign-in method, it's critical to enforce a strong sign-in policy.

## Implementation Steps
 The following are general strong sign-in recommendations. The actual settings you configure should be set by your company policy or use a standard like [NIST 800-63](https://pages.nist.gov/800-63-3/sp800-63b.html).
- Require MFA. It's an [IAM best practice to require MFA](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#enable-mfa-for-privileged-users) for human identities and workloads. Turning on MFA provides an additional layer of security requiring that users provide sign-in credentials and a one-time password (OTP) or a cryptographically verified and generated string from a hardware device.
- Enforce a minimum password length, which is a primary factor in password strength.
- Enforce password complexity to make passwords more difficult to guess.
- Allow users to change their own passwords.
- Create individual identities instead of shared credentials. By creating individual identities, you can give each user a unique set of security credentials. Individual users provide the ability to audit each user's activity.

 IAM Identity Center recommendations:
- IAM Identity Center provides a predefined [password policy](https://docs.aws.amazon.com/singlesignon/latest/userguide/password-requirements.html) when using the default directory that establishes password length, complexity, and reuse requirements.
- [Turn on MFA](https://docs.aws.amazon.com/singlesignon/latest/userguide/mfa-enable-how-to.html) and configure the context-aware or always-on setting for MFA when the identity source is the default directory, AWS Managed Microsoft AD, or AD Connector.
- Allow users to [register their own MFA devices](https://docs.aws.amazon.com/singlesignon/latest/userguide/how-to-allow-user-registration.html).

 Amazon Cognito user pools directory recommendations:
- Configure the [Password strength](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-policies.html) settings.
- [Require MFA](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-mfa.html) for users.
- Use the Amazon Cognito user pools [advanced security settings](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pool-settings-advanced-security.html) for features like [adaptive authentication](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pool-settings-adaptive-authentication.html) which can block suspicious sign-ins.

 IAM user recommendations:
- Ideally you are using IAM Identity Center or direct federation. However, you might have the need for IAM users. In that case, [set a password policy](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_passwords_account-policy.html) for IAM users. You can use the password policy to define requirements such as minimum length or whether the password requires non-alphabetic characters.
- Create an IAM policy to [enforce MFA sign-in](https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_users-self-manage-mfa-and-creds.html#tutorial_mfa_step1) so that users are allowed to manage their own passwords and MFA devices.

## Resources
### Related Best Practices
- [SEC02-BP03 Store and use secrets securely](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_identities_secrets.html)
- [SEC02-BP04 Rely on a centralized identity provider](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_identities_identity_provider.html)
- [SEC03-BP08 Share resources securely within your organization](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_permissions_share_securely.html)
### Related Documents
- [AWS IAM Identity Center Password Policy](https://docs.aws.amazon.com/singlesignon/latest/userguide/password-requirements.html)
- [IAM user password policy](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_passwords_account-policy.html)
- [Setting the AWS account root user password](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html)
- [Amazon Cognito password policy](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-policies.html)
- [AWS credentials](https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html)
- [IAM security best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
### Related Videos
- [Managing user permissions at scale with AWS IAM Identity Center](https://youtu.be/aEIqeFCcK7E)
- [Mastering identity at every layer of the cake](https://www.youtube.com/watch?v=vbjFjMNVEpc)
