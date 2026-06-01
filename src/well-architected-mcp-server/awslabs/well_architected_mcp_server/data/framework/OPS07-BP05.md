---
id: "OPS07-BP05"
title: "Make informed decisions to deploy systems and changes"
pillar: "Operational Excellence"
risk_level: "LOW"
capability: "How do you know that you are ready to support a workload?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_informed_deploy_decisions.html"
description: "Have processes in place for successful and unsuccessful changes to your workload. A pre-mortem is an exercise where a team simulates a failure to develop mitigation strategies. Use pre-mortems to anticipate failure and create procedures where appropriate. Evaluate the benefits and risks of deploying changes to your workload. Verify that all changes comply with governance."
area: ["Prepare", "Operational readiness and change management"]
relatedIds: ["OPS01-BP03", "OPS06-BP01", "OPS06-BP02", "OPS07-BP01"]
---

# OPS07-BP05 Make informed decisions to deploy systems and changes

Have processes in place for successful and unsuccessful changes to your workload. A pre-mortem is an exercise where a team simulates a failure to develop mitigation strategies. Use pre-mortems to anticipate failure and create procedures where appropriate. Evaluate the benefits and risks of deploying changes to your workload. Verify that all changes comply with governance.

**Desired outcome:**

- You make informed decisions when deploying changes to your workload.
- Changes comply with governance.

**Common anti-patterns:**

- Deploying a change to our workload without a process to handle a failed deployment.
- Making changes to your production environment that are out of compliance with governance requirements.
- Deploying a new version of your workload without establishing a baseline for resource utilization.

**Benefits of establishing this best
practice:**

- You are prepared for unsuccessful changes to your workload.
- Changes to your workload are compliant with governance policies.

**Level of risk exposed if this best practice
is not established:** Low

## Implementation guidance

Use pre-mortems to develop processes for unsuccessful changes. Document your processes for unsuccessful changes. Ensure that all changes comply with governance. Evaluate the benefits and risks to deploying changes to your workload.

**Customer example**

AnyCompany Retail regularly conducts pre-mortems to validate their processes for unsuccessful changes. They document their processes in a shared Wiki and update it frequently. All changes comply with governance requirements.

**Implementation steps**

- Make informed decisions when deploying changes to your workload. Establish and review criteria for a successful deployment. Develop scenarios or criteria that would initiate a rollback of a change. Weigh the benefits of deploying changes against the risks of an unsuccessful change.
- Verify that all changes comply with governance policies.
- Use pre-mortems to plan for unsuccessful changes and document mitigation strategies. Run a table-top exercise to model an unsuccessful change and validate roll-back procedures.

**Level of effort for the implementation plan:** Moderate. Implementing a practice of pre-mortems requires coordination and effort from stakeholders across your organization

## Resources

**Related best practices:**

- [OPS01-BP03 Evaluate governance requirements](./ops_priorities_governance_reqs.html) - Governance requirements are a key factor in determining whether to deploy a change.
- [OPS06-BP01 Plan for unsuccessful changes](./ops_mit_deploy_risks_plan_for_unsucessful_changes.html) - Establish plans to mitigate a failed deployment and use pre-mortems to validate them.
- [OPS06-BP02 Test deployments](./ops_mit_deploy_risks_test_val_chg.html) - Every software change should be properly tested before deployment in order to reduce defects in production.
- [OPS07-BP01 Ensure personnel capability](./ops_ready_to_support_personnel_capability.html) - Having enough trained personnel to support the workload is essential to making an informed decision to deploy a system change.

**Related documents:**

- [Amazon Web Services: Risk and Compliance](https://docs.aws.amazon.com/whitepapers/latest/aws-risk-and-compliance/welcome.html)
- [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/)
- [Governance in the AWS Cloud: The Right Balance Between Agility and Safety](https://aws.amazon.com/blogs/apn/governance-in-the-aws-cloud-the-right-balance-between-agility-and-safety/)
