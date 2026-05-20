---
id: "REL11-BP07"
title: "Architect your product to meet availability targets and uptime service level agreements (SLAs)"
framework: "WAF"
domain: "Reliability"
capability: "How do you design your workload to withstand component failures?"
risk_level: "Medium"
---

# REL11-BP07 Architect your product to meet availability targets and uptime service level agreements (SLAs)

## Desired Outcome
Each application has a defined target for availability and SLA for performance metrics, which can be monitored and maintained in order to meet business outcomes.

## Anti-Patterns
- Designing and deploying workload’s without setting any SLAs.
- SLA metrics are set too high without rationale or business requirements.
- Setting SLAs without taking into account for dependencies and their underlying SLA.
- Application designs are created without considering the Shared Responsibility Model for Resilience.

## Implementation Guidance
 Application designs have to account for a diverse set of requirements that are derived from business, operational, and financial objectives. Within the operational requirements, workloads need to have specific resilience metric targets so they can be properly monitored and supported. Resilience metrics should not be set or derived after deploying the workload. They should be defined during the design phase and help guide various decisions and tradeoffs.
- Every workload should have its own set of resilience metrics. Those metrics may be different from other business applications.
- Reducing dependencies can have a positive impact on availability. Each workload should consider its dependencies and their SLAs. In general, select dependencies with availability goals equal to or greater than the goals of your workload.
- Consider loosely coupled designs so your workload can operate correctly despite dependency impairment, where possible.
- Reduce control plane dependencies, especially during recovery or a degradation. Evaluate designs that are statically stable for mission critical workloads. Use resource sparing to increase the availability of those dependencies in a workload.
- Observability and instrumentation are critical for achieving SLAs by reducing Mean Time to Detection (MTTD) and Mean Time to Repair (MTTR).
- Less frequent failure (longer MTBF), shorter failure detection times (shorter MTTD), and shorter repair times (shorter MTTR) are the three factors that are used to improve availability in distributed systems.
- Establishing and meeting resilience metrics for a workload is foundational to any effective design. Those designs must factor in tradeoffs of design complexity, service dependencies, performance, scaling, and costs.

## Implementation Steps
- Review and document the workload design considering the following questions:
  - Where are control planes used in the workload?
  - How does the workload implement fault tolerance?
  - What are the design patterns for scaling, automatic scaling, redundancy, and highly available components?
  - What are the requirements for data consistency and availability?
  - Are there considerations for resource sparing or resource static stability?
  - What are the service dependencies?
- Define SLA metrics based on the workload architecture while working with stakeholders. Consider the SLAs of all dependencies used by the workload.
- Once the SLA target has been set, optimize the architecture to meet the SLA.
- Once the design is set that will meet the SLA, implement operational changes, process automation, and runbooks that also will have focus on reducing MTTD and MTTR.
- Once deployed, monitor and report on the SLA.

## Resources
### Related Best Practices
- [REL03-BP01 Choose how to segment your workload](rel_service_architecture_monolith_soa_microservice.md)
- [REL10-BP01 Deploy the workload to multiple locations](rel_fault_isolation_multiaz_region_system.md)
- [REL11-BP01 Monitor all components of the workload to detect failures](rel_withstand_component_failures_monitoring_health.md)
- [REL11-BP03 Automate healing on all layers](rel_withstand_component_failures_auto_healing_system.md)
- [REL12-BP04 Test resiliency using chaos engineering](rel_testing_resiliency_failure_injection_resiliency.md)
- [REL13-BP01 Define recovery objectives for downtime and data loss](rel_planning_for_recovery_objective_defined_recovery.md)
- [ Understanding workload health ](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/understanding-workload-health.html)
### Related Documents
- [ Availability with redundancy ](https://docs.aws.amazon.com/whitepapers/latest/availability-and-beyond-improving-resilience/availability-with-redundancy.html)
- [ Reliability pillar - Availability ](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/availability.html)
- [ Measuring availability ](https://docs.aws.amazon.com/whitepapers/latest/availability-and-beyond-improving-resilience/measuring-availability.html)
- [AWS Fault Isolation Boundaries ](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/abstract-and-introduction.html)
- [ Shared Responsibility Model for Resiliency ](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/shared-responsibility-model-for-resiliency.html)
- [ Static stability using Availability Zones ](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)
- [AWS Service Level Agreements (SLAs) ](https://aws.amazon.com/legal/service-level-agreements/)
- [ Guidance for Cell-based Architecture on AWS](https://aws.amazon.com/solutions/guidance/cell-based-architecture-on-aws/)
- [AWS infrastructure ](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/aws-infrastructure.html)
- [ Advanced Multi-AZ Resilience Patterns whitepaper ](https://docs.aws.amazon.com/whitepapers/latest/advanced-multi-az-resilience-patterns/advanced-multi-az-resilience-patterns.html)
### Related Services
- [ Amazon CloudWatch ](https://aws.amazon.com/cloudwatch/)
- [AWS Config](https://aws.amazon.com/config/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
