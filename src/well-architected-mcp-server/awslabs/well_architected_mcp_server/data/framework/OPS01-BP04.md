---
id: "OPS01-BP04"
title: "Evaluate compliance requirements"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How do you determine what your priorities are?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_compliance_reqs.html"
description: "Regulatory, industry, and internal compliance requirements are an important driver for defining your organization’s priorities. Your compliance framework may preclude you from using specific technologies or geographic locations. Apply due diligence if no external compliance frameworks are identified. Generate audits or reports that validate compliance."
area: ["Organization", "Organization priorities"]
relatedIds: ["SEC01-BP03", "SEC01-BP06", "SEC07-BP02", "SEC10-BP03"]
---

# OPS01-BP04 Evaluate compliance requirements

Regulatory, industry, and internal compliance requirements are an important driver for defining
your organization’s priorities. Your compliance framework may preclude you from using specific
technologies or geographic locations. Apply due diligence if no external compliance frameworks are
identified. Generate audits or reports that validate compliance.

If you advertise that your product meets specific compliance standards, you must have an internal process for ensuring continuous compliance. Examples of compliance standards include PCI DSS, FedRAMP, and HIPAA. Applicable compliance standards are determined by various factors, such as what types of data the solution stores or transmits and which geographic regions the solution supports.

**Desired outcome:**

- Regulatory, industry, and internal compliance requirements are incorporated into architectural selection.
- You can validate compliance and generate audit reports.

**Common anti-patterns:**

- Parts of your workload fall under the Payment Card Industry Data Security Standard (PCI-DSS) framework but your workload stores credit cards data unencrypted.
- Your software developers and architects are unaware of the compliance framework that your organization must adhere to.
- The yearly Systems and Organizations Control (SOC2) Type II audit is happening soon and you are unable to verify that controls are in place.

**Benefits of establishing this best
practice:**

- Evaluating and understanding the compliance requirements that apply to your workload will inform how you prioritize your efforts to deliver business value.
- You choose the right locations and technologies that are congruent with your compliance framework.
- Designing your workload for auditability helps you to prove you are adhering to your compliance framework.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Implementing this best practice means that you incorporate compliance requirements into your architecture design process. Your team members are aware of the required compliance framework. You validate compliance in line with the framework.

**Customer example**

AnyCompany Retail stores credit card information for customers. Developers on the card storage team understand that they need to comply with the PCI-DSS framework. They’ve taken steps to verify that credit card information is stored and accessed securely in line with the PCI-DSS framework. Every year they work with their security team to validate compliance.

**Implementation steps**

- Work with your security and governance teams to determine what industry, regulatory, or internal compliance frameworks that your workload must adhere to. Incorporate the compliance frameworks into your workload.

Validate continual compliance of AWS resources with services like
[AWS Compute Optimizer](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)
and [AWS Security Hub CSPM](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html).

- Educate your team members on the compliance requirements so they can operate and evolve the workload in line with them. Compliance requirements should be included in architectural and technological choices.
- Depending on the compliance framework, you may be required to generate an audit or compliance report. Work with your organization to automate this process as much as possible.

Use services like [AWS Audit Manager](https://docs.aws.amazon.com/audit-manager/latest/userguide/what-is.html) to validate compliance and generate audit reports.
- You can download AWS security and compliance documents with [AWS Artifact](https://docs.aws.amazon.com/artifact/latest/ug/what-is-aws-artifact.html).

**Level of effort for the implementation plan:** Medium. Implementing compliance frameworks can be challenging. Generating audit reports or compliance documents adds additional complexity.

## Resources

**Related best practices:**

- [SEC01-BP03 Identify and validate control objectives](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_control_objectives.html) - Security control objectives are an important part of overall compliance.
- [SEC01-BP06 Automate testing and validation of security controls in pipelines](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_test_validate_pipeline.html) - As part of your pipelines, validate security controls. You can also generate compliance documentation for new changes.
- [SEC07-BP02 Define data protection controls](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_data_classification_define_protection.html) - Many compliance frameworks have data handling and storage policies based.
- [SEC10-BP03 Prepare forensic capabilities](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_incident_response_prepare_forensic.html) - Forensic capabilities can sometimes be used in auditing compliance.

**Related documents:**

- [AWS Compliance Center](https://aws.amazon.com/financial-services/security-compliance/compliance-center/)
- [AWS Compliance Resources](https://aws.amazon.com/compliance/resources/)
- [AWS Risk and Compliance Whitepaper](https://docs.aws.amazon.com/whitepapers/latest/aws-risk-and-compliance/welcome.html)
- [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/)
- [AWS services in scope by compliance programs](https://aws.amazon.com/compliance/services-in-scope/)

**Related videos:**

- [AWS re:Invent 2020: Achieve compliance as code using AWS Compute Optimizer](https://www.youtube.com/watch?v=m8vTwvbzOfw)
- [AWS re:Invent 2021 - Cloud compliance, assurance, and auditing](https://www.youtube.com/watch?v=pdrYGVgb08Y)
- [AWS Summit ATL 2022 - Implementing compliance, assurance, and auditing on AWS (COP202)](https://www.youtube.com/watch?v=i7XrWimhqew)

**Related examples:**

- [PCI DSS and AWS Foundational Security Best Practices on AWS](https://aws.amazon.com/solutions/partners/compliance-pci-fsbp-remediation/)

**Related services:**

- [AWS Artifact](https://docs.aws.amazon.com/artifact/latest/ug/what-is-aws-artifact.html)
- [AWS Audit Manager](https://docs.aws.amazon.com/audit-manager/latest/userguide/what-is.html)
- [AWS Compute Optimizer](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)
- [AWS Security Hub CSPM](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)
