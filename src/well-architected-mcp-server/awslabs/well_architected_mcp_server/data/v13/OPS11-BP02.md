---
id: "OPS11-BP02"
title: "Perform post-incident analysis"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you evolve operations?"
risk_level: "High"
effort: "Medium"
---

# OPS11-BP02 Perform post-incident analysis

## Desired Outcome
- You have established incident management processes that include post-incident analysis.
- You have observability plans in place to collect data on events.
- With this data, you understand and collect metrics that support your post-incident analysis process.
- You learn from incidents to improve future outcomes.

## Anti-Patterns
- You administer an application server. Approximately every 23 hours and 55 minutes all your active sessions are terminated. You have tried to identify what is going wrong on your application server. You suspect it could instead be a network issue but are unable to get cooperation from the network team as they are too busy to support you. You lack a predefined process to follow to get support and collect the information necessary to determine what is going on.
- You have had data loss within your workload. This is the first time it has happened and the cause is not obvious. You decide it is not important because you can recreate the data. Data loss starts occurring with greater frequency impacting your customers. This also places addition operational burden on you as you restore the missing data.

## Implementation Guidance
 Use a process to determine contributing factors. Review all customer impacting incidents. Have a process to identify and document the contributing factors of an incident so that you can develop mitigations to limit or prevent recurrence and you can develop procedures for prompt and effective responses. Communicate incident root causes as appropriate, and tailor the communication to your target audience. Share learnings openly within your organization.

## Implementation Steps
1.  Collect metrics such as deployment change, configuration change, incident start time, alarm time, time of engagement, mitigation start time, and incident resolved time.

1.  Describe key time points on the timeline to understand the events of the incident.

1.  Ask the following questions:

   1.  Could you improve time to detection?

   1.  Are there updates to metrics and alarms that would detect the incident sooner?

   1.  Can you improve the time to diagnosis?

   1.  Are there updates to your response plans or escalation plans that would engage the correct responders sooner?

   1.  Can you improve the time to mitigation?

   1.  Are there runbook or playbook steps that you could add or improve?

   1.  Can you prevent future incidents from occurring?

1.  Create checklists and actions. Track and deliver all actions.

## Resources
### Related Best Practices
- [OPS11-BP01 Have a process for continuous improvement](ops_evolve_ops_process_cont_imp.md)
- [ OPS 4 - Implement observability ](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)
### Related Documents
- [Performing a post-incident analysis in Incident Manager](https://docs.aws.amazon.com/incident-manager/latest/userguide/analysis.html)
- [Operational Readiness Review](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/iteration.html)
