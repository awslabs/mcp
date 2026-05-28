---
id: "SEC08-BP04"
title: "Enforce access control"
framework: "WAF"
domain: "Security"
capability: "How do you protect your data at rest?"
risk_level: "High"
---

# SEC08-BP04 Enforce access control

## Desired Outcome
You verify that only authorized users can access data on a need-to-know basis. You protect your data with regular backups and versioning to prevent against intentional or inadvertent modification or deletion of data. You isolate critical data from other data to protect its confidentiality and data integrity.

## Anti-Patterns
- Storing data with different sensitivity requirements or classification together.
- Using overly permissive permissions on decryption keys.
- Improperly classifying data.
- Not retaining detailed backups of important data.
- Providing persistent access to production data.
- Not auditing data access or regularly reviewing permissions.

## Implementation Guidance
 Protecting data at rest is important to maintain data integrity, confidentiality, and compliance with regulatory requirements. You can implement multiple controls to help achieve this, including access control, isolation, conditional access, and versioning.

 You can enforce access control with the principle of least privilege, which provides only the necessary permissions to users and services to perform their tasks. This includes access to encryption keys. Review your [AWS Key Management Service (AWS KMS) policies](https://docs.aws.amazon.com/kms/latest/developerguide/overview.html) to verify that the level of access you grant is appropriate and that relevant conditions apply.

 You can separate data based on different classification levels by using distinct AWS accounts for each level, and manage these accounts using [AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html). This isolation can help prevent unauthorized access and minimizes the risk of data exposure.

 Regularly review the level of access granted in Amazon S3 bucket policies. Avoid using publicly readable or writeable buckets unless absolutely necessary. Consider using [AWS Config](https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html) to detect publicly available buckets and Amazon CloudFront to serve content from Amazon S3. Verify that buckets that should not allow public access are properly configured to prevent it.

 Implement versioning and object locking mechanisms for critical data stored in Amazon S3. [Amazon S3 versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html) preserves previous versions of objects to recover data from accidental deletion or overwrites. [Amazon S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) provides mandatory access control for objects, which prevents them from being deleted or overwritten, even by the root user, until the lock expires. Additionally, [Amazon Glacier Vault Lock](https://docs.aws.amazon.com/amazonglacier/latest/dev/vault-lock.html) offers a similar feature for archives stored in Amazon Glacier.

## Implementation Steps
1.  **Enforce access control with the principle of least privilege**:
   - Review the access permissions granted to users and services, and verify that they have only the necessary permissions to perform their tasks.
   - Review access to encryption keys by checking the [AWS Key Management Service (AWS KMS) policies](https://docs.aws.amazon.com/kms/latest/developerguide/overview.html).

1.  **Separate data based on different classification levels**:
   - Use distinct AWS accounts for each data classification level.
   - Manage these accounts using [AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html).

1.  **Review Amazon S3 bucket and object permissions**:
   - Regularly review the level of access granted in Amazon S3 bucket policies.
   - Avoid using publicly readable or writeable buckets unless absolutely necessary.
   - Consider using [AWS Config](https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html) to detect publicly available buckets.
   - Use Amazon CloudFront to serve content from Amazon S3.
   - Verify that buckets that should not allow public access are properly configured to prevent it.
   - You can apply the same review process for databases and any other data sources that use IAM authentication, such as SQS or third-party data stores.

1.  **Use AWS IAM Access Analyzer**:
   - You can configure [AWS IAM Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html) to analyze Amazon S3 buckets and generate findings when an S3 policy grants access to an external entity.

1.  **Implement versioning and object locking mechanisms**:
   - Use [Amazon S3 versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html) to preserve previous versions of objects, which provides recovery from accidental deletion or overwrites.
   - Use [Amazon S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) to provide mandatory access control for objects, which prevents them from being deleted or overwritten, even by the root user, until the lock expires.
   - Use [Amazon Glacier Vault Lock](https://docs.aws.amazon.com/amazonglacier/latest/dev/vault-lock.html) for archives stored in Amazon Glacier.

1.  **Use Amazon S3 Inventory**:
   - You can use [Amazon S3 Inventory](https://docs.aws.amazon.com/AmazonS3/latest/dev/storage-inventory.html) to audit and report on the replication and encryption status of your S3 objects.

1.  **Review Amazon EBS and AMI sharing permissions**:
   - Review your sharing permissions for [Amazon EBS](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-modifying-snapshot-permissions.html) and [AMI sharing](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/sharing-amis.html) to verify that your images and volumes are not shared with AWS accounts that are external to your workload.

1.  **Review AWS Resource Access Manager Shares periodically**:
   - You can use [AWS Resource Access Manager](https://docs.aws.amazon.com/ram/latest/userguide/what-is.html) to share resources, such as AWS Network Firewall policies, Amazon Route 53 resolver rules, and subnets, within your Amazon VPCs.
   - Audit shared resources regularly and stop sharing resources that no longer need to be shared.

## Resources
### Related Best Practices
- [SEC03-BP01 Define access requirements](sec_permissions_define.md)
- [SEC03-BP02 Grant least privilege access](sec_permissions_least_privileges.md)
### Related Documents
- [AWS KMS Cryptographic Details Whitepaper](https://docs.aws.amazon.com/kms/latest/cryptographic-details/intro.html)
- [Introduction to Managing Access Permissions to Your Amazon S3 Resources](https://docs.aws.amazon.com/AmazonS3/latest/dev/intro-managing-access-s3-resources.html)
- [Overview of managing access to your AWS KMS resources](https://docs.aws.amazon.com/kms/latest/developerguide/control-access-overview.html)
- [AWS Config Rules](https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html)
- [Amazon S3 \$1 Amazon CloudFront: A Match Made in the Cloud](https://aws.amazon.com/blogs/networking-and-content-delivery/amazon-s3-amazon-cloudfront-a-match-made-in-the-cloud/)
- [Using versioning](https://docs.aws.amazon.com/AmazonS3/latest/dev/Versioning.html)
- [Locking Objects Using Amazon S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/dev/object-lock.html)
- [Sharing an Amazon EBS Snapshot](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-modifying-snapshot-permissions.html)
- [Shared AMIs](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/sharing-amis.html)
- [Hosting a single-page application on Amazon S3](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/deploy-a-react-based-single-page-application-to-amazon-s3-and-cloudfront.html)
- [AWS Global Condition Keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)
- [Building a Data Perimeter on AWS](https://docs.aws.amazon.com/whitepapers/latest/building-a-data-perimeter-on-aws/building-a-data-perimeter-on-aws.html)
### Related Videos
- [Securing Your Block Storage on AWS](https://youtu.be/Y1hE1Nkcxs8)
