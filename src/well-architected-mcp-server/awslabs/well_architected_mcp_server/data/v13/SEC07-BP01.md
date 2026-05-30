---
id: "SEC07-BP01"
title: "Understand your data classification scheme"
framework: "WAF"
domain: "Security"
capability: "How do you classify your data?"
risk_level: "High"
---

# SEC07-BP01 Understand your data classification scheme

## Desired Outcome
The types of data present in your workload are well-understood and documented.  Appropriate controls are in place to protect sensitive data based on its classification.  These controls govern considerations such as who is allowed to access the data and for what purpose, where the data is stored, the encryption policy for that data and how encryption keys are managed, the lifecycle for the data and its retention requirements, appropriate destruction processes, what backup and recovery processes are in place, and the auditing of access.

## Anti-Patterns
- Not having a formal data classification policy in place to define data sensitivity levels and their handling requirements
- Not having a good understanding of the sensitivity levels of data within your workload, and not capturing this information in architecture and operations documentation
- Failing to apply the appropriate controls around your data based on its sensitivity and requirements, as outlined in your data classification and handling policy
- Failing to provide feedback about data classification and handling requirements to owners of the policies.

## Implementation Guidance
 When designing a workload, you may be considering ways to protect sensitive data intuitively.  For example, in a multi-tenant application, it is intuitive to think of each tenant's data as sensitive and put protections in place so that one tenant can't access the data of another tenant.  Likewise, you may intuitively design access controls so only administrators can modify data while other users have only read-level access or no access at all.

 By having these data sensitivity levels defined and captured in policy, along with their data protection requirements, you can formally identify what data resides in your workload. You can then determine if the right controls are in place, if the controls can be audited, and what responses are appropriate if data is found to be mishandled.

 To help identify where sensitive data resides within your workload, consider using a data catalog. A data catalog is a database that maps data in your organization, its location, sensitivity level, and the controls in place to protect that data. Additionally, consider using [resource tags](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html) where available.  For example, you can apply a tag that has a *tag key* of `Classification` and a *tag value* of `PHI` for protected health information (PHI), and another tag that has a *tag key* of `Sensitivity` and a *tag value* of `High`.  Services such as [AWS Config](https://aws.amazon.com/config/) can then be used to monitor these resources for changes and alert if they are modified in a way that brings them out of compliance with your protection requirements (such as changing the encryption settings).  You can capture the standard definition of your tag keys and acceptable values using [tag policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html), a feature of AWS Organizations. It is not recommended that the tag key or value contains private or sensitive data.

## Implementation Steps
1.  Understand your organization's data classification scheme and protection requirements.

1.  Identify the types of sensitive data processed by your workloads.

1.  Capture the data in a data catalog that provides a single view of where data resides in the organization and the level of sensitivity of that data.

1.  Consider using resource and data-level tagging, where available, to tag data with its sensitivity level and other operational metadata that can help with monitoring and incident response.

   1.   AWS Organizations tag policies can be used to enforce tagging standards.

## Resources
### Related Best Practices
- [SUS04-BP01 Implement a data classification policy](https://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_data_a2.html)
### Related Documents
- [Data Classification whitepaper](https://docs.aws.amazon.com/whitepapers/latest/data-classification/data-classification-overview.html)
- [Best Practices for Tagging AWS Resources](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html)
### Related Examples
- [AWS Organizations Tag Policy Syntax and Examples](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_example-tag-policies.html)
### Related Tools
- [AWS Tag Editor](https://docs.aws.amazon.com/tag-editor/latest/userguide/tag-editor.html)
