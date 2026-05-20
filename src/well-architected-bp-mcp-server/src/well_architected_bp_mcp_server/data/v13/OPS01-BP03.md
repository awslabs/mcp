---
id: "OPS01-BP03"
title: "Evaluate governance requirements"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you determine what your priorities are?"
risk_level: "High"
effort: "Medium"
---

# OPS01-BP03 Evaluate governance requirements

## Desired Outcome
- Governance requirements are incorporated into the architectural design and operation of your workload.
- You can provide proof that you have followed governance requirements.
- Governance requirements are regularly reviewed and updated.

## Anti-Patterns
- Your organization mandates that the root account has multi-factor authentication. You failed to implement this requirement and the root account is compromised.
- During the design of your workload, you choose an instance type that is not approved by the IT department. You are unable to launch your workload and must conduct a redesign.
- You are required to have a disaster recovery plan. You did not create one and your workload suffers an extended outage.
- Your team wants to use new instances but your governance requirements have not been updated to allow them.

## Implementation Guidance
Identify governance requirement by working with stakeholders and governance organizations. Include governance requirements into your workload. Be able to demonstrate proof that you’ve followed governance requirements.

 **Customer example**

 At AnyCompany Retail, the cloud operations team works with stakeholders across the organization to develop governance requirements. For example, they prohibit SSH access into Amazon EC2 instances. If teams need system access, they are required to use AWS Systems Manager Session Manager. The cloud operations team regularly updates governance requirements as new services become available.

## Implementation Steps
1.  Identify the stakeholders for your workload, including any centralized teams.

1.  Work with stakeholders to identify governance requirements.

1.  Once you’ve generated a list, prioritize the improvement items, and begin implementing them into your workload.

   1.  Use services like [AWS Config](https://aws.amazon.com/blogs/industries/best-practices-for-aws-organizations-service-control-policies-in-a-multi-account-environment/) to create governance-as-code and validate that governance requirements are followed.

   1.  If you use [AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html), you can leverage Service Control Policies to implement governance requirements.

1.  Provide documentation that validates the implementation.

## Resources
### Related Best Practices
- [OPS01-BP04 Evaluate compliance requirements](ops_priorities_compliance_reqs.md) - Compliance is like governance but comes from outside an organization.
### Related Documents
- [AWS Management and Governance Cloud Environment Guide ](https://docs.aws.amazon.com/wellarchitected/latest/management-and-governance-guide/management-and-governance-cloud-environment-guide.html)
- [ Best Practices for AWS Organizations Service Control Policies in a Multi-Account Environment ](https://aws.amazon.com/blogs/industries/best-practices-for-aws-organizations-service-control-policies-in-a-multi-account-environment/)
- [ Governance in the AWS Cloud: The Right Balance Between Agility and Safety ](https://aws.amazon.com/blogs/apn/governance-in-the-aws-cloud-the-right-balance-between-agility-and-safety/)
- [ What is Governance, Risk, And Compliance (GRC)? ](https://aws.amazon.com/what-is/grc/)
### Related Videos
- [AWS Management and Governance: Configuration, Compliance, and Audit - AWS Online Tech Talks ](https://www.youtube.com/watch?v=79ud1ZAaoj0)
- [AWS re:Inforce 2019: Governance for the Cloud Age (DEM12-R1) ](https://www.youtube.com/watch?v=y3WmHnavuN8)
- [AWS re:Invent 2020: Achieve compliance as code using AWS Config](https://www.youtube.com/watch?v=m8vTwvbzOfw)
- [AWS re:Invent 2020: Agile governance on AWS GovCloud (US)](https://www.youtube.com/watch?v=hv6B17eriHQ)
### Related Examples
- [AWS Config Conformance Pack Samples ](https://docs.aws.amazon.com/config/latest/developerguide/conformancepack-sample-templates.html)
### Related Services
- [AWS Config](https://aws.amazon.com/config/)
- [AWS Organizations - Service Control Policies ](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)
