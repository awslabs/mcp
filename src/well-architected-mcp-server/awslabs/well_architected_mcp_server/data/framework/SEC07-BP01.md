---
id: "SEC07-BP01"
title: "Understand your data classification scheme"
pillar: "Security"
risk_level: "HIGH"
capability: "How do you classify your data?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_data_classification_identify_data.html"
---

# SEC07-BP01 Understand your data classification scheme

Understand the classification of data your workload is processing,
its handling requirements, the associated business processes, where
the data is stored, and who the data owner is.  Your data
classification and handling scheme should consider the applicable
legal and compliance requirements of your workload and what data
controls are needed. Understanding the data is the first step in the
data classification journey.

**Desired outcome:** The types of
data present in your workload are well-understood and documented.
Appropriate controls are in place to protect sensitive data based
on its classification.  These controls govern considerations such as
who is allowed to access the data and for what purpose, where the
data is stored, the encryption policy for that data and how
encryption keys are managed, the lifecycle for the data and its
retention requirements, appropriate destruction processes, what
backup and recovery processes are in place, and the auditing of
access.

**Common anti-patterns:**

- Not having a formal data classification policy in place to
define data sensitivity levels and their handling requirements
- Not having a good understanding of the sensitivity levels of
data within your workload, and not capturing this information in
architecture and operations documentation
- Failing to apply the appropriate controls around your data based
on its sensitivity and requirements, as outlined in your data
classification and handling policy
- Failing to provide feedback about data classification and
handling requirements to owners of the policies.

**Benefits of establishing this best practice:** This practice removes ambiguity around the appropriate
handling of data within your workload.  Applying a formal policy
that defines the sensitivity levels of data in your organization and
their required protections can help you comply with legal
regulations and other cybersecurity attestations and certifications.
Workload owners can have confidence in knowing where sensitive data
is stored and what protection controls are in place.  Capturing
these in documentation helps new team members better understand them
and maintain controls early in their tenure. These practices can
also help reduce costs by right sizing the controls for each type of
data.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

When designing a workload, you may be considering ways to protect
sensitive data intuitively.  For example, in a multi-tenant
application, it is intuitive to think of each tenant's data as
sensitive and put protections in place so that one tenant can't
access the data of another tenant.  Likewise, you may intuitively
design access controls so only administrators can modify data
while other users have only read-level access or no access at all.

By having these data sensitivity levels defined and captured in
policy, along with their data protection requirements, you can
formally identify what data resides in your workload. You can then
determine if the right controls are in place, if the controls can
be audited, and what responses are appropriate if data is found to
be mishandled.

To help identify where sensitive data resides within your
workload, consider using a data catalog. A data catalog is a
database that maps data in your organization, its location,
sensitivity level, and the controls in place to protect that data.
Additionally, consider using
[resource
tags](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html) where available.  For example, you can apply a tag
that has a *tag key* of
Classification and a *tag
value* of PHI for protected health
information (PHI), and another tag that has a *tag
key* of Sensitivity and a
*tag value* of High.
Services such as
[AWS Config](https://aws.amazon.com/config/) can then be used to monitor these resources for
changes and alert if they are modified in a way that brings them
out of compliance with your protection requirements (such as
changing the encryption settings).  You can capture the standard
definition of your tag keys and acceptable values using
[tag
policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html), a feature of AWS Organizations. It is not
recommended that the tag key or value contains private or
sensitive data.

### Implementation steps

- Understand your organization's data classification scheme and
protection requirements.
- Identify the types of sensitive data processed by your
workloads.
- Capture the data in a data catalog that provides a single
view of where data resides in the organization and the level
of sensitivity of that data.
- Consider using resource and data-level tagging, where
available, to tag data with its sensitivity level and other
operational metadata that can help with monitoring and
incident response.

AWS Organizations tag policies can be used to enforce
tagging standards.

## Resources

**Related best practices:**

- [SUS04-BP01
Implement a data classification policy](https://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_data_a2.html)

**Related documents:**

- [Data
Classification whitepaper](https://docs.aws.amazon.com/whitepapers/latest/data-classification/data-classification-overview.html)
- [Best
Practices for Tagging AWS Resources](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html)

**Related examples:**

- [AWS Organizations Tag Policy Syntax and Examples](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_example-tag-policies.html)

**Related tools**

- [AWS Tag Editor](https://docs.aws.amazon.com/tag-editor/latest/userguide/tag-editor.html)
