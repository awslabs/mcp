---
id: "OPS02-BP04"
title: "Mechanisms exist to manage responsibilities and ownership"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you structure your organization to support your business outcomes?"
risk_level: "High"
effort: "Medium"
---

# OPS02-BP04 Mechanisms exist to manage responsibilities and ownership

## Desired Outcome
Teams within your organization have clearly-defined responsibilities that include how they are related to resources, actions to be performed, processes, and procedures. These responsibilities align to the team's responsibilities and goals, as well as the responsibilities of other teams. You document the routes of escalation in a consistent and discoverable manner and feed these decisions into documentation artifacts, such as responsibility matrices, team definitions, or wiki pages.

## Anti-Patterns
- The responsibilities of the team are ambiguous or poorly-defined.
- The team does not align roles with responsibilities.
- The team does not align its goals and objectives its responsibilities, which makes it difficult to measure success.
- Team member responsibilities do not align with the team and the wider organization.
- Your team does not keep responsibilities up-to-date, which makes them inconsistent with the tasks performed by the team.
- Escalation paths for determining responsibilities aren't defined or are unclear.
- Escalation paths have no single thread owner to ensure timely reponse.
- Roles, responsibilities, and escalation paths are not discoverable, and they are not readily available when required (for example, in response to an incident).

## Implementation Guidance
 Identify team members roles and responsibilities, and verify that they understand the expectations of their role. Make this information discoverable so that members of your organization can identify who they need to contact for specific needs, whether it's a team or individual. As organizations seek to capitalize on the opportunities to migrate and modernize on AWS, roles and responsibilities might also change. Keep your teams and their members aware of their responsibilities, and train them appropriately to carry out their tasks during this change.

 Determine the role or team that should receive escalations to identify responsibility and ownership. This team can engage with various stakeholders to come to a decision. However, they should own the management of the decision making process.

 Provide accessible mechanisms for members of your organization to discover and identify ownership and responsibility. These mechanisms teach them who to contact for specific needs.

 **Customer example**

 AnyCompany Retail recently completed a migration of workloads from an on-premises environment to their landing zone in AWS with a lift and shift approach. They performed an operations review to reflect on how they accomplish common operational tasks and verified that their existing responsibility matrix reflects operations in the new environment. When they migrated from on-premises to AWS, they reduced the infrastructure teams responsibilities relating to the hardware and physical infrastructure. This move also revealed new opportunities to evolve the operating model for their workloads.

 While they identified, addressed, and documented the majority of responsibilities, they also defined escalation routes for any responsibilities that were missed or that may need to change as operations practices evolve. To explore new opportunities to standardize and improve efficiency across your workloads, provide access to operations tools like AWS Systems Manager and security tools like AWS Security Hub and Amazon GuardDuty. AnyCompany Retail puts together a review of responsibilities and strategy based on improvements they wants to address first. As the company adopts new ways of working and technology patterns, they update their responsibility matrix to match.

## Implementation Steps
1.  Start with existing documentation. Some typical source documents might include:

   1.  Responsibility or responsible, accountable, consulted, and informed (RACI) matrices

   1.  Team definitions or wiki pages

   1.  Service definitions and offerings

   1.  Role or job descriptions

1.  Review and host discussions on the documented responsibilities:

   1.  Review with teams to identify misalignments between documented responsibilities and responsibilities the team typically performs.

   1.  Discuss potential services offered by internal customers to identify gaps in expectations between teams.

1.  Analysis and address the discrepancies.

1.  Identify opportunities for improvement.

   1.  Identify frequently-requested, resource-intensive requests, which are typically strong candidates for improvement.

   1.  Look for best practices, understand patterns, follow prescriptive guidance, and simplify and standardize improvements.

   1.  Record improvement opportunities, and track them to completion.

1.  If a team doesn't already hold responsibility for managing and tracking the assignment of responsibilities, identify someone on the team to hold this responsibility.

1.  Define a process for teams to request clarification of responsibility.

   1.  Review the process, and verify that it is clear and simple to use.

   1.  Make sure that someone owns and tracks escalations to their conclusion.

   1.  Establish operational metrics to measure effectiveness.

   1.  Create a feedback mechanisms to verify that teams can highlight improvement opportunities.

   1.  Implement a mechanism for periodic review.

1.  Document in a discoverable and accessible location.

   1.  Wikis or documentation portal are common choices.

## Resources
### Related Best Practices
- [OPS01-BP06 Evaluate tradeoffs](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_eval_tradeoffs.html)
- [OPS03-BP02 Team members are empowered to take action when outcomes are at risk](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_culture_team_emp_take_action.html)
- [OPS03-BP03 Escalation is encouraged](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_culture_team_enc_escalation.html)
- [OPS03-BP07 Resource teams appropriately](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_culture_team_res_appro.html)
- [OPS09-BP01 Measure operations goals and KPIs with metrics](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_operations_health_measure_ops_goals_kpis.html)
- [OPS09-BP03 Review operations metrics and prioritize improvement](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_operations_health_review_ops_metrics_prioritize_improvement.html)
- [OPS11-BP01 Have a process for continuous improvement](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_process_cont_imp.html)
### Related Documents
- [AWS Whitepaper - Introduction to DevOps on AWS](https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/automation.html)
- [AWS Whitepaper - AWS Cloud Adoption Framework: Operations Perspective](https://docs.aws.amazon.com/whitepapers/latest/aws-caf-operations-perspective/aws-caf-operations-perspective.html)
- [AWS Well-Architected Framework Operational Excellence - Workload level Operating model topologies](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/operating-model-2-by-2-representations.html)
- [AWS Prescriptive Guidance - Building your Cloud Operating Model](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-cloud-operating-model/welcome.html)
- [AWS Prescriptive Guidance - Create a RACI or RASCI matrix for a cloud operating model](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/create-a-raci-or-rasci-matrix-for-a-cloud-operating-model.html)
- [AWS Cloud Operations & Migrations Blog - Delivering Business Value with Cloud Platform Teams](https://aws.amazon.com/blogs/mt/delivering-business-value-with-cloud-platform-teams/)
- [AWS Cloud Operations & Migrations Blog - Why a Cloud Operating Model?](https://aws.amazon.com/blogs/mt/why-a-cloud-operating-model/)
- [AWS DevOps Blog - How organizations are modernizing for cloud operations](https://aws.amazon.com/blogs/devops/how-organizations-are-modernizing-for-cloud-operations/)
### Related Videos
- [AWS Summit Online - Cloud Operating Models for Accelerated Transformation](https://www.youtube.com/watch?v=ksJ5_UdYIag)
- [AWS re:Invent 2023 - Future-proofing cloud security: A new operating model](https://www.youtube.com/watch?v=GFcKCz1VO2I)
