---
id: "SEC03-BP07"
title: "Analyze public and cross-account access"
framework: "WAF"
domain: "Security"
capability: "How do you manage permissions for people and machines?"
risk_level: "Low"
---

# SEC03-BP07 Analyze public and cross-account access

## Desired Outcome
Know which of your AWS resources are shared and with whom. Continually monitor and audit your shared resources to verify they are shared with only authorized principals.

## Anti-Patterns
- Not keeping an inventory of shared resources.
- Not following a process for approval of cross-account or public access to resources.

## Implementation Guidance
 If your account is in AWS Organizations, you can grant access to resources to the entire organization, specific organizational units, or individual accounts. If your account is not a member of an organization, you can share resources with individual accounts. You can grant direct cross-account access using resource-based policies — for example, [Amazon Simple Storage Service (Amazon S3) bucket policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html) — or by allowing a principal in another account to assume an IAM role in your account. When using resource policies, verify that access is only granted to authorized principals. Define a process to approve all resources which are required to be publicly available.

 [AWS Identity and Access Management Access Analyzer](https://aws.amazon.com/iam/features/analyze-access/) uses [provable security](https://aws.amazon.com/security/provable-security/) to identify all access paths to a resource from outside of its account. It reviews resource policies continuously, and reports findings of public and cross-account access to make it simple for you to analyze potentially broad access. Consider configuring IAM Access Analyzer with AWS Organizations to verify that you have visibility to all your accounts. IAM Access Analyzer also allows you to [preview findings](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-access-preview.html) before deploying resource permissions. This allows you to validate that your policy changes grant only the intended public and cross-account access to your resources. When designing for multi-account access, you can use [trust policies](https://aws.amazon.com/blogs/security/how-to-use-trust-policies-with-iam-roles/) to control in what cases a role can be assumed. For example, you could use the [`PrincipalOrgId` condition key to deny an attempt to assume a role from outside your AWS Organizations](https://aws.amazon.com/blogs/security/how-to-use-trust-policies-with-iam-roles/).

 [AWS Config can report resources](https://docs.aws.amazon.com/config/latest/developerguide/operational-best-practices-for-Publicly-Accessible-Resources.html) that are misconfigured, and through AWS Config policy checks, can detect resources that have public access configured. Services such as [AWS Control Tower](https://aws.amazon.com/controltower/) and [AWS Security Hub](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html) simplify deploying detective controls and guardrails across AWS Organizations to identify and remediate publicly exposed resources. For example, AWS Control Tower has a managed guardrail which can detect if any [Amazon EBS snapshots are restorable by AWS accounts](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html).

## Implementation Steps
- **Consider using [AWS Config for AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/services-that-can-integrate-config.html):** AWS Config allows you to aggregate findings from multiple accounts within an AWS Organizations to a delegated administrator account. This provides a comprehensive view, and allows you to [deploy AWS Config Rules across accounts to detect publicly accessible resources](https://docs.aws.amazon.com/config/latest/developerguide/config-rule-multi-account-deployment.html).
- **Configure AWS Identity and Access Management Access Analyzer:** IAM Access Analyzer helps you identify resources in your organization and accounts, such as Amazon S3 buckets or IAM roles that are [shared with an external entity](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-getting-started.html).
- **Use auto-remediation in AWS Config to respond to changes in public access configuration of Amazon S3 buckets:** [You can automatically turn on the block public access settings for Amazon S3 buckets](https://aws.amazon.com/blogs/security/how-to-use-aws-config-to-monitor-for-and-respond-to-amazon-s3-buckets-allowing-public-access/).
- **Implement monitoring and alerting to identify if Amazon S3 buckets have become public:** You must have [monitoring and alerting](https://aws.amazon.com/blogs/aws/amazon-s3-update-cloudtrail-integration/) in place to identify when Amazon S3 Block Public Access is turned off, and if Amazon S3 buckets become public. Additionally, if you are using AWS Organizations, you can create a [service control policy](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html) that prevents changes to Amazon S3 public access policies. [AWS Trusted Advisor](https://docs.aws.amazon.com/awssupport/latest/user/trusted-advisor.html) checks for Amazon S3 buckets that have open access permissions. Bucket permissions that grant, upload, or delete access to everyone create potential security issues by allowing anyone to add, modify, or remove items in a bucket. The Trusted Advisor check examines explicit bucket permissions and associated bucket policies that might override the bucket permissions. You also can use AWS Config to monitor your Amazon S3 buckets for public access. For more information, see [How to Use AWS Config to Monitor for and Respond to Amazon S3 Buckets Allowing Public Access](https://aws.amazon.com/blogs/security/how-to-use-aws-config-to-monitor-for-and-respond-to-amazon-s3-buckets-allowing-public-access/).

 When reviewing access controls for Amazon S3 buckets, it is important to consider the nature of the data stored within them. [Amazon Macie](https://docs.aws.amazon.com/macie/latest/user/findings-types.html) is a service designed to help you discover and protect sensitive data, such as Personally Identifiable Information (PII), Protected Health Information (PHI), and credentials like private keys or AWS access keys.

## Resources
### Related Documents
- [Using AWS Identity and Access Management Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html?ref=wellarchitected)
- [AWS Control Tower controls library ](https://docs.aws.amazon.com/controltower/latest/userguide/controls-reference.html)
- [AWS Foundational Security Best Practices standard](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-standards-fsbp.html)
- [AWS Config Managed Rules](https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_use-managed-rules.html)
- [AWS Trusted Advisor check reference](https://docs.aws.amazon.com/awssupport/latest/user/trusted-advisor-check-reference.html)
- [ Monitoring AWS Trusted Advisor check results with Amazon EventBridge ](https://docs.aws.amazon.com/awssupport/latest/user/cloudwatch-events-ta.html)
- [ Managing AWS Config Rules Across All Accounts in Your Organization ](https://docs.aws.amazon.com/config/latest/developerguide/config-rule-multi-account-deployment.html)
- [AWS Config and AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/services-that-can-integrate-config.html)
- [ Make your AMI publicly available for use in Amazon EC2 ](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/sharingamis-intro.html#block-public-access-to-amis)
### Related Videos
- [Best Practices for securing your multi-account environment](https://www.youtube.com/watch?v=ip5sn3z5FNg)
- [Dive Deep into IAM Access Analyzer](https://www.youtube.com/watch?v=i5apYXya2m0)
