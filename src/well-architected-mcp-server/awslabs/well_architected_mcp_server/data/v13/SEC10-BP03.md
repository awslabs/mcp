---
id: "SEC10-BP03"
title: "Prepare forensic capabilities"
framework: "WAF"
domain: "Security"
capability: "How do you anticipate, respond to, and recover from incidents?"
risk_level: "Medium"
---

# SEC10-BP03 Prepare forensic capabilities

## Implementation Guidance
 Concepts from traditional on-premises forensics apply to AWS. For key information to start building forensics capabilities in the AWS Cloud, see [Forensic investigation environment strategies in the AWS Cloud](https://aws.amazon.com/blogs/security/forensic-investigation-environment-strategies-in-the-aws-cloud/).

 Once you have your environment and AWS account structure set up for forensics, define the technologies required to effectively perform forensically sound methodologies across the four phases:
- **Collection:** Collect relevant AWS logs, such as AWS CloudTrail, AWS Config, VPC Flow Logs, and host-level logs. Collect snapshots, backups, and memory dumps of impacted AWS resources where available.
- **Examination:** Examine the data collected by extracting and assessing the relevant information.
- **Analysis:** Analyze the data collected in order to understand the incident and draw conclusions from it.
- **Reporting:** Present the information resulting from the analysis phase.

## Implementation Steps
 **Prepare your forensics environment**

 [AWS Organizations](https://aws.amazon.com/organizations/) helps you centrally manage and govern an AWS environment as you grow and scale AWS resources. An AWS organization consolidates your AWS accounts so that you can administer them as a single unit. You can use organizational units (OUs) to group accounts together to administer as a single unit.

 For incident response, it’s helpful to have an AWS account structure that supports the functions of incident response, which includes a *security OU* and a *forensics OU*. Within the security OU, you should have accounts for:
- **Log archival:** Aggregate logs in a log archival AWS account with limited permissions.
- **Security tools:** Centralize security services in a security tool AWS account. This account operates as the delegated administrator for security services.

 Within the forensics OU, you have the option to implement a single forensics account or accounts for each Region that you operate in, depending on which works best for your business and operational model. If you create a forensics account per Region, you can block the creation of AWS resources outside of that Region and reduce the risk of resources being copied to an unintended region. For example, if you only operate in US East (N. Virginia) Region (`us-east-1`) and US West (Oregon) (`us-west-2`), then you would have two accounts in the forensics OU: one for `us-east-1` and one for `us-west-2`.

 You can create a forensics AWS account for multiple Regions. You should exercise caution in copying AWS resources to that account to verify you’re aligning with your data sovereignty requirements. Because it takes time to provision new accounts, it is imperative to create and instrument the forensics accounts well ahead of an incident so that responders can be prepared to effectively use them for response.

 The following diagram displays a sample account structure including a forensics OU with per-Region forensics accounts:

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/region-account-structure.png)

 **Capture backups and snapshots**

 Setting up backups of key systems and databases are critical for recovering from a security incident and for forensics purposes. With backups in place, you can restore your systems to their previous safe state. On AWS, you can take snapshots of various resources. Snapshots provide you with point-in-time backups of those resources. There are many AWS services that can support you in backup and recovery. For detail on these services and approaches for backup and recovery, see [Backup and Recovery Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/backup-recovery/services.html) and [Use backups to recover from security incidents](https://aws.amazon.com/blogs/security/use-backups-to-recover-from-security-incidents/).

 Especially when it comes to situations such as ransomware, it’s critical for your backups to be well protected. For guidance on securing your backups, see [Top 10 security best practices for securing backups in AWS](https://aws.amazon.com/blogs/security/top-10-security-best-practices-for-securing-backups-in-aws/). In addition to securing your backups, you should regularly test your backup and restore processes to verify that the technology and processes you have in place work as expected.

 **Automate forensics**

 During a security event, your incident response team must be able to collect and analyze evidence quickly while maintaining accuracy for the time period surrounding the event (such as capturing logs related to a specific event or resource or collecting memory dump of an Amazon EC2 instance). It’s both challenging and time consuming for the incident response team to manually collect the relevant evidence, especially across a large number of instances and accounts. Additionally, manual collection can be prone to human error. For these reasons, you should develop and implement automation for forensics as much as possible.

 AWS offers a number of automation resources for forensics, which are listed in the following Resources section. These resources are examples of forensics patterns that we have developed and customers have implemented. While they might be a useful reference architecture to start with, consider modifying them or creating new forensics automation patterns based on your environment, requirements, tools, and forensics processes.

## Resources
### Related Documents
- [AWS Security Incident Response Guide - Develop Forensics Capabilities ](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/develop-forensics-capabilities.html)
- [AWS Security Incident Response Guide - Forensics Resources ](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/appendix-b-incident-response-resources.html#forensic-resources)
- [Forensic investigation environment strategies in the AWS Cloud](https://aws.amazon.com/blogs/security/forensic-investigation-environment-strategies-in-the-aws-cloud/)
- [How to automate forensic disk collection in AWS](https://aws.amazon.com/blogs/security/how-to-automate-forensic-disk-collection-in-aws/)
- [AWS Prescriptive Guidance - Automate incident response and forensics ](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/automate-incident-response-and-forensics.html)
### Related Videos
- [ Automating Incident Response and Forensics ](https://www.youtube.com/watch?v=f_EcwmmXkXk)
### Related Examples
- [ Automated Incident Response and Forensics Framework ](https://github.com/awslabs/aws-automated-incident-response-and-forensics)
- [ Automated Forensics Orchestrator for Amazon EC2 ](https://docs.aws.amazon.com/solutions/latest/automated-forensics-orchestrator-for-amazon-ec2/welcome.html)
