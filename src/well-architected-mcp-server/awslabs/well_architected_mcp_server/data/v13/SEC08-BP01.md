---
id: "SEC08-BP01"
title: "Implement secure key management"
framework: "WAF"
domain: "Security"
capability: "How do you protect your data at rest?"
risk_level: "High"
---

# SEC08-BP01 Implement secure key management

## Desired Outcome
You have a scalable, repeatable, and automated key management mechanism. The mechanism enforces least privilege access to key material and provides the correct balance between key availability, confidentiality, and integrity. You monitor access to the keys, and if rotation of key material is required, you rotate them using an automated process. You do not allow key material to be accessed by human operators.

## Anti-Patterns
- Human access to unencrypted key material.
- Creating custom cryptographic algorithms.
- Overly broad permissions to access key material.

## Implementation Guidance
 Encryption of data at rest is a fundamental security control. To implement this control, your workload needs a mechanism to securely store and manage the key material used to encrypt your data at rest.

 AWS offers the AWS Key Management Service (AWS KMS) to provide durable, secure, and redundant storage for AWS KMS keys. [Many AWS services integrate with AWS KMS](https://aws.amazon.com/kms/features/#integration) to support encryption of your data. AWS KMS uses FIPS 140-3 Level 3 validated hardware security modules to protect your keys. There is no mechanism to export AWS KMS keys in plain text.

 When deploying workloads using a multi-account strategy, you should keep AWS KMS keys in the same account as the workload that uses them. [This distributed model](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/application.html#app-kms) places the responsibility for managing the AWS KMS keys with your team. In other use cases, your organization may choose to store AWS KMS keys into a centralized account. This centralized structure requires additional policies to enable the cross-account access required for the workload account to access keys stored in the centralized account, but may be more applicable in use cases where a single key is shared across multiple AWS accounts.

 Regardless of where the key material is stored, you should tightly control access to the key through the use of [key policies](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html) and IAM policies. Key policies are the primary way to control access to an AWS KMS key. Additionally, AWS KMS key grants can provide access to AWS services to encrypt and decrypt data on your behalf. Review the [guidance for access control to your AWS KMS keys](https://docs.aws.amazon.com/kms/latest/developerguide/iam-policies-best-practices.html).

 You should monitor the use of encryption keys to detect unusual access patterns. Operations performed using AWS managed keys and customer managed keys stored in AWS KMS can be logged in AWS CloudTrail and should be reviewed periodically. Pay special attention to monitoring key destruction events. To mitigate accidental or malicious destruction of key material, key destruction events do not delete the key material immediately. Attempts to delete keys in AWS KMS are subject to a [waiting period](https://docs.aws.amazon.com/kms/latest/developerguide/deleting-keys.html#deleting-keys-how-it-works), which defaults to 30 days and a minimum of 7 days, providing administrators time to review these actions and roll back the request if necessary.

 Most AWS services use AWS KMS in a way that is transparent to you - your only requirement is to decide whether to use an AWS managed or customer managed key. If your workload requires the direct use of AWS KMS to encrypt or decrypt data, you should use [envelope encryption](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#enveloping) to protect your data. The [AWS Encryption SDK](https://docs.aws.amazon.com/encryption-sdk/latest/developer-guide/introduction.html) can provide your applications client-side encryption primitives to implement envelope encryption and integrate with AWS KMS.

## Implementation Steps
1.  Determine the appropriate [key management options](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#key-mgmt) (AWS managed or customer managed) for the key.

   1.  For ease of use, AWS offers AWS owned and AWS managed keys for most services, which provide encryption-at-rest capability without the need to manage key material or key policies.

   1.  When using customer managed keys, consider the default key store to provide the best balance between agility, security, data sovereignty, and availability. Other use cases may require the use of custom key stores with [AWS CloudHSM](https://aws.amazon.com/cloudhsm/) or the [external key store](https://docs.aws.amazon.com/kms/latest/developerguide/keystore-external.html).

1.  Review the list of services that you are using for your workload to understand how AWS KMS integrates with the service. For example, EC2 instances can use encrypted EBS volumes, verifying that Amazon EBS snapshots created from those volumes are also encrypted using a customer managed key and mitigating accidental disclosure of unencrypted snapshot data.

   1.  [How AWS services use AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/service-integration.html)

   1.  For detailed information about the encryption options that an AWS service offers, see the Encryption at Rest topic in the user guide or the developer guide for the service.

1.  Implement AWS KMS: AWS KMS makes it simple for you to create and manage keys and control the use of encryption across a wide range of AWS services and in your applications.

   1.  [Getting started: AWS Key Management Service (AWS KMS)](https://docs.aws.amazon.com/kms/latest/developerguide/getting-started.html)

   1.  Review the [best practices for access control to your AWS KMS keys](https://docs.aws.amazon.com/kms/latest/developerguide/iam-policies-best-practices.html).

1.  Consider AWS Encryption SDK: Use the AWS Encryption SDK with AWS KMS integration when your application needs to encrypt data client-side.

   1.  [AWS Encryption SDK](https://docs.aws.amazon.com/encryption-sdk/latest/developer-guide/introduction.html)

1.  Enable [IAM Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html) to automatically review and notify if there are overly broad AWS KMS key policies.

   1.  Consider using [custom policy checks](https://docs.aws.amazon.com/access-analyzer/latest/APIReference/API_CheckNoPublicAccess.html) to verify that a resource policy update does not grant public access to KMS Keys.

1.  Enable [Security Hub](https://docs.aws.amazon.com/securityhub/latest/userguide/kms-controls.html) to receive notifications if there are misconfigured key policies, keys scheduled for deletion, or keys without automated rotation enabled.

1.  Determine the logging level appropriate for your AWS KMS keys. Since calls to AWS KMS, including read-only events, are logged, the CloudTrail logs associated with AWS KMS can become voluminous.

   1.  Some organizations prefer to segregate the AWS KMS logging activity into a separate trail. For more detail, see the [Logging AWS KMS API calls with CloudTrail](https://docs.aws.amazon.com/kms/latest/developerguide/logging-using-cloudtrail.html) section of the AWS KMS developers guide.

## Resources
### Related Documents
- [AWS Key Management Service](https://docs.aws.amazon.com/kms/latest/developerguide/overview.html)
- [AWS cryptographic services and tools](https://docs.aws.amazon.com/crypto/latest/userguide/awscryp-overview.html)
- [Protecting Amazon S3 Data Using Encryption](https://docs.aws.amazon.com/AmazonS3/latest/dev/UsingEncryption.html)
- [Envelope encryption](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#enveloping)
- [Digital sovereignty pledge](https://aws.amazon.com/blogs/security/aws-digital-sovereignty-pledge-control-without-compromise/)
- [Demystifying AWS KMS key operations, bring your own key, custom key store, and ciphertext portability](https://aws.amazon.com/blogs/security/demystifying-kms-keys-operations-bring-your-own-key-byok-custom-key-store-and-ciphertext-portability/)
- [AWS Key Management Service cryptographic details](https://docs.aws.amazon.com/kms/latest/cryptographic-details/intro.html)
### Related Videos
- [How Encryption Works in AWS](https://youtu.be/plv7PQZICCM)
- [Securing Your Block Storage on AWS](https://youtu.be/Y1hE1Nkcxs8)
- [AWS data protection: Using locks, keys, signatures, and certificates](https://www.youtube.com/watch?v=lD34wbc7KNA)
### Related Examples
- [Implement advanced access control mechanisms using AWS KMS](https://catalog.workshops.aws/advkmsaccess/en-US/introduction)
