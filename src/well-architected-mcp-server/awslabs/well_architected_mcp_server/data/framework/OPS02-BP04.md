---
id: "OPS02-BP04"
title: "Mechanisms exist to manage responsibilities and ownership"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How do you structure your organization to support your business outcomes?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ops_model_def_responsibilities_ownership.html"
description: "Understand the responsibilities of your role and how you contribute to business outcomes, as this understanding informs the prioritization of your tasks and why your role is important. This helps team members recognize needs and respond appropriately. When team members know their role, they can establish ownership, identify improvement opportunities, and understand how to influence or make appropriate changes."
area: ["Organization", "Operating model", "Relationships and ownership"]
relatedIds: ["OPS02-BP06", "OPS03-BP02", "OPS03-BP03", "OPS03-BP07", "OPS09-BP01", "OPS09-BP03", "OPS11-BP01"]
---

# OPS02-BP04 Mechanisms exist to manage responsibilities and ownership

Understand the responsibilities of your role and how you contribute
to business outcomes, as this understanding informs the
prioritization of your tasks and why your role is important. This
helps team members recognize needs and respond appropriately. When
team members know their role, they can establish ownership, identify
improvement opportunities, and understand how to influence or make
appropriate changes.

Occasionally, a responsibility might not have a clear owner. In
these situations, design a mechanism to resolve this gap. Create a
well-defined escalation path to someone with the authority to assign
ownership or plan to address the need.

**Desired outcome:** Teams within
your organization have clearly-defined responsibilities that include
how they are related to resources, actions to be performed,
processes, and procedures. These responsibilities align to the
team's responsibilities and goals, as well as the responsibilities
of other teams. You document the routes of escalation in a
consistent and discoverable manner and feed these decisions into
documentation artifacts, such as responsibility matrices, team
definitions, or wiki pages.

**Common anti-patterns:**

- The responsibilities of the team are ambiguous or
poorly-defined.
- The team does not align roles with responsibilities.
- The team does not align its goals and objectives its
responsibilities, which makes it difficult to measure success.
- Team member responsibilities do not align with the team and the
wider organization.
- Your team does not keep responsibilities up-to-date, which makes
them inconsistent with the tasks performed by the team.
- Escalation paths for determining responsibilities aren't defined
or are unclear.
- Escalation paths have no single thread owner to ensure timely
reponse.
- Roles, responsibilities, and escalation paths are not
discoverable, and they are not readily available when required
(for example, in response to an incident).

**Benefits of establishing this best
practice:**

- When you understand who has responsibility or ownership, you can
contact the proper team or team member to make a request or
transition a task.
- To reduce the risk of inaction and unaddressed needs, you have
identified a person who has the authority to assign
responsibility or ownership.
- When you clearly define the scope of a responsibility, your team
members gain autonomy and ownership.
- Your responsibilities inform the decisions you make, the actions
you take, and your handoff activities to their proper owners.
- It's easy to identify abandoned responsibilities because you
have a clear understanding of what falls outside of your team's
responsibility, which helps you escalate for clarification.
- Teams avoid confusion and tension, and they can more adequately
manage their workloads and resources.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Identify team members roles and responsibilities, and verify that
they understand the expectations of their role. Make this
information discoverable so that members of your organization can
identify who they need to contact for specific needs, whether it's
a team or individual. As organizations seek to capitalize on the
opportunities to migrate and modernize on AWS, roles and
responsibilities might also change. Keep your teams and their
members aware of their responsibilities, and train them
appropriately to carry out their tasks during this change.

Determine the role or team that should receive escalations to
identify responsibility and ownership. This team can engage with
various stakeholders to come to a decision. However, they should
own the management of the decision making process.

Provide accessible mechanisms for members of your organization to
discover and identify ownership and responsibility. These
mechanisms teach them who to contact for specific needs.

**Customer example**

AnyCompany Retail recently completed a migration of workloads from
an on-premises environment to their landing zone in AWS with a
lift and shift approach. They performed an operations review to
reflect on how they accomplish common operational tasks and
verified that their existing responsibility matrix reflects
operations in the new environment. When they migrated from
on-premises to AWS, they reduced the infrastructure teams
responsibilities relating to the hardware and physical
infrastructure. This move also revealed new opportunities to
evolve the operating model for their workloads.

While they identified, addressed, and documented the majority of
responsibilities, they also defined escalation routes for any
responsibilities that were missed or that may need to change as
operations practices evolve. To explore new opportunities to
standardize and improve efficiency across your workloads, provide
access to operations tools like AWS Systems Manager and security
tools like AWS Security Hub CSPM and Amazon GuardDuty. AnyCompany
Retail puts together a review of responsibilities and strategy
based on improvements they wants to address first. As the company
adopts new ways of working and technology patterns, they update
their responsibility matrix to match.

### Implementation steps

- Start with existing documentation. Some typical source
documents might include:

Responsibility or responsible, accountable, consulted,
and informed (RACI) matrices
- Team definitions or wiki pages
- Service definitions and offerings
- Role or job descriptions

- Review and host discussions on the documented
responsibilities:

Review with teams to identify misalignments between
documented responsibilities and responsibilities the
team typically performs.
- Discuss potential services offered by internal customers
to identify gaps in expectations between teams.

- Analysis and address the discrepancies.
- Identify opportunities for improvement.

Identify frequently-requested, resource-intensive
requests, which are typically strong candidates for
improvement.
- Look for best practices, understand patterns, follow prescriptive
guidance, and simplify and standardize improvements.
- Record improvement opportunities, and track them to
completion.

- If a team doesn't already hold responsibility for managing
and tracking the assignment of responsibilities, identify
someone on the team to hold this responsibility.
- Define a process for teams to request clarification of
responsibility.

Review the process, and verify that it is clear and
simple to use.
- Make sure that someone owns and tracks escalations to
their conclusion.
- Establish operational metrics to measure effectiveness.
- Create a feedback mechanisms to verify that teams can
highlight improvement opportunities.
- Implement a mechanism for periodic review.

- Document in a discoverable and accessible location.

Wikis or documentation portal are common choices.

**Level of effort for the implementation
plan:** Medium

## Resources

**Related best practices:**

- [OPS01-BP06
Evaluate tradeoffs](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_eval_tradeoffs.html)
- [OPS03-BP02
Team members are empowered to take action when outcomes are at
risk](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_culture_team_emp_take_action.html)
- [OPS03-BP03
Escalation is encouraged](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_culture_team_enc_escalation.html)
- [OPS03-BP07
Resource teams appropriately](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_culture_team_res_appro.html)
- [OPS09-BP01
Measure operations goals and KPIs with metrics](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_operations_health_measure_ops_goals_kpis.html)
- [OPS09-BP03
Review operations metrics and prioritize improvement](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_operations_health_review_ops_metrics_prioritize_improvement.html)
- [OPS11-BP01
Have a process for continuous improvement](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_process_cont_imp.html)

**Related documents:**

- [AWS Whitepaper - Introduction to DevOps on AWS](https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/automation.html)
- [AWS Whitepaper - AWS Cloud Adoption Framework: Operations
Perspective](https://docs.aws.amazon.com/whitepapers/latest/aws-caf-operations-perspective/aws-caf-operations-perspective.html)
- [AWS Well-Architected Framework Operational Excellence - Workload
level Operating model topologies](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/operating-model-2-by-2-representations.html)
- [AWS Prescriptive Guidance - Building your Cloud Operating
Model](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-cloud-operating-model/welcome.html)
- [AWS Prescriptive Guidance - Create a RACI or RASCI matrix for a
cloud operating model](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/create-a-raci-or-rasci-matrix-for-a-cloud-operating-model.html)
- [AWS Cloud Operations & Migrations Blog - Delivering Business
Value with Cloud Platform Teams](https://aws.amazon.com/blogs/mt/delivering-business-value-with-cloud-platform-teams/)
- [AWS Cloud Operations & Migrations Blog - Why a Cloud Operating
Model?](https://aws.amazon.com/blogs/mt/why-a-cloud-operating-model/)
- [AWS DevOps Blog - How organizations are modernizing for cloud
operations](https://aws.amazon.com/blogs/devops/how-organizations-are-modernizing-for-cloud-operations/)

**Related videos:**

- [AWS Summit Online - Cloud Operating Models for Accelerated
Transformation](https://www.youtube.com/watch?v=ksJ5_UdYIag)
- [AWS re:Invent 2023 - Future-proofing cloud security: A new
operating model](https://www.youtube.com/watch?v=GFcKCz1VO2I)
