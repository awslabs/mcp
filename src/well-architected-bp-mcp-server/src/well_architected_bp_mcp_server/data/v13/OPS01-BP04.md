---
id: "OPS01-BP04"
title: "Evaluate compliance requirements"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you determine what your priorities are?"
risk_level: "High"
effort: "Medium"
---

# OPS01-BP04 Evaluate compliance requirements

## Desired Outcome
- Regulatory, industry, and internal compliance requirements are incorporated into architectural selection.
- You can validate compliance and generate audit reports.

## Anti-Patterns
- Parts of your workload fall under the Payment Card Industry Data Security Standard (PCI-DSS) framework but your workload stores credit cards data unencrypted.
- Your software developers and architects are unaware of the compliance framework that your organization must adhere to.
- The yearly Systems and Organizations Control (SOC2) Type II audit is happening soon and you are unable to verify that controls are in place.

## Implementation Guidance
 Implementing this best practice means that you incorporate compliance requirements into your architecture design process. Your team members are aware of the required compliance framework. You validate compliance in line with the framework.

 **Customer example**

 AnyCompany Retail stores credit card information for customers. Developers on the card storage team understand that they need to comply with the PCI-DSS framework. They’ve taken steps to verify that credit card information is stored and accessed securely in line with the PCI-DSS framework. Every year they work with their security team to validate compliance.

## Implementation Steps
1.  Work with your security and governance teams to determine what industry, regulatory, or internal compliance frameworks that your workload must adhere to. Incorporate the compliance frameworks into your workload.

   1.  Validate continual compliance of AWS resources with services like [AWS Compute Optimizer](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html) and [AWS Security Hub](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html).

1.  Educate your team members on the compliance requirements so they can operate and evolve the workload in line with them. Compliance requirements should be included in architectural and technological choices.

1.  Depending on the compliance framework, you may be required to generate an audit or compliance report. Work with your organization to automate this process as much as possible.

   1.  Use services like [AWS Audit Manager](https://docs.aws.amazon.com/audit-manager/latest/userguide/what-is.html) to validate compliance and generate audit reports.

   1.  You can download AWS security and compliance documents with [AWS Artifact](https://docs.aws.amazon.com/artifact/latest/ug/what-is-aws-artifact.html).

## Resources
### Related Best Practices
- [SEC01-BP03 Identify and validate control objectives](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_control_objectives.html) - Security control objectives are an important part of overall compliance.
- [SEC01-BP06 Automate testing and validation of security controls in pipelines](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_test_validate_pipeline.html) - As part of your pipelines, validate security controls. You can also generate compliance documentation for new changes.
- [SEC07-BP02 Define data protection controls](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_data_classification_define_protection.html) - Many compliance frameworks have data handling and storage policies based.
- [SEC10-BP03 Prepare forensic capabilities](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_incident_response_prepare_forensic.html) - Forensic capabilities can sometimes be used in auditing compliance.
### Related Documents
- [AWS Compliance Center ](https://aws.amazon.com/financial-services/security-compliance/compliance-center/)
- [AWS Compliance Resources ](https://aws.amazon.com/compliance/resources/)
- [AWS Risk and Compliance Whitepaper ](https://docs.aws.amazon.com/whitepapers/latest/aws-risk-and-compliance/welcome.html)
- [AWS Shared Responsibility Model ](https://aws.amazon.com/compliance/shared-responsibility-model/)
- [AWS services in scope by compliance programs ](https://aws.amazon.com/compliance/services-in-scope/)
### Related Videos
- [AWS re:Invent 2020: Achieve compliance as code using AWS Compute Optimizer](https://www.youtube.com/watch?v=m8vTwvbzOfw)
- [AWS re:Invent 2021 - Cloud compliance, assurance, and auditing ](https://www.youtube.com/watch?v=pdrYGVgb08Y)
- [AWS Summit ATL 2022 - Implementing compliance, assurance, and auditing on AWS (COP202) ](https://www.youtube.com/watch?v=i7XrWimhqew)
### Related Examples
- [ PCI DSS and AWS Foundational Security Best Practices on AWS](https://aws.amazon.com/solutions/partners/compliance-pci-fsbp-remediation/)
### Related Services
- [AWS Artifact](https://docs.aws.amazon.com/artifact/latest/ug/what-is-aws-artifact.html)
- [AWS Audit Manager](https://docs.aws.amazon.com/audit-manager/latest/userguide/what-is.html)
- [AWS Compute Optimizer](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)
- [AWS Security Hub](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)
