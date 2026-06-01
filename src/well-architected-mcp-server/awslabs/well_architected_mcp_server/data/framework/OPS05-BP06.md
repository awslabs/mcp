---
id: "OPS05-BP06"
title: "Share design standards"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How do you reduce defects, ease remediation, and improve flow into production?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_dev_integ_share_design_stds.html"
description: "Share best practices across teams to increase awareness and maximize the benefits of development efforts. Document them and keep them up to date as your architecture evolves. If shared standards are enforced in your organization, it’s critical that mechanisms exist to request additions, changes, and exceptions to standards. Without this option, standards become a constraint on innovation."
area: ["Prepare", "Design for operations"]
relatedIds: ["OPS01-BP03", "OPS01-BP04", "OPS07-BP02", "OPS11-BP01", "OPS11-BP04"]
---

# OPS05-BP06 Share design standards

Share best practices across teams to increase awareness and maximize the benefits of development efforts. Document them and keep them up to date as your architecture evolves. If shared standards are enforced in your organization, it’s critical that mechanisms exist to request additions, changes, and exceptions to standards. Without this option, standards become a constraint on innovation.

**Desired outcome:** Design standards are shared across teams in your organizations. They are documented and kept up-to-date as best practices evolve.

**Common anti-patterns:**

- Two development teams have each created a user authentication service. Your users must maintain a separate set of credentials for each part of the system they want to access.
- Each team manages their own infrastructure. A new compliance requirement forces a change to your infrastructure and each team implements it in a different way.

**Benefits of establishing this best
practice:** Using shared standards supports the adoption of best practices and maximizes the benefits of development efforts. Documenting and updating design standards keeps your organization up-to-date with best practices and security and compliance requirements.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Share existing best practices, design standards, checklists, operating procedures, guidance, and governance requirements across teams. Have procedures to request changes, additions, and exceptions to design standards to support improvement and innovation. Make teams are aware of published content. Have a mechanism to keep design standards up-to-date as new best practices emerge.

**Customer example**

AnyCompany Retail has a cross-functional architecture team that creates software architecture patterns. This team builds the architecture with compliance and governance built in. Teams that adopt these shared standards get the benefits of having compliance and governance built in. They can quickly build on top of the design standard. The architecture team meets quarterly to evaluate architecture patterns and update them if necessary.

### Implementation steps

- Identify a cross-functional team that owns developing and updating design standards. This team should work with stakeholders across your organization to develop design standards, operating procedures, checklists, guidance, and governance requirements. Document the design standards and share them within your organization.

[AWS Service Catalog](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/introduction.html) can be used to create portfolios representing design standards using infrastructure as code. You can share portfolios across accounts.

- Have a mechanism in place to keep design standards up-to-date as new best practices are identified.
- If design standards are centrally enforced, have a process to request changes, updates, and exemptions.

**Level of effort for the implementation plan:** Medium. Developing a process to create and share design standards can take coordination and cooperation with stakeholders across your organization.

## Resources

**Related best practices:**

- [OPS01-BP03 Evaluate governance requirements](./ops_priorities_governance_reqs.html) - Governance requirements influence design standards.
- [OPS01-BP04 Evaluate compliance requirements](./ops_priorities_compliance_reqs.html) - Compliance is a vital input in creating design standards.
- [OPS07-BP02 Ensure a consistent review of operational readiness](./ops_ready_to_support_const_orr.html) - Operational readiness checklists are a mechanism to implement design standards when designing your workload.
- [OPS11-BP01 Have a process for continuous improvement](./ops_evolve_ops_process_cont_imp.html) - Updating design standards is a part of continuous improvement.
- [OPS11-BP04 Perform knowledge management](./ops_evolve_ops_knowledge_management.html) - As part of your knowledge management practice, document and share design standards.

**Related documents:**

- [Automate AWS Backups with AWS Service Catalog](https://aws.amazon.com/blogs/mt/automate-aws-backups-with-aws-service-catalog/)
- [AWS Service Catalog Account Factory-Enhanced](https://aws.amazon.com/blogs/mt/aws-service-catalog-account-factory-enhanced/)
- [How Expedia Group built Database as a Service (DBaaS) offering using AWS Service Catalog](https://aws.amazon.com/blogs/mt/how-expedia-group-built-database-as-a-service-dbaas-offering-using-aws-service-catalog/)
- [Maintain visibility over the use of cloud architecture patterns](https://aws.amazon.com/blogs/architecture/maintain-visibility-over-the-use-of-cloud-architecture-patterns/)
- [Simplify sharing your AWS Service Catalog portfolios in an AWS Organizations setup](https://aws.amazon.com/blogs/mt/simplify-sharing-your-aws-service-catalog-portfolios-in-an-aws-organizations-setup/)

**Related videos:**

- [AWS Service Catalog – Getting Started](https://www.youtube.com/watch?v=A9kKy6WhqVA)
- [AWS re:Invent 2020: Manage your AWS Service Catalog portfolios like an expert](https://www.youtube.com/watch?v=lVfXkWHAtR8)

**Related examples:**

- [AWS Service Catalog Reference Architecture](https://github.com/aws-samples/aws-service-catalog-reference-architectures)
- [AWS Service Catalog Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/d40750d7-a330-49be-9945-cde864610de9/en-US)

**Related services:**

- [AWS Service Catalog](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/introduction.html)
