---
id: "OPS11-BP02"
title: "Perform post-incident analysis"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How do you evolve operations?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_perform_rca_process.html"
---

# OPS11-BP02 Perform post-incident analysis

Review customer-impacting events and identify the contributing
factors and preventative actions. Use this information to develop
mitigations to limit or prevent recurrence. Develop procedures for
prompt and effective responses. Communicate contributing factors and
corrective actions as appropriate, tailored to target audiences.

**Desired outcome:**

- You have established incident management processes that include
post-incident analysis.
- You have observability plans in place to collect data on events.
- With this data, you understand and collect metrics that support
your post-incident analysis process.
- You learn from incidents to improve future outcomes.

**Common anti-patterns:**

- You administer an application server. Approximately every 23
hours and 55 minutes all your active sessions are terminated.
You have tried to identify what is going wrong on your
application server. You suspect it could instead be a network
issue but are unable to get cooperation from the network team as
they are too busy to support you. You lack a predefined process
to follow to get support and collect the information necessary
to determine what is going on.
- You have had data loss within your workload. This is the first
time it has happened and the cause is not obvious. You decide it
is not important because you can recreate the data. Data loss
starts occurring with greater frequency impacting your
customers. This also places addition operational burden on you
as you restore the missing data.

**Benefits of establishing this best
practice:**

- You have a predefined process to determine the components,
conditions, actions, and events that contributed to an incident,
which helps you identify opportunities for improvement.
- You use data from post-incident analysis to make improvements.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Use a process to determine contributing factors. Review all
customer impacting incidents. Have a process to identify and
document the contributing factors of an incident so that you can
develop mitigations to limit or prevent recurrence and you can
develop procedures for prompt and effective responses. Communicate
incident root causes as appropriate, and tailor the communication
to your target audience. Share learnings openly within your
organization.

### Implementation steps

- Collect metrics such as deployment change, configuration
change, incident start time, alarm time, time of engagement,
mitigation start time, and incident resolved time.
- Describe key time points on the timeline to understand the
events of the incident.
- Ask the following questions:

Could you improve time to detection?
- Are there updates to metrics and alarms that would
detect the incident sooner?
- Can you improve the time to diagnosis?
- Are there updates to your response plans or escalation
plans that would engage the correct responders sooner?
- Can you improve the time to mitigation?
- Are there runbook or playbook steps that you could add
or improve?
- Can you prevent future incidents from occurring?

- Create checklists and actions. Track and deliver all
actions.

**Level of effort for the implementation
plan:** Medium

## Resources

**Related best practices:**

- [OPS11-BP01 Have a process for continuous improvement](./ops_evolve_ops_process_cont_imp.html)
- [OPS 4 - Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

**Related documents:**

- [Performing
a post-incident analysis in Incident Manager](https://docs.aws.amazon.com/incident-manager/latest/userguide/analysis.html)
- [Operational
Readiness Review](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/iteration.html)
