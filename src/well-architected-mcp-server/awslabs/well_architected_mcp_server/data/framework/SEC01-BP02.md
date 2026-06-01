---
id: "SEC01-BP02"
title: "Secure account root user and properties"
pillar: "Security"
risk_level: "HIGH"
capability: "How do you securely operate your workload?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate_aws_account.html"
---

# SEC01-BP02 Secure account root user and properties

The root user is the most privileged user in an AWS account, with
full administrative access to all resources within the account, and
in some cases cannot be constrained by security policies. Deactivating
programmatic access to the root user, establishing appropriate
controls for the root user, and avoiding routine use of the root
user helps reduce the risk of inadvertent exposure of the root
credentials and subsequent compromise of the cloud environment.

**Desired outcome:**Securing the root user helps reduce the
chance that accidental or intentional damage can occur through the misuse of root user
credentials. Establishing detective controls can also alert the appropriate personnel when
actions are taken using the root user.

**Common anti-patterns:**

- Using the root user for tasks other than the few that require root user credentials.
- Neglecting to test contingency plans on a regular basis to verify the functioning of
critical infrastructure, processes, and personnel during an emergency.
- Only considering the typical account login flow and neglecting to consider or test
alternate account recovery methods.
- Not handling DNS, email servers, and telephone providers as part of the critical
security perimeter, as these are used in the account recovery flow.

**Benefits of establishing this best practice:** Securing access to
the root user builds confidence that actions in your account are controlled and audited.

**Level of risk exposed if this best practice is not established**:
High

## Implementation guidance

AWS offers many tools to help secure your account. However,
because some of these measures are not turned on by default, you
must take direct action to implement them. Consider these
recommendations as foundational steps to securing your AWS account. As you implement these steps it’s important that you
build a process to continuously assess and monitor the security
controls.

When you first create an AWS account, you begin with one identity
that has complete access to all AWS services and resources in the
account. This identity is called the AWS account root user. You
can sign in as the root user using the email address and password
that you used to create the account. Due to the elevated access
granted to the AWS root user, you must limit use of the AWS root
user to perform tasks that
[specifically
require it](https://docs.aws.amazon.com/general/latest/gr/aws_tasks-that-require-root.html). The root user login credentials must be closely
guarded, and multi-factor authentication (MFA) should always be
used for the AWS account root user.

In addition to the normal authentication flow to log into your
root user using a username, password, and multi-factor
authentication (MFA) device, there are account recovery flows to
log into your AWS account root user given access to the email
address and phone number associated with your account. Therefore,
it is equally important to secure the root user email account
where the recovery email is sent and the phone number associated
with the account. Also consider potential circular dependencies
where the email address associated with the root user is hosted on
email servers or domain name service (DNS) resources from the same
AWS account.

When using AWS Organizations, there are multiple AWS accounts each
of which have a root user. One account is designated as the
management account and several layers of member accounts can then
be added underneath the management account. Prioritize securing
your management account’s root user, then address your member
account root users. The strategy for securing your management
account’s root user can differ from your member account root
users, and you can place preventative security controls on your
member account root users.

**Implementation steps**

The following implementation steps are recommended to establish controls for the root
user. Where applicable, recommendations are cross-referenced to [CIS AWS
Foundations benchmark version 1.4.0](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cis-controls-1.4.0.html). In addition to these steps, consult [AWS best
practice guidelines](https://aws.amazon.com/premiumsupport/knowledge-center/security-best-practices/) for securing your AWS account and resources.

**Preventative controls**

- Set up accurate [contact
information](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-update-contact-primary.html) for the account.

This information is used for the lost password recovery flow, lost MFA device
account recovery flow, and for critical security-related communications with your
team.
- Use an email address hosted by your corporate domain, preferably a distribution
list, as the root user’s email address. Using a distribution list rather than an
individual’s email account provides additional redundancy and continuity for access
to the root account over long periods of time.
- The phone number listed on the contact information should be a dedicated,
secure phone for this purpose. The phone number should not be listed or shared with
anyone.

- Do not create access keys for the root user. If access keys exist, remove them (CIS
1.4).

Eliminate any long-lived programmatic credentials (access and secret keys) for
the root user.
- If root user access keys already exist, you should transition processes using
those keys to use temporary access keys from an AWS Identity and Access Management (IAM) role, then [delete the root user access keys](https://docs.aws.amazon.com/accounts/latest/reference/root-user-access-key.html#root-user-delete-access-key).

- Determine if you need to store credentials for the root user.

If you are using AWS Organizations to create new member accounts, the initial password
for the root user on new member accounts is set to a random value that is not
exposed to you. Consider using the password reset flow from your AWS Organization
management account to [gain access to the member account](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_access.html#orgs_manage_accounts_access-as-root) if needed.
- For standalone AWS accounts or the management AWS Organization account,
consider creating and securely storing credentials for the root user. Use MFA for
the root user.

- Use preventative controls for member account root users in AWS multi-account
environments.

Consider using the [Disallow Creation of Root Access Keys for the Root User](https://docs.aws.amazon.com/controltower/latest/userguide/strongly-recommended-controls.html#disallow-root-access-keys) preventative
guard rail for member accounts.
- Consider using the [Disallow Actions as a Root User](https://docs.aws.amazon.com/controltower/latest/userguide/strongly-recommended-controls.html#disallow-root-auser-actions) preventative guard rail for member
accounts.

- If you need credentials for the root user:

Use a complex password.
- Turn on multi-factor authentication (MFA) for the root user, especially for
AWS Organizations management (payer) accounts (CIS 1.5).
- Consider hardware MFA devices for resiliency and security, as single use
devices can reduce the chances that the devices containing your MFA codes might be
reused for other purposes. Verify that hardware MFA devices powered by a battery are
replaced regularly. (CIS 1.6)

To configure MFA for the root user, follow the instructions for creating
either a [virtual MFA](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_enable_virtual.html#enable-virt-mfa-for-root) or [hardware MFA device](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_enable_physical.html#enable-hw-mfa-for-root).

- Consider enrolling multiple MFA devices for backup. [Up to 8 MFA devices
are allowed per account](https://aws.amazon.com/blogs/security/you-can-now-assign-multiple-mfa-devices-in-iam/).

Note that enrolling more than one MFA device for the root user
automatically turns off the [flow for recovering
your account if the MFA device is lost](https://aws.amazon.com/premiumsupport/knowledge-center/reset-root-user-mfa/).

- Store the password securely, and consider circular dependencies if storing the
password electronically. Don’t store the password in such a way that would require
access to the same AWS account to obtain it.

- Optional: Consider establishing a periodic password rotation schedule for the root
user.

Credential management best practices depend on your regulatory and policy
requirements. Root users protected by MFA are not reliant on the password as a
single factor of authentication.
- [Changing
the root user password](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_passwords_change-root.html) on a periodic basis reduces the risk that an
inadvertently exposed password can be misused.

**Detective controls**

- Create alarms to detect use of the root credentials (CIS 1.7). [Amazon GuardDuty](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_settingup.html) can monitor and alert on root user API credential usage through the
[RootCredentialUsage](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-iam.html#policy-iam-rootcredentialusage) finding.
- Evaluate and implement the detective controls included in the [AWS Well-Architected Security Pillar conformance pack for AWS Config](https://docs.aws.amazon.com/config/latest/developerguide/operational-best-practices-for-wa-Security-Pillar.html), or if
using AWS Control Tower, the [strongly
recommended controls](https://docs.aws.amazon.com/controltower/latest/userguide/strongly-recommended-controls.html) available inside Control Tower.

**Operational guidance**

- Determine who in the organization should have access to the root user credentials.

Use a two-person rule so that no one individual has access to all necessary
credentials and MFA to obtain root user access.
- Verify that the organization, and not a single individual, maintains control
over the phone number and email alias associated with the account (which are used
for password reset and MFA reset flow).

- Use root user only by exception (CIS 1.7).

The AWS root user must not be used for everyday tasks, even administrative
ones. Only log in as the root user to perform [AWS tasks that require
root user](https://docs.aws.amazon.com/general/latest/gr/aws_tasks-that-require-root.html). All other actions should be performed by other users assuming
appropriate roles.

- Periodically check that access to the root user is functioning so that procedures
are tested prior to an emergency situation requiring the use of the root user
credentials.
- Periodically check that the email address associated with the account and those
listed under [Alternate
Contacts](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-update-contact-alternate.html) work. Monitor these email inboxes for security notifications you
might receive from . Also ensure any phone numbers
associated with the account are working.
- Prepare incident response procedures to respond to root account misuse. Refer to
the [AWS Security Incident Response Guide](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/aws-security-incident-response-guide.html) and the best practices in
the [Incident Response section of the Security Pillar whitepaper](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/incident-response.html)
for more information on building an incident response strategy for your AWS account.

## Resources

**Related best practices:**

- SEC01-BP01 Separate workloads using accounts
- SEC02-BP01 Use strong sign-in mechanisms
- SEC03-BP02 Grant least privilege access
- SEC03-BP03 Establish emergency access process
- SEC10-BP05 Pre-provision access

**Related documents:**

- [AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)
- [AWS Security Audit Guidelines](https://docs.aws.amazon.com/general/latest/gr/aws-security-audit-guide.html)
- [IAM
Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [Amazon GuardDuty – root credential usage alert](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-iam.html#policy-iam-rootcredentialusage)
- [Step-by-step
guidance on monitoring for root credential use through
CloudTrail](https://docs.aws.amazon.com/securityhub/latest/userguide/iam-controls.html#iam-20)
- [MFA
tokens approved for use with AWS](https://aws.amazon.com/iam/features/mfa/)
- Implementing [break
glass access](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/break-glass-access.html) on AWS
- [Top
10 security items to improve in your AWS account](https://aws.amazon.com/blogs/security/top-10-security-items-to-improve-in-your-aws-account/)
- [What
do I do if I notice unauthorized activity in my AWS account?](https://aws.amazon.com/premiumsupport/knowledge-center/potential-account-compromise/)

**Related videos:**

- [Enable AWS
adoption at scale with automation and governance](https://youtu.be/GUMSgdB-l6s)
- [Security
Best Practices the Well-Architected Way](https://youtu.be/u6BCVkXkPnM)
- [Limiting use of AWS root
credentials](https://youtu.be/SMjvtxXOXdU?t=979) from AWS re:inforce 2022 – Security best practices with AWS
IAM
