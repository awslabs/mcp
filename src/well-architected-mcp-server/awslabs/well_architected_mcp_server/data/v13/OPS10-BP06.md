---
id: "OPS10-BP06"
title: "Communicate status through dashboards"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you manage workload and operations events?"
risk_level: "Medium"
---

# OPS10-BP06 Communicate status through dashboards

## Desired Outcome
- Your dashboards provide a comprehensive view of the system and business metrics relevant to different stakeholders.
- Stakeholders can proactively access operational information, reducing the need for frequent status requests.
- Real-time decision-making is enhanced during normal operations and incidents.

## Anti-Patterns
- Engineers joining an incident management call require status updates to get up to speed.
- Relying on manual reporting for management, which leads to delays and potential inaccuracies.
- Operations teams are frequently interrupted for status updates during incidents.

## Implementation Guidance
 Dashboards effectively communicate the status of your system and business metrics and can be tailored to the needs of different audience groups. Tools like Amazon CloudWatch dashboards and Amazon Quick Suite help you create interactive, real-time dashboards for system monitoring and business intelligence.

## Implementation Steps
1.  **Identify stakeholder needs:** Determine the specific information needs of different audience groups, such as technical teams, leadership, and customers.

1.  ** Choose the right tools:** Select appropriate tools like [Amazon CloudWatch dashboards](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html) for system monitoring and [Amazon Quick Suite](https://aws.amazon.com/quicksight/) for interactive business intelligence. [AWS Health](https://docs.aws.amazon.com/health/latest/ug/what-is-aws-health.html) provides a ready-to-use experience in the [AWS Health Dashboard](https://health.aws.amazon.com/health/home), or you can use Health events in Amazon EventBridge or through the AWS Health API to augment your own dashboards.

1.  **Design effective dashboards:**
   - Design dashboards to clearly present relevant metrics and KPIs, ensuring they are understandable and actionable.
   - Incorporate system-level and business-level views as needed.
   - Include both high-level (for broad overviews) and low-level (for detailed analysis) dashboards.
   - Integrate automated alarms within dashboards to highlight critical issues.
   - Annotate dashboards with important metrics thresholds and goals for immediate visibility.

1.  **Integrate data sources:**
   - Use [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) to aggregate and display metrics from various AWS services and [query metrics from other data sources](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/MultiDataSourceQuerying.html), creating a unified view of your system's health and business metrics.
   - Use features like [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html) to query and visualize log data from different applications and services.
   - Use AWS Health events to stay informed about the operational status and confirmed operational issues from AWS services through the [AWS Health API](https://docs.aws.amazon.com/health/latest/APIReference/Welcome.html) or [AWS Health events on Amazon EventBridge](https://docs.aws.amazon.com/health/latest/ug/cloudwatch-events-health.html).

1.  **Provide self-service access:**
   - Share CloudWatch dashboards with relevant stakeholders for self-service information access using [dashboard sharing features](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-dashboard-sharing.html).
   - Ensure that dashboards are easily accessible and provide real-time, up-to-date information.

1.  **Regularly update and refine:**
   - Continually update and refine dashboards to align with evolving business needs and stakeholder feedback.
   - Regularly review the dashboards to keep them relevant and effective for conveying the necessary information.

## Resources
### Related Best Practices
- [OPS08-BP05 Create dashboards](ops_workload_observability_create_dashboards.md)
### Related Documents
- [ Building dashboards for operational visibility ](https://aws.amazon.com/builders-library/building-dashboards-for-operational-visibility/)
- [ Using Amazon CloudWatch dashboards ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html)
- [ Create flexible dashboards with dashboard variables ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_dashboard_variables.html)
- [ Sharing CloudWatch dashboards ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-dashboard-sharing.html)
- [ Query metrics from other data sources ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/MultiDataSourceQuerying.html)
- [ Add a custom widget to a CloudWatch dashboard ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/add_custom_widget_dashboard.html)
### Related Examples
- [ One Observability Workshop - Dashboards ](https://catalog.us-east-1.prod.workshops.aws/workshops/31676d37-bbe9-4992-9cd1-ceae13c5116c/en-US/aws-native/dashboards)
