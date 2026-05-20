---
id: "OPS07-BP02"
title: "Ensure a consistent review of operational readiness"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you know that you are ready to support a workload?"
risk_level: "High"
effort: "High"
---

# OPS07-BP02 Ensure a consistent review of operational readiness

## Desired Outcome
You have an ORR checklist with best practices for your organization. ORRs are conducted before workloads launch. ORRs are run periodically over the course of the workload lifecycle.

## Anti-Patterns
- You launch a workload without knowing if you can operate it.
- Governance and security requirements are not included in certifying a workload for launch.
- Workloads are not re-evaluated periodically.
- Workloads launch without required procedures in place.
- You see repetition of the same root cause failures in multiple workloads.

## Implementation Guidance
 An ORR is two things: a process and a checklist. Your ORR process should be adopted by your organization and supported by an executive sponsor. At a minimum, ORRs must be conducted before a workload launches to general availability. Run the ORR throughout the software development lifecycle to keep it up to date with best practices or new requirements. The ORR checklist should include configuration items, security and governance requirements, and best practices from your organization. Over time, you can use services, such as [AWS Config](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html), [AWS Security Hub](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html), and [AWS Control Tower Guardrails](https://docs.aws.amazon.com/controltower/latest/userguide/guardrails.html), to build best practices from the ORR into guardrails for automatic detection of best practices.

 **Customer example**

 After several production incidents, AnyCompany Retail decided to implement an ORR process. They built a checklist composed of best practices, governance and compliance requirements, and lessons learned from outages. New workloads conduct ORRs before they launch. Every workload conducts a yearly ORR with a subset of best practices to incorporate new best practices and requirements that are added to the ORR checklist. Over time, AnyCompany Retail used [AWS Config](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html) to detect some best practices, speeding up the ORR process.

## Implementation Steps
 To learn more about ORRs, read the [Operational Readiness Reviews (ORR) whitepaper](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/wa-operational-readiness-reviews.html). It provides detailed information on the history of the ORR process, how to build your own ORR practice, and how to develop your ORR checklist. The following steps are an abbreviated version of that document. For an in-depth understanding of what ORRs are and how to build your own, we recommend reading that whitepaper.

1. Gather the key stakeholders together, including representatives from security, operations, and development.

1. Have each stakeholder provide at least one requirement. For the first iteration, try to limit the number of items to thirty or less.
   - [Appendix B: Example ORR questions](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/appendix-b-example-orr-questions.html) from the Operational Readiness Reviews (ORR) whitepaper contains sample questions that you can use to get started.

1. Collect your requirements into a spreadsheet.
   - You can use [custom lenses](https://docs.aws.amazon.com/wellarchitected/latest/userguide/lenses-custom.html) in the [AWS Well-Architected Tool](https://console.aws.amazon.com/wellarchiected/) to develop your ORR and share them across your accounts and AWS Organization.

1. Identify one workload to conduct the ORR on. A pre-launch workload or an internal workload is ideal.

1. Run through the ORR checklist and take note of any discoveries made. Discoveries might be acceptable if a mitigation is in place. For any discovery that lacks a mitigation, add those to your backlog of items and implement them before launch.

1. Continue to add best practices and requirements to your ORR checklist over time.

 Support customers with Enterprise Support can request the [Operational Readiness Review Workshop](https://aws.amazon.com/premiumsupport/technology-and-programs/proactive-services/) from their Technical Account Manager. The workshop is an interactive *working backwards* session to develop your own ORR checklist.

## Resources
### Related Best Practices
- [OPS01-BP03 Evaluate governance requirements](ops_priorities_governance_reqs.md) – Governance requirements are a natural fit for an ORR checklist.
- [OPS01-BP04 Evaluate compliance requirements](ops_priorities_compliance_reqs.md) – Compliance requirements are sometimes included in an ORR checklist. Other times they are a separate process.
- [OPS03-BP07 Resource teams appropriately](ops_org_culture_team_res_appro.md) – Team capability is a good candidate for an ORR requirement.
- [OPS06-BP01 Plan for unsuccessful changes](ops_mit_deploy_risks_plan_for_unsucessful_changes.md) – A rollback or rollforward plan must be established before you launch your workload.
- [OPS07-BP01 Ensure personnel capability](ops_ready_to_support_personnel_capability.md) – To support a workload you must have the required personnel.
- [SEC01-BP03 Identify and validate control objectives](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_control_objectives.html) – Security control objectives make excellent ORR requirements.
- [REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_planning_for_recovery_objective_defined_recovery.html) – Disaster recovery plans are a good ORR requirement.
- [COST02-BP01 Develop policies based on your organization requirements](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost_govern_usage_policies.html) – Cost management policies are good to include in your ORR checklist.
### Related Documents
- [AWS Control Tower - Guardrails in AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/guardrails.html)
- [AWS Well-Architected Tool - Custom Lenses](https://docs.aws.amazon.com/wellarchitected/latest/userguide/lenses-custom.html)
- [Operational Readiness Review Template by Adrian Hornsby](https://medium.com/the-cloud-architect/operational-readiness-review-template-e23a4bfd8d79)
- [Operational Readiness Reviews (ORR) Whitepaper](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/wa-operational-readiness-reviews.html)
### Related Videos
- [AWS Supports You \$1 Building an Effective Operational Readiness Review (ORR)](https://www.youtube.com/watch?v=Keo6zWMQqS8)
### Related Examples
- [Sample Operational Readiness Review (ORR) Lens](https://github.com/aws-samples/custom-lens-wa-sample/tree/main/ORR-Lens)
### Related Services
- [AWS Config](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)
- [AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)
- [AWS Security Hub](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)
- [AWS Well-Architected Tool](https://docs.aws.amazon.com/wellarchitected/latest/userguide/intro.html)
