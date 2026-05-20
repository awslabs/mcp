---
id: "SEC06-BP05"
title: "Automate compute protection"
framework: "WAF"
domain: "Security"
capability: "How do you protect your compute resources?"
risk_level: "Medium"
---

# SEC06-BP05 Automate compute protection

## Desired Outcome
Automated systems perform all scanning and patching of compute resources. You use automated verification to check that software images and dependencies come from trusted sources, and have not been tampered with. Workloads are automatically checked for up-to-date dependencies, and are signed to establish trustworthiness in AWS compute environments.  Automated remediations are initiated when non-compliant resources are detected.

## Anti-Patterns
- Following the practice of immutable infrastructure, but not having a solution in place for emergency patching or replacement of production systems.
- Using automation to fix misconfigured resources, but not having a manual override mechanism in place.  Situations may arise where you need to adjust the requirements, and you may need to suspend automations until you make these changes.

## Implementation Guidance
 You can apply the automations described in the Security Pillar practices for protecting your compute resources. [SEC06-BP01 Perform vulnerability management](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_protect_compute_vulnerability_management.html) describes how you can use [Amazon Inspector](https://aws.amazon.com/inspector/) in both your CI/CD pipelines and for continually scanning your runtime environments for known Common Vulnerabilities and Exposures (CVEs).  You can use [AWS Systems Manager](https://aws.amazon.com/systems-manager/) to apply patches or redeploy from fresh images through automated runbooks to keep your compute fleet updated with the latest software and libraries.  Use these techniques to reduce the need for manual processes and interactive access to your compute resources.  See [SEC06-BP03 Reduce manual management and interactive access](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_protect_compute_reduce_manual_management.html) to learn more.

 Automation also plays a role in deploying workloads that are trustworthy, described in [SEC06-BP02 Provision compute from hardened images](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_protect_compute_hardened_images.html) and [SEC06-BP04 Validate software integrity](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_protect_compute_validate_software_integrity.html).  You can use services such as [EC2 Image Builder](https://aws.amazon.com/image-builder/), [AWS Signer](https://docs.aws.amazon.com/signer/latest/developerguide/Welcome.html), [AWS CodeArtifact](https://aws.amazon.com/codeartifact/), and [Amazon Elastic Container Registry (ECR)](https://aws.amazon.com/ecr/) to download, verify, construct, and store hardened and approved images and code dependencies.   Alongside Inspector, each of these can play a role in your CI/CD process so your workload makes its way to production only when it is confirmed that its dependencies are up-to-date and from trusted sources.  Your workload is also signed so AWS compute environments, such as [AWS Lambda](https://aws.amazon.com/lambda/) and [Amazon Elastic Kubernetes Service (EKS)](https://aws.amazon.com/eks/) can verify it hasn't been tampered with before allowing it to run.

 Beyond these preventative controls, you can use automation in your detective controls for your compute resources as well.  As one example, [AWS Security Hub](https://aws.amazon.com/security-hub/) offers the [NIST 800-53 Rev. 5](https://docs.aws.amazon.com/securityhub/latest/userguide/nist-standard.html) standard that includes checks such as [[EC2.8] EC2 instances should use Instance Metadata Service Version 2 (IMDSv2)](https://docs.aws.amazon.com/securityhub/latest/userguide/ec2-controls.html#ec2-8).  IMDSv2 uses the techniques of session authentication, blocking requests that contain an X-Forwarded-For HTTP header, and a network TTL of 1 to stop traffic originating from external sources to retrieve information about the EC2 instance. This check in Security Hub can detect when EC2 instances use IMDSv1 and initiate automated remediation. Learn more about automated detection and remediations in [SEC04-BP04 Initiate remediation for non-compliant resources](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_detect_investigate_events_noncompliant_resources.html).

## Implementation Steps
1.  Automate creating secure, compliant and hardened AMIs with [EC2 Image Builder](https://docs.aws.amazon.com/imagebuilder/latest/userguide/integ-compliance-products.html).  You can produce images that incorporate controls from the Center for Internet Security (CIS) Benchmarks or Security Technical Implementation Guide (STIG) standards from base AWS and APN partner images.

1.  Automate configuration management. Enforce and validate secure configurations in your compute resources automatically by using a configuration management service or tool.

   1.  Automated configuration management using [AWS Config](https://aws.amazon.com/config/)

   1.  Automated security and compliance posture management using [AWS Security Hub](https://aws.amazon.com/security-hub/)

1.  Automate patching or replacing Amazon Elastic Compute Cloud (Amazon EC2) instances. AWS Systems Manager Patch Manager automates the process of patching managed instances with both security-related and other types of updates. You can use Patch Manager to apply patches for both operating systems and applications.

   1.  [AWS Systems Manager Patch Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-patch.html)

1.  Automate scanning of compute resources for common vulnerabilities and exposures (CVEs), and embed security scanning solutions within your build pipeline.

   1.  [Amazon Inspector](https://aws.amazon.com/inspector/)

   1.  [ECR Image Scanning](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)

1.  Consider Amazon GuardDuty for automatic malware and threat detection to protect compute resources. GuardDuty can also identify potential issues when an [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html) function gets invoked in your AWS environment.

   1.  [Amazon GuardDuty](https://aws.amazon.com/guardduty/)

1.  Consider AWS Partner solutions. AWS Partners offer industry-leading products that are equivalent, identical to, or integrate with existing controls in your on-premises environments. These products complement the existing AWS services to allow you to deploy a comprehensive security architecture and a more seamless experience across your cloud and on-premises environments.

   1.  [Infrastructure security](https://aws.amazon.com/security/partner-solutions/#infrastructure_security)

## Resources
### Related Best Practices
- [SEC01-BP06 Automate deployment of standard security controls](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_automate_security_controls.html)
### Related Documents
- [Get the full benefits of IMDSv2 and disable IMDSv1 across your AWS infrastructure](https://aws.amazon.com/blogs/security/get-the-full-benefits-of-imdsv2-and-disable-imdsv1-across-your-aws-infrastructure/)
### Related Videos
- [Security best practices for the Amazon EC2 instance metadata service](https://youtu.be/2B5bhZzayjI)
