---
id: "REL13-BP01"
title: "Define recovery objectives for downtime and data loss"
framework: "WAF"
domain: "Reliability"
capability: "How do you plan for disaster recovery (DR)?"
risk_level: "High"
---

# REL13-BP01 Define recovery objectives for downtime and data loss

## Desired Outcome
Every workload has a designated RTO and RPO based on technical considerations and business impact.

## Anti-Patterns
- You haven't designated recovery objectives.
- You select arbitrary recovery objectives.
- You select recovery objectives that are too lenient and do not meet business objectives.
- You have not evaluated the impact of downtime and data loss.
- You select unrealistic recovery objectives, such as zero time to recover or zero data loss, which may not be achievable for your workload configuration.
- You select recovery objectives that are more stringent than actual business objectives. This forces recovery implementations that are costlier and more complicated than what the workload needs.
- You select recovery objectives that are incompatible with those of a dependent workload.
- You fail to consider regulatory and compliance requirements.

## Implementation Guidance
 Construct a matrix or worksheet to help guide your disaster recovery planning. In your matrix, create different workload categories or tiers based on their business impact (such as critical, high, medium, and low) and the associated RTOs and RPOs to target for each one. The following matrix provides an example (note that your RTO and RPO values may differ) you can follow:

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/disaster-recovery-matrix.png)

 For each workload, investigate and understand the impact of downtime and lost data on your business. The impact typically grows with downtime and data loss, but the shape of the impact can differ based on the workload type. For example, downtime for up to an hour might have low impact, but after that, the impact could quickly intensify. Impact can take many forms, including financial impact (such as lost revenue), reputational impact (including loss of customer trust), operational impact (such as a missed payroll or decreased productivity), and regulatory risk. Once completed, assign the workload to the appropriate tier.

 Consider the following questions when you analyze the impact of failure:

1.  What is the maximum time the workload can be unavailable before unacceptable impact to the business is incurred?

1.  How much impact, and what kind, will be incurred by the business by a workload disruption? Consider all kinds of impact, including financial, reputational, operational, and regulatory.

1.  What is the maximum amount of data that can be lost or unrecoverable before unacceptable impact to the business is incurred?

1.  Can lost data be recreated from other sources (also known as *derived* data)? If so, also consider the RPOs of all source data used to recreate the workload data.

1.  What are the recovery objectives and availability expectations of workloads that this one depends on (downstream)? Your workload's objectives must be achievable given the recovery capabilities of its downstream dependencies. Consider possible downstream dependency workarounds or mitigations that can improve this workload's recovery capability.

1.  What are the recovery objectives and availability expectations of workloads that depend on this one (upstream)? Upstream workload objectives may require this workload to have more stringent recovery capabilities than it first appears.

1.  Are there different recovery objectives based on the type of incident? For example, you might have different RTOs and RPOs depending on whether the incident impacts an Availability Zone or an entire Region.

1.  Do your recovery objectives change during certain events or times of the year? For example, you might have different RTOs and RPOs around holiday shopping seasons, sporting events, special sales, and new product launches.

1.  How do the recovery objectives align with any line of business and organizational disaster recovery strategy you might have?

1.  Are there legal or contractual ramifications to consider? For example, are you contractually obligated to provide a service with a given RTO or RPO? What penalties might you incur for not meeting them?

1.  Are you required to maintain data integrity to meet regulatory or compliance requirements?

 The following worksheet can aid your evaluation of each workload. You may modify this worksheet to suit your specific needs, such as adding additional questions.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/worksheet.png)

## Implementation Steps
1.  Identify the business stakeholders and technical teams responsible for each workload, and engage with them.

1.  Create categories or tiers of criticality for workload impact in your organization. Example categories include critical, high, medium, and low. For each category, choose an RTO and RPO that reflects your business objectives and requirements.

1.  Assign one of the impact categories you created in the previous step to each workload. To decide how a workload maps to a category, consider the workload's importance to the business and the impact of interruption or data loss, and use the questions above to guide you. This results in an RTO and RPO for each workload.

1.  Consider the RTO and RPO for each workload determined in the previous step. Involve the workload's business and technical teams to determine whether the objectives should be adjusted. For example, business stakeholders could determine that more stringent targets are required. Alternatively, technical teams could determine that targets should be modified to make them achievable with available resources and technological constraints.

## Resources
### Related Best Practices
- [REL09-BP04 Perform periodic recovery of the data to verify backup integrity and processes](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_backing_up_data_periodic_recovery_testing_data.html)
- [REL12-BP01 Use playbooks to investigate failures](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_testing_resiliency_playbook_resiliency.html)
- [REL13-BP02 Use defined recovery strategies to meet the recovery objectives](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)
- [REL13-BP03 Test disaster recovery implementation to validate the implementation](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_dr_tested.html)
### Related Documents
- [AWS Architecture Blog: Disaster Recovery Series](https://aws.amazon.com/blogs/architecture/tag/disaster-recovery-series/)
- [Disaster Recovery of Workloads on AWS: Recovery in the Cloud (AWS Whitepaper)](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.html)
- [Managing resiliency policies with AWS Resilience Hub](https://docs.aws.amazon.com/resilience-hub/latest/userguide/resiliency-policies.html)
- [APN Partner: partners that can help with disaster recovery](https://aws.amazon.com/partners/find/results/?keyword=Disaster+Recovery)
- [AWS Marketplace: products that can be used for disaster recovery](https://aws.amazon.com/marketplace/search/results?searchTerms=Disaster+recovery)
### Related Videos
- [AWS re:Invent 2018: Architecture Patterns for Multi-Region Active-Active Applications](https://youtu.be/2e29I3dA8o4)
- [Disaster Recovery of Workloads on AWS](https://www.youtube.com/watch?v=cJZw5mrxryA)
