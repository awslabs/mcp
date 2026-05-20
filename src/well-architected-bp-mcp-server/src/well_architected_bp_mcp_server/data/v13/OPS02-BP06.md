---
id: "OPS02-BP06"
title: "Responsibilities between teams are predefined or negotiated"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you structure your organization to support your business outcomes?"
risk_level: "Low"
effort: "Medium"
---

# OPS02-BP06 Responsibilities between teams are predefined or negotiated

## Desired Outcome
- Inter-team working or support agreements are agreed to and documented.
- Teams that support or work with each other have defined communication channels and response expectations.

## Anti-Patterns
- An issue occurs in production and two separate teams start troubleshooting independent of each other. Their siloed efforts extend the outage.
- The operations team needs assistance from the development team but there is no agreed to response time. The request is stuck in the backlog.

## Implementation Guidance
 Implementing this best practice means that there is no ambiguity about how teams work with each other. Formal agreements codify how teams work together or support each other. Inter-team communication channels are documented.

 **Customer example**

 AnyCompany Retail’s SRE team has a service level agreement with their development team. Whenever the development team makes a request in their ticketing system, they can expect a response within fifteen minutes. If there is a site outage, the SRE team takes lead in the investigation with support from the development team.

## Implementation Steps
1.  Working with stakeholders across your organization, develop agreements between teams based on processes and procedures.

   1.  If a process or procedure is shared between two teams, develop a runbook on how the teams will work together.

   1.  If there are dependencies between teams, agree to a response SLA for requests.

1.  Document responsibilities in your knowledge management system.

## Resources
### Related Best Practices
- [OPS02-BP02 Processes and procedures have identified owners](ops_ops_model_def_proc_owners.md) - Process ownership must be identified before setting agreements between teams.
- [OPS02-BP03 Operations activities have identified owners responsible for their performance](ops_ops_model_def_activity_owners.md) - Operations activities ownership must be identified before setting agreements between teams.
### Related Documents
- [AWS Executive Insights - Empowering Innovation with the Two-Pizza Team ](https://aws.amazon.com/executive-insights/content/amazon-two-pizza-team/)
- [ Introduction to DevOps on AWS - Two-Pizza Teams ](https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/two-pizza-teams.html)
