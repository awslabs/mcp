---
id: "OPS10-BP03"
title: "Prioritize operational events based on business impact"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you manage workload and operations events?"
risk_level: "High"
---

# OPS10-BP03 Prioritize operational events based on business impact

## Desired Outcome
Responses to operational events are prioritized based on potential impact to business operations and objectives. This makes the responses efficient and effective.

## Anti-Patterns
- Every event is treated with the same level of urgency, leading to confusion and delays in addressing critical issues.
- You fail to distinguish between high and low impact events, leading to misallocation of resources.
- Your organization lacks a clear prioritization framework, resulting in inconsistent responses to operational events.
- Events are prioritized based on the order they are reported, rather than their impact on business outcomes.

## Implementation Guidance
 When faced with multiple operational events, a structured approach to prioritization based on impact and urgency is essential. This approach helps you make informed decisions, direct efforts where they're needed most, and mitigate the risk to business continuity.

## Implementation Steps
1.  **Assess impact:** Develop a classification system to evaluate the severity of events in terms of their potential impact on business operations and objectives. The following example shows impact categories:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/ops_event_response_prioritize_events.html)

1.  **Assess urgency:** Define urgency levels for how quickly an event needs a response, considering factors such as safety, financial implications, and service-level agreements (SLAs). The following example demonstrates urgency categories:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/ops_event_response_prioritize_events.html)

1.  **Create a prioritization matrix:**
   - Use a matrix to cross-reference impact and urgency, assigning priority levels to different combinations.
   - Make the matrix accessible and understood by all team members responsible for operational event responses.
   - The following example matrix displays incident severity according to urgency and impact:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/ops_event_response_prioritize_events.html)

1.  **Train and communicate:** Train response teams on the prioritization matrix and the importance of following it during an event. Communicate the prioritization process to all stakeholders to set clear expectations.

1.  **Integrate with incident response:**
   - Incorporate the prioritization matrix into your incident response plans and tools.
   - Automate the classification and prioritization of events where possible to speed up response times.
   - Enterprise Support customers can leverage [AWS Incident Detection and Response](https://aws.amazon.com/premiumsupport/aws-incident-detection-response/), which provides 24x7 proactive monitoring and incident management for production workloads.

1.  **Review and adapt:** Regularly review the effectiveness of the prioritization process and make adjustments based on feedback and changes in the business environment.

## Resources
### Related Best Practices
- [OPS03-BP03 Escalation is encouraged](ops_org_culture_team_enc_escalation.md)
- [OPS08-BP04 Create actionable alerts](ops_workload_observability_create_alerts.md)
- [OPS09-BP01 Measure operations goals and KPIs with metrics](ops_operations_health_measure_ops_goals_kpis.md)
### Related Documents
- [ Atlassian - Understanding incident severity levels ](https://www.atlassian.com/incident-management/kpis/severity-levels)
- [ IT Process Map - Checklist Incident Priority ](https://wiki.en.it-processmaps.com/index.php/Checklist_Incident_Priority)
