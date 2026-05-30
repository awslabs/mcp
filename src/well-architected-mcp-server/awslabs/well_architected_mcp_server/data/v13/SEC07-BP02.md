---
id: "SEC07-BP02"
title: "Apply data protection controls based on data sensitivity"
framework: "WAF"
domain: "Security"
capability: "How do you classify your data?"
risk_level: "High"
---

# SEC07-BP02 Apply data protection controls based on data sensitivity

## Desired Outcome
You have a classification policy that defines the different levels of sensitivity for data in your organization.  For each of these sensitivity levels, you have clear guidelines published for approved storage and handling services and locations, and their required configuration.  You implement the controls for each level according to the level of protection required and their associated costs.  You have monitoring and alerting in place to detect if data is present in unauthorized locations, processed in unauthorized environments, accessed by unauthorized actors, or the configuration of related services becomes non-compliant.

## Anti-Patterns
- Applying the same level of protection controls across all data. This may lead to over-provisioning security controls for low-sensitivity data, or insufficient protection of highly sensitive data.
- Not involving relevant stakeholders from security, compliance, and business teams when defining data protection controls.
- Overlooking the operational overhead and costs associated with implementing and maintaining data protection controls.
- Not conducting periodic data protection control reviews to maintain alignment with classification policies.
- Not having a complete inventory of where data resides at rest and in transit.

## Implementation Guidance
 Implementing data protection controls based on data sensitivity levels involves several key steps. First, identify the different data sensitivity levels within your workload architecture (such as public, internal, confidential, and restricted) and evaluate where you store and process this data. Next, define isolation boundaries around data based on its sensitivity level. We recommend you separate data into different AWS accounts, using [service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html) (SCPs) to restrict services and actions allowed for each data sensitivity level. This way, you can create strong isolation boundaries and enforce the principle of least privilege.

 After you define the isolation boundaries, implement appropriate protection controls based on the data sensitivity levels. Refer to best practices for [Protecting data at rest](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/protecting-data-at-rest.html) and [Protecting data in transit](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/protecting-data-in-transit.html) to implement relevant controls like encryption, access controls, and auditing. Consider techniques like tokenization or anonymization to reduce the sensitivity level of your data. Simplify applying consistent data policies across your business with a centralized system for tokenization and de-tokenization.

 Continuously monitor and test the effectiveness of the implemented controls. Regularly review and update the data classification scheme, risk assessments, and protection controls as your organization's data landscape and threats evolve. Align the implemented data protection controls with relevant industry regulations, standards, and legal requirements. Further, provide security awareness and training to help employees understand the data classification scheme and their responsibilities in handling and protecting sensitive data.

## Implementation Steps
1.  Identify the classification and sensitivity levels of data within your workload.

1.  Define isolation boundaries for each level and determine an enforcement strategy.

1.  Evaluate the controls you define that govern access, encryption, auditing, retention, and others required by your data classification policy.

1.  Evaluate options to reduce the sensitivity level of data where appropriate, such as using tokenization or anonymization.

1.  Verify your controls using automated testing and monitoring of your configured resources.

## Resources
### Related Best Practices
- [PERF03-BP01 Use a purpose-built data store that best supports your data access and storage requirements](https://docs.aws.amazon.com/wellarchitected/latest/framework/perf_data_use_purpose_built_data_store.html)
- [COST04-BP05 Enforce data retention policies](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost_decomissioning_resources_data_retention.html)
### Related Documents
- [Data Classification whitepaper](https://docs.aws.amazon.com/whitepapers/latest/data-classification/data-classification.html)
- [Best Practices for Security, Identify, & Compliance](https://aws.amazon.com/architecture/security-identity-compliance/?cards-all.sort-by=item.additionalFields.sortDate&cards-all.sort-order=desc&awsf.content-type=*all&awsf.methodology=*all)
- [AWS KMS Best Practices](https://docs.aws.amazon.com/kms/latest/developerguide/best-practices.html)
- [Encryption best practices and features for AWS services](https://docs.aws.amazon.com/prescriptive-guidance/latest/encryption-best-practices/welcome.html)
### Related Examples
- [Building a serverless tokenization solution to mask sensitive data](https://aws.amazon.com/blogs/compute/building-a-serverless-tokenization-solution-to-mask-sensitive-data/)
- [How to use tokenization to improve data security and reduce audit scope](https://aws.amazon.com/blogs/security/how-to-use-tokenization-to-improve-data-security-and-reduce-audit-scope/)
### Related Tools
- [AWS Key Management Service (AWS KMS)](https://aws.amazon.com/kms/)
- [AWS CloudHSM](https://aws.amazon.com/cloudhsm/)
- [AWS Organizations](https://aws.amazon.com/organizations/)
