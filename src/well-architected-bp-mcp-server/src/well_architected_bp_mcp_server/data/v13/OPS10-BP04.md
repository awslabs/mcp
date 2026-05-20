---
id: "OPS10-BP04"
title: "Define escalation paths"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you manage workload and operations events?"
risk_level: "Medium"
effort: "Medium"
---

# OPS10-BP04 Define escalation paths

## Desired Outcome
A structured and efficient process that escalates incidents to the appropriate personnel, minimizing response times and impact.

## Anti-Patterns
- Lack of clarity on recovery procedures leads to makeshift responses during critical incidents.
- Absence of defined permissions and ownership results in delays when urgent action is needed.
- Stakeholders and customers are not informed in line with expectations.
- Important decisions are delayed.

## Implementation Guidance
 Properly defined escalation paths are crucial for rapid incident response. AWS Systems Manager Incident Manager supports the setup of structured escalation plans and on-call schedules, which alert the right personnel so that they are ready to act when incidents occur.

## Implementation Steps
1.  **Set up escalation prompts:** Set up [CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html#alarms-and-actions) to create an incident in [AWS Systems Manager Incident Manager](https://docs.aws.amazon.com/incident-manager/latest/userguide/incident-creation.html).

1.  ** Set up on-call schedules:** Create [on-call schedules](https://docs.aws.amazon.com/incident-manager/latest/userguide/incident-manager-on-call-schedule-create.html) in Incident Manager that align with your escalation paths. Equip on-call personnel with the necessary permissions and tools to act swiftly.

1.  ** Detail escalation procedures: **
   - Determine specific conditions under which an incident should be escalated.
   - Create [escalation plans](https://docs.aws.amazon.com/incident-manager/latest/userguide/escalation.html) in Incident Manager.
   - Escalation channels should consist of a contact or an on-call schedule.
   - Define the roles and responsibilities of the team at each escalation level.

1.  **Pre-approve mitigation actions:** Collaborate with decision-makers to pre-approve actions for anticipated scenarios. Use [Systems Manager Automation runbooks](https://docs.aws.amazon.com/incident-manager/latest/userguide/tutorials-runbooks.html) integrated with Incident Manager to speed up incident resolution.

1.  **Specify ownership:** Clearly identify internal owners for each step of the escalation path.

1.  **Detail third-party escalations:**
   - Document third-party service-level agreements (SLAs), and align them with internal goals.
   - Set clear protocols for vendor communication during incidents.
   - Integrate vendor contacts into incident management tools for direct access.
   - Conduct regular drills that include third-party response scenarios.
   - Keep vendor escalation information well-documented and easily accessible.

1.  **Train and rehearse escalation plans:** Train your team on the escalation process and conduct regular incident response drills or game days. Enterprise Support customers can request an [Incident Management Workshop](https://aws.amazon.com/premiumsupport/technology-and-programs/proactive-services/).

1.  **Continue to improve:** Review the effectiveness of your escalation paths regularly. Update your processes based on lessons learned from incident post-mortems and continuous feedback.

## Resources
### Related Best Practices
- [OPS08-BP04 Create actionable alerts](ops_workload_observability_create_alerts.md)
- [OPS10-BP02 Have a process per alert](ops_event_response_process_per_alert.md)
- [OPS11-BP02 Perform post-incident analysis](ops_evolve_ops_perform_rca_process.md)
### Related Documents
- [AWS Systems Manager Incident Manager Escalation Plans ](https://docs.aws.amazon.com/incident-manager/latest/userguide/escalation.html)
- [ Working with on-call schedules in Incident Manager ](https://docs.aws.amazon.com/incident-manager/latest/userguide/incident-manager-on-call-schedule.html)
- [ Creating and Managing Runbooks ](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-documents.html)
- [ Temporary elevated access management with AWS IAM Identity Center](https://aws.amazon.com/blogs/security/temporary-elevated-access-management-with-iam-identity-center/)
- [ Atlassian - Escalation policies for effective incident management ](https://www.atlassian.com/incident-management/on-call/escalation-policies)
