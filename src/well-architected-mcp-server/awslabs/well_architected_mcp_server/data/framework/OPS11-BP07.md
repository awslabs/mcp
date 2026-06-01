---
id: "OPS11-BP07"
title: "Perform operations metrics reviews"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How do you evolve operations?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_metrics_review.html"
description: "Regularly perform retrospective analysis of operations metrics with cross-team participants from different areas of the business. Use these reviews to identify opportunities for improvement, potential courses of action, and to share lessons learned. Look for opportunities to improve in all of your environments (for example, development, test, and production)."
area: ["Evolve", "Learn, share, and improve"]
relatedIds: ["OPS08-BP05", "OPS09-BP03", "OPS10-BP01"]
---

# OPS11-BP07 Perform operations metrics reviews

Regularly perform retrospective analysis of operations metrics with
cross-team participants from different areas of the business. Use
these reviews to identify opportunities for improvement, potential
courses of action, and to share lessons learned. Look for
opportunities to improve in all of your environments (for example,
development, test, and production).

**Desired outcome:**

- You frequently review business-affecting metrics
- You detect and review anomalies through your observability
capabilities
- You use data to support business outcomes and goals

**Common anti-patterns:**

- Your maintenance window interrupts a significant retail
promotion. The business remains unaware that there is a standard
maintenance window that could be delayed if there are other
business impacting events.
- You suffered an extended outage because you commonly use an
outdated library in your organization. You have since migrated
to a supported library. The other teams in your organization do
not know that they are at risk.
- You do not regularly review attainment of customer SLAs. You are
trending to not meet your customer SLAs. There are financial
penalties related to not meeting your customer SLAs.

**Benefits of establishing this best
practice:**

- When you meet regularly to review operations metrics, events,
and incidents, you maintain common understanding across teams.
- Your team meets routinely to review metrics and incidents, which
positions you to take action on risks and recognize customer
SLAs.
- You share lessons learned, which provides data for
prioritization and targeted improvements for business outcomes.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

- Regularly perform retrospective analysis of operations metrics
with cross-team participants from different areas of the
business.
- Engage stakeholders, including the business, development, and
operations teams, to validate your findings from immediate
feedback and retrospective analysis and share lessons learned.
- Use their insights to identify opportunities for improvement
and potential courses of action.

## Resources

**Related best practices:**

- [OPS08-BP05
Create dashboards](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_workload_observability_create_dashboards.html)
- [OPS09-BP03
Review operations metrics and prioritize improvement](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_operations_health_review_ops_metrics_prioritize_improvement.html)
- [OPS10-BP01
Use a process for event, incident, and problem
management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_event_response_event_incident_problem_process.html)

**Related documents:**

- [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/)
- [Amazon CloudWatch metrics and dimensions reference](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CW_Support_For_AWS.html)
- [Publish
custom metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html)
- [Using
Amazon CloudWatch metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html)
- [Dashboards
and visualizations with CloudWatch](https://docs.aws.amazon.com/prescriptive-guidance/latest/implementing-logging-monitoring-cloudwatch/cloudwatch-dashboards-visualizations.html)
