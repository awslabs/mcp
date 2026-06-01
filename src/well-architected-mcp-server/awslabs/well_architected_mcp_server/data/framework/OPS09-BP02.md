---
id: "OPS09-BP02"
title: "Communicate status and trends to ensure visibility into operation"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How do you understand the health of your operations?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_operations_health_communicate_status_trends.html"
---

# OPS09-BP02 Communicate status and trends to ensure visibility into operation

Knowing the state of your operations and its trending direction is necessary to identify when outcomes may be at risk, whether or not added work can be supported, or the effects that changes have had to your teams. During operations events, having status pages that users and operations teams can refer to for information can reduce pressure on communication channels and disseminate information proactively.

**Desired outcome:**

- Operations leaders have insight at a glance to see what sort of call volumes their teams are operating under and what efforts may be under way, such as deployments.
- Alerts are disseminated to stakeholders and user communities when impacts to normal operations occur.
- Organization leadership and stakeholders can check a status page in response to an alert or impact, and obtain information surrounding an operational event, such as points of contact, ticket information, and estimated recovery times.
- Reports are made available to leadership and other stakeholders to show operations statistics such as call volumes over a period of time, user satisfaction scores, numbers of outstanding tickets and their ages.

**Common anti-patterns:**

- A workload goes down, leaving a service unavailable. Call volumes spike as users request to know what's going on. Managers add to the volume requesting to know who's working an issue. Various operations teams duplicate efforts in trying to investigate.
- A desire for a new capability leads to several personnel being reassigned to an engineering effort. No backfill is provided, and issue resolution times spike. This information is not captured, and only after several weeks and dissatisfied user feedback does leadership become aware of the issue.

**Benefits of establishing this best
practice:** During operational events where the business is impacted, much time and energy can be wasted querying information from various teams attempting to understand the situation. By establishing widely-disseminated status pages and dashboards, stakeholders can quickly obtain information such as whether or not an issue was detected, who has lead on the issue, or when a return to normal operations may be expected. This frees team members from spending too much time communicating status to others and more time addressing issues.

In addition, dashboards and reports can provide insights to decision-makers and stakeholders to see how operations teams are able to respond to business needs and how their resources are being allocated. This is crucial for determining if adequate resources are in place to support the business.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Build dashboards that show the current key metrics for your ops teams, and make them readily accessible both to operations leaders and management.

Build status pages that can be updated quickly to show when an incident or event is unfolding, who has ownership and who is coordinating the response. Share any steps or workarounds that users should consider on this page, and disseminate the location widely. Encourage users to check this location first when confronted with an unknown issue.

Collect and provide reports that show the health of operations over time, and distribute this to leaders and decision makers to illustrate the work of operations along with challenges and needs.

Share between teams these metrics and reports that best reflect goals and KPIs and where they have been influential in driving change. Dedicate time to these activities to elevate the importance of operations inside of and between teams.

Use [AWS Health](https://docs.aws.amazon.com/health/latest/ug/what-is-aws-health.html) alongside your own dashboards, or integrate AWS Health events into them, so that your teams can correlate application issues to AWS service status.

## Resources

**Related best practices:**

- [OPS09-BP01 Measure operations goals and KPIs with metrics](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_operations_health_measure_ops_goals_kpis.html)

**Related documents:**

- [Measure Progress](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-cloud-operating-model/measure-progress.html)
- [Building dashboards for operation visibility](https://aws.amazon.com/builders-library/building-dashboards-for-operational-visibility/)

**Related examples:**

- [Data Operations](https://aws.amazon.com/solutions/app-development/data-operations)
- [How to track your cost optimization KPIs with KPI Dashboard](https://aws.amazon.com/blogs/aws-cloud-financial-management/how-to-track-your-cost-optimization-kpis-with-the-kpi-dashboard/)
- [The Importance of Key Performance Indicators (KPIs) for Large-Scale Cloud Migrations](https://aws.amazon.com/blogs/mt/the-importance-of-key-performance-indicators-kpis-for-large-scale-cloud-migrations/)
