---
id: "COST05-BP01"
title: "Identify organization requirements for cost"
pillar: "Cost Optimization"
risk_level: "HIGH"
capability: "How do you evaluate cost when you select services?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_select_service_requirements.html"
---

# COST05-BP01 Identify organization requirements for cost

Work with team members to define the balance between cost
optimization and other pillars, such as performance and reliability,
for this workload.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

In most organizations, the information technology (IT) department is comprised of multiple small teams, each with its own agenda and focus area, that reflects the specialisies and skills of its team members. You need to understand your organization’s overall objectives, priorities, goals and how each department or project contributes to these objectives. Categorizing all essential resources, including personnel, equipment, technology, materials, and external services, is crucial for achieving organizational objectives and comprehensive budget planning. Adopting this systematic approach to cost identification and understanding is fundamental for establishing a realistic and robust cost plan for the organization.

When selecting services for your workload, it is key that you understand your organization priorities. Create a balance between cost optimization and other AWS Well-Architected Framework pillars, such as performance and reliability. This process should be conducted systematically and regularly to reflect changes in the organization's objectives, market conditions, and operational dynamics. A fully cost-optimized workload is the solution that is most aligned to your organization’s requirements, not necessarily the lowest cost. Meet with all teams in your organization, such as product, business, technical, and finance to collect information. Evaluate the impact of tradeoffs between competing interests or alternative approaches to help make informed decisions when determining where to focus efforts or choosing a course of action.

For example, accelerating speed to market for new features may be emphasized over cost optimization, or you may choose a relational database for non-relational data to simplify the effort to migrate a system, rather than migrating to a database optimized for your data type and updating your application.

### Implementation steps

- **Identify organization requirements for cost:** Meet with team members from your organization, including those in product management, application owners, development and operational teams, management, and financial roles. Prioritize the Well-Architected pillars for this workload and its components. The output should be a list of the pillars in order. You can also add a weight to each pillar to indicate how much additional focus it has, or how similar the focus is between two pillars.
- **Address the technical debt and document it:** During the workload review, address the technical debt. Document a backlog item to revisit the workload in the future, with the goal of refactoring or re-architecting to optimize it further. It's essential to clearly communicate the trade-offs that were made to other stakeholders.

## Resources

**Related best practices:**

- REL11-BP07 Architect your product to meet availability targets and uptime service level agreements (SLAs)
- OPS01-BP06 Evaluate tradeoffs

**Related documents:**

- [AWS Total Cost of Ownership (TCO) Calculator](https://aws.amazon.com/tco-calculator/)
- [Amazon S3 storage classes](https://aws.amazon.com/s3/storage-classes/)
- [Cloud
products](https://aws.amazon.com/products/)
