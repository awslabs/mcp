---
id: "OPS01-BP03"
title: "Evaluate governance requirements"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How do you determine what your priorities are?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_governance_reqs.html"
description: "Governance is the set of policies, rules, or frameworks that a company uses to achieve its business goals. Governance requirements are generated from within your organization. They can affect the types of technologies you choose or influence the way you operate your workload. Incorporate organizational governance requirements into your workload. Conformance is the ability to demonstrate that you have implemented governance requirements."
area: ["Organization", "Organization priorities"]
relatedIds: ["OPS01-BP04"]
---

# OPS01-BP03 Evaluate governance requirements

Governance is the set of policies, rules, or frameworks that a company uses to
achieve its business goals. Governance requirements are generated from within your
organization. They can affect the types of technologies you choose or influence the
way you operate your workload. Incorporate organizational governance requirements
into your workload. Conformance is the ability to demonstrate that you have implemented
governance requirements.

**Desired outcome:**

- Governance requirements are incorporated into the architectural design and operation of your workload.
- You can provide proof that you have followed governance requirements.
- Governance requirements are regularly reviewed and updated.

**Common anti-patterns:**

- Your organization mandates that the root account has multi-factor authentication. You failed to implement this requirement and the root account is compromised.
- During the design of your workload, you choose an instance type that is not approved by the IT department. You are unable to launch your workload and must conduct a redesign.
- You are required to have a disaster recovery plan. You did not create one and your workload suffers an extended outage.
- Your team wants to use new instances but your governance requirements have not been updated to allow them.

**Benefits of establishing this best
practice:**

- Following governance requirements aligns your workload with larger organization policies.
- Governance requirements reflect industry standards and best practices for your organization.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Identify governance requirement by working with stakeholders and
governance organizations. Include governance requirements into your
workload. Be able to demonstrate proof that you’ve followed governance
requirements.

**Customer example**

At AnyCompany Retail, the cloud operations team works with stakeholders
across the organization to develop governance requirements. For example,
they prohibit SSH access into Amazon EC2 instances. If teams need system access,
they are required to use AWS Systems Manager Session Manager. The cloud
operations team regularly updates governance requirements as new services
become available.

**Implementation steps**

- Identify the stakeholders for your workload, including any centralized teams.
- Work with stakeholders to identify governance requirements.
- Once you’ve generated a list, prioritize the improvement items, and begin implementing them into your workload.

Use services like [AWS Config](https://aws.amazon.com/blogs/industries/best-practices-for-aws-organizations-service-control-policies-in-a-multi-account-environment/) to create governance-as-code and validate that governance requirements are followed.
- If you use [AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html), you can leverage Service Control Policies to implement governance requirements.

- Provide documentation that validates the implementation.

**Level of effort for the implementation plan:** Medium. Implementing missing governance requirements
may result in rework of your workload.

## Resources

**Related best practices:**

- [OPS01-BP04 Evaluate compliance requirements](./ops_priorities_compliance_reqs.html) - Compliance is like governance but comes from outside an organization.

**Related documents:**

- [AWS Management and Governance Cloud Environment Guide](https://docs.aws.amazon.com/wellarchitected/latest/management-and-governance-guide/management-and-governance-cloud-environment-guide.html)
- [Best Practices for AWS Organizations Service Control Policies in a Multi-Account Environment](https://aws.amazon.com/blogs/industries/best-practices-for-aws-organizations-service-control-policies-in-a-multi-account-environment/)
- [Governance in the AWS Cloud: The Right Balance Between Agility and Safety](https://aws.amazon.com/blogs/apn/governance-in-the-aws-cloud-the-right-balance-between-agility-and-safety/)
- [What is Governance, Risk, And Compliance (GRC)?](https://aws.amazon.com/what-is/grc/)

**Related videos:**

- [AWS Management and Governance: Configuration, Compliance, and Audit - AWS Online Tech Talks](https://www.youtube.com/watch?v=79ud1ZAaoj0)
- [AWS re:Inforce 2019: Governance for the Cloud Age (DEM12-R1)](https://www.youtube.com/watch?v=y3WmHnavuN8)
- [AWS re:Invent 2020: Achieve compliance as code using AWS Config](https://www.youtube.com/watch?v=m8vTwvbzOfw)
- [AWS re:Invent 2020: Agile governance on AWS GovCloud (US)](https://www.youtube.com/watch?v=hv6B17eriHQ)

**Related examples:**

- [AWS Config Conformance Pack Samples](https://docs.aws.amazon.com/config/latest/developerguide/conformancepack-sample-templates.html)

**Related services:**

- [AWS Config](https://aws.amazon.com/config/)
- [AWS Organizations - Service Control Policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)
