---
id: "OPS07-BP05"
title: "Make informed decisions to deploy systems and changes"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you know that you are ready to support a workload?"
risk_level: "Low"
effort: "Medium"
---

# OPS07-BP05 Make informed decisions to deploy systems and changes

## Desired Outcome
- You make informed decisions when deploying changes to your workload.
- Changes comply with governance.

## Anti-Patterns
- Deploying a change to our workload without a process to handle a failed deployment.
- Making changes to your production environment that are out of compliance with governance requirements.
- Deploying a new version of your workload without establishing a baseline for resource utilization.

## Implementation Guidance
 Use pre-mortems to develop processes for unsuccessful changes. Document your processes for unsuccessful changes. Ensure that all changes comply with governance. Evaluate the benefits and risks to deploying changes to your workload.

 **Customer example**

 AnyCompany Retail regularly conducts pre-mortems to validate their processes for unsuccessful changes. They document their processes in a shared Wiki and update it frequently. All changes comply with governance requirements.

## Implementation Steps
1.  Make informed decisions when deploying changes to your workload. Establish and review criteria for a successful deployment. Develop scenarios or criteria that would initiate a rollback of a change. Weigh the benefits of deploying changes against the risks of an unsuccessful change.

1.  Verify that all changes comply with governance policies.

1.  Use pre-mortems to plan for unsuccessful changes and document mitigation strategies. Run a table-top exercise to model an unsuccessful change and validate roll-back procedures.

## Resources
### Related Best Practices
- [OPS01-BP03 Evaluate governance requirements](ops_priorities_governance_reqs.md) - Governance requirements are a key factor in determining whether to deploy a change.
- [OPS06-BP01 Plan for unsuccessful changes](ops_mit_deploy_risks_plan_for_unsucessful_changes.md) - Establish plans to mitigate a failed deployment and use pre-mortems to validate them.
- [OPS06-BP02 Test deployments](ops_mit_deploy_risks_test_val_chg.md) - Every software change should be properly tested before deployment in order to reduce defects in production.
- [OPS07-BP01 Ensure personnel capability](ops_ready_to_support_personnel_capability.md) - Having enough trained personnel to support the workload is essential to making an informed decision to deploy a system change.
### Related Documents
- [ Amazon Web Services: Risk and Compliance ](https://docs.aws.amazon.com/whitepapers/latest/aws-risk-and-compliance/welcome.html)
- [AWS Shared Responsibility Model ](https://aws.amazon.com/compliance/shared-responsibility-model/)
- [ Governance in the AWS Cloud: The Right Balance Between Agility and Safety ](https://aws.amazon.com/blogs/apn/governance-in-the-aws-cloud-the-right-balance-between-agility-and-safety/)
