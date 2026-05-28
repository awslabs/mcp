---
id: "OPS07-BP06"
title: "Create support plans for production workloads"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you know that you are ready to support a workload?"
risk_level: "Low"
effort: "Low"
---

# OPS07-BP06 Create support plans for production workloads

## Desired Outcome
- Implement support plans for software and services that production workloads rely on.
- Choose an appropriate support plan based on service-level needs.
- Document the support plans, support levels, and how to request support.

## Anti-Patterns
- You have no support plan for a critical software vendor. Your workload is impacted by them and you can do nothing to expedite a fix or get timely updates from the vendor.
- A developer that was the primary point of contact for a software vendor left the company. You are not able to reach the vendor support directly. You must spend time researching and navigating generic contact systems, increasing the time required to respond when needed.
- A production outage occurs with a software vendor. There is no documentation on how to file a support case.

## Implementation Guidance
 Enable support plans for any software and services vendors that your production workload relies on. Set up appropriate support plans to meet service-level needs. For AWS customers, this means activating AWS Business Support or greater on any accounts where you have production workloads. Meet with support vendors on a regular cadence to get updates about support offerings, processes, and contacts. Document how to request support from software and services vendors, including how to escalate if there is an outage. Implement mechanisms to keep support contacts up to date.

 **Customer example**

 At AnyCompany Retail, all commercial software and services dependencies have support plans. For example, they have AWS Enterprise Support activated on all accounts with production workloads. Any developer can raise a support case when there is an issue. There is a wiki page with information on how to request support, whom to notify, and best practices for expediting a case.

## Implementation Steps
1.  Work with stakeholders in your organization to identify software and services vendors that your workload relies on. Document these dependencies.

1.  Determine service-level needs for your workload. Select a support plan that aligns with them.

1.  For commercial software and services, establish a support plan with the vendors.

   1.  Subscribing to AWS Business Support or greater for all production accounts provides faster response time from AWS Support and strongly recommended. If you don’t have premium support, you must have an action plan to handle issues, which require help from AWS Support. AWS Support provides a mix of tools and technology, people, and programs designed to proactively help you optimize performance, lower costs, and innovate faster. In addition, AWS Business Support provides additional benefits, including API access to AWS Trusted Advisor and AWS Health for programmatic integration with your systems, alongside other access methods like the AWS Management Console and Amazon EventBridge channels.

1.  Document the support plan in your knowledge management tool. Include how to request support, who to notify if a support case is filed, and how to escalate during an incident. A wiki is a good mechanism to allow anyone to make necessary updates to documentation when they become aware of changes to support processes or contacts.

## Resources
### Related Best Practices
- [OPS02-BP02 Processes and procedures have identified owners](ops_ops_model_def_proc_owners.md)
### Related Documents
- [AWS Support Plans ](https://docs.aws.amazon.com/awssupport/latest/user/aws-support-plans.html)
### Related Services
- [AWS Business Support ](https://aws.amazon.com/premiumsupport/plans/business/)
- [AWS Enterprise Support ](https://aws.amazon.com/premiumsupport/plans/enterprise/)
