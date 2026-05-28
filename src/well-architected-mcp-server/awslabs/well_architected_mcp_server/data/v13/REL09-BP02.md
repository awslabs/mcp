---
id: "REL09-BP02"
title: "Secure and encrypt backups"
framework: "WAF"
domain: "Reliability"
capability: "How do you back up data?"
risk_level: "High"
---

# REL09-BP02 Secure and encrypt backups

## Anti-Patterns
- Having the same access to the backups and restoration automation as you do to the data.
- Not encrypting your backups.
- Not implementing immutability for protection against deletion or tampering.
- Using the same security domain for production and backup systems.
- Not validating backup integrity through regular testing.

## Implementation Guidance
 Control and detect access to backups using authentication and authorization, such as AWS Identity and Access Management (IAM). Prevent and detect if data integrity of backups is compromised using encryption.

 Amazon S3 supports several methods of encryption of your data at rest. Using server-side encryption, Amazon S3 accepts your objects as unencrypted data, and then encrypts them as they are stored. Using client-side encryption, your workload application is responsible for encrypting the data before it is sent to Amazon S3. Both methods allow you to use AWS Key Management Service (AWS KMS) to create and store the data key, or you can provide your own key, which you are then responsible for. Using AWS KMS, you can set policies using IAM on who can and cannot access your data keys and decrypted data.

 For Amazon RDS, if you have chosen to encrypt your databases, then your backups are encrypted also. DynamoDB backups are always encrypted. When using AWS Elastic Disaster Recovery, all data in transit and at rest is encrypted. With Elastic Disaster Recovery, data at rest can be encrypted using either the default Amazon EBS encryption Volume Encryption Key or a custom customer-managed key.

 **Cyber resilience considerations**

 To enhance backup security against cyber threats, consider implementing these additional controls besides encryption:
- Implement immutability using AWS Backup Vault Lock or Amazon S3 Object Lock to prevent backup data from being altered or deleted during its retention period, protecting against ransomware and malicious deletion.
- Establish logical isolation between production and backup environments with AWS Backup logically air-gapped vault for critical systems, creating separation that helps prevent compromise of both environments simultaneously.
- Validate backup integrity regularly using AWS Backup restore testing to verify that backups are not corrupted and can be successfully restored following a cyber incident.
- Implement multi-party approval for critical recovery operations using AWS Backup multi-party approval to prevent unauthorized or malicious recovery attempts by requiring authorization from multiple designated approvers.

## Implementation Steps
1.  Use encryption on each of your data stores. If your source data is encrypted, then the backup will also be encrypted.
   - [Use encryption in Amazon RDS.](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html). You can configure encryption at rest using AWS Key Management Service when you create an RDS instance.
   - [Use encryption on Amazon EBS volumes.](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EBSEncryption.html). You can configure default encryption or specify a unique key upon volume creation.
   - Use the required [Amazon DynamoDB encryption](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/EncryptionAtRest.html). DynamoDB encrypts all data at rest. You can either use an AWS owned AWS KMS key or an AWS managed KMS key, specifying a key that is stored in your account.
   - [Encrypt your data stored in Amazon EFS](https://docs.aws.amazon.com/efs/latest/ug/encryption.html). Configure the encryption when you create your file system.
   - Configure the encryption in the source and destination Regions. You can configure encryption at rest in Amazon S3 using keys stored in KMS, but the keys are Region-specific. You can specify the destination keys when you configure the replication.
   - Choose whether to use the default or custom [Amazon EBS encryption for Elastic Disaster Recovery](https://docs.aws.amazon.com/drs/latest/userguide/volumes-drs.html#ebs-encryption). This option will encrypt your replicated data at rest on the Staging Area Subnet disks and the replicated disks.

1.  Implement least privilege permissions to access your backups. Follow best practices to limit the access to the backups, snapshots, and replicas in accordance with [security best practices](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html).

1.  Configure immutability for critical backups. For critical data, implement AWS Backup Vault Lock or S3 Object Lock to prevent deletion or alteration during the specified retention period. For implementation details, see [AWS Backup Vault Lock](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html).

1.  Create logical separation for backup environments. Implement AWS Backup logically air-gapped vault for critical systems requiring enhanced protection from cyber threats. For implementation guidance, see [Building cyber resiliency with AWS Backup logically air-gapped vault](https://aws.amazon.com/blogs/storage/building-cyber-resiliency-with-aws-backup-logically-air-gapped-vault/).

1.  Implement backup validation processes. Configure AWS Backup restore testing to regularly verify that backups are not corrupted and can be successfully restored following a cyber incident. For more information, see [Validate recovery readiness with AWS Backup restore testing](https://aws.amazon.com/blogs/storage/validate-recovery-readiness-with-aws-backup-restore-testing/).

1.  Configure multi-party approval for sensitive recovery operations. For critical systems, implement AWS Backup multi-party approval to require authorization from multiple designated approvers before recovery can proceed. For implementation details, see [Improve recovery resilience with AWS Backup support for Multi-party approval](https://aws.amazon.com/blogs/storage/improve-recovery-resilience-with-aws-backup-support-for-multi-party-approval/).

## Resources
### Related Documents
- [AWS Marketplace: products that can be used for backup](https://aws.amazon.com/marketplace/search/results?searchTerms=Backup)
- [Amazon EBS Encryption](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EBSEncryption.html)
- [Amazon S3: Protecting Data Using Encryption](https://docs.aws.amazon.com/AmazonS3/latest/dev/UsingEncryption.html)
- [CRR Additional Configuration: Replicating Objects Created with Server-Side Encryption (SSE) Using Encryption Keys stored in AWS KMS](https://docs.aws.amazon.com/AmazonS3/latest/dev/crr-replication-config-for-kms-objects.html)
- [DynamoDB Encryption at Rest](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/EncryptionAtRest.html)
- [Encrypting Amazon RDS Resources](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html)
- [Encrypting Data and Metadata in Amazon EFS](https://docs.aws.amazon.com/efs/latest/ug/encryption.html)
- [Encryption for Backups in AWS](https://docs.aws.amazon.com/aws-backup/latest/devguide/encryption.html)
- [Managing Encrypted Tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/encryption.tutorial.html)
- [Security Pillar - AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- [ What is AWS Elastic Disaster Recovery? ](https://docs.aws.amazon.com/drs/latest/userguide/what-is-drs.html)
- [FSISEC11: How are you protecting against ransomware?](https://docs.aws.amazon.com/wellarchitected/latest/financial-services-industry-lens/fsisec11.html)
- [ Ransomware Risk Management on AWS Using the NIST Cyber Security Framework ](https://docs.aws.amazon.com/whitepapers/latest/ransomware-risk-management-on-aws-using-nist-csf/welcome.html)
- [Building cyber resiliency with AWS Backup logically air-gapped vault](https://aws.amazon.com/blogs/storage/building-cyber-resiliency-with-aws-backup-logically-air-gapped-vault/)
- [Validate recovery readiness with AWS Backup restore testing](https://aws.amazon.com/blogs/storage/validate-recovery-readiness-with-aws-backup-restore-testing/)
- [Improve recovery resilience with AWS Backup support for Multi-party approval](https://aws.amazon.com/blogs/storage/improve-recovery-resilience-with-aws-backup-support-for-multi-party-approval/)
### Related Examples
- [ Implementing Bi-Directional Cross-Region Replication (CRR) for Amazon S3 ](https://wellarchitectedlabs.com/reliability/200_labs/200_bidirectional_replication_for_s3/)
