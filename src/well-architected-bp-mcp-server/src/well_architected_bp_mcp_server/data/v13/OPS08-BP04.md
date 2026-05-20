---
id: "OPS08-BP04"
title: "Create actionable alerts"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you utilize workload observability in your organization?"
risk_level: "High"
effort: "Medium"
---

# OPS08-BP04 Create actionable alerts

## Desired Outcome
Receive timely, relevant, and actionable alerts for rapid identification and mitigation of potential issues, especially when KPI outcomes are at risk.

## Anti-Patterns
- Setting up too many non-critical alerts, leading to alert fatigue.
- Not prioritizing alerts based on KPIs, making it hard to understand the business impact of issues.
- Neglecting to address root causes, leading to repetitive alerts for the same issue.

## Implementation Guidance
 To create an effective alerting mechanism, it's vital to use metrics, logs, and trace data that flag when outcomes based on KPIs are at risk or anomalies are detected.

## Implementation Steps
1.  **Determine key performance indicators (KPIs)**: Identify your application's KPIs. Alerts should be tied to these KPIs to reflect the business impact accurately.

1.  **Implement anomaly detection**:
   - **Use Amazon CloudWatch anomaly detection**: Set up [Amazon CloudWatch anomaly detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html) to automatically detect unusual patterns, which helps you only generate alerts for genuine anomalies.
   - **Use AWS X-Ray Insights**:

     1.  Set up [X-Ray Insights](https://docs.aws.amazon.com/xray/latest/devguide/xray-console-insights.html) to detect anomalies in trace data.

     1.  Configure [notifications for X-Ray Insights](https://docs.aws.amazon.com/xray/latest/devguide/xray-console-insights.html#xray-console-insight-notifications) to be alerted on detected issues.
   - **Integrate with Amazon DevOps Guru**:

     1.  Leverage [Amazon DevOps Guru](https://aws.amazon.com/devops-guru/) for its machine learning capabilities in detecting operational anomalies with existing data.

     1.  Navigate to the [notification settings](https://docs.aws.amazon.com/devops-guru/latest/userguide/update-notifications.html#navigate-to-notification-settings) in DevOps Guru to set up anomaly alerts.

1.  **Implement actionable alerts**: Design alerts that provide adequate information for immediate action.

   1.  Monitor [AWS Health events with Amazon EventBridge rules](https://docs.aws.amazon.com/health/latest/ug/cloudwatch-events-health.html), or integrate programatically with the AWS Health API to automate actions when you receive AWS Health events. These can be general actions, such as sending all planned lifecycle event messages to a chat interface, or specific actions, such as the initiation of a workflow in an IT service management tool.

1.  **Reduce alert fatigue**: Minimize non-critical alerts. When teams are overwhelmed with numerous insignificant alerts, they can lose oversight of critical issues, which diminishes the overall effectiveness of the alert mechanism.

1.  **Set up composite alarms**: Use [Amazon CloudWatch composite alarms](https://aws.amazon.com/bloprove-monitoring-efficiency-using-amazon-cloudwatch-composite-alarms-2/) to consolidate multiple alarms.

1.  **Integrate with alert tools**: Incorporate tools like [Ops Genie](https://www.atlassian.com/software/opsgenie) and [PagerDuty](https://www.pagerduty.com/).

1.  **Engage Amazon Q Developer in chat applications**: Integrate [Amazon Q Developer in chat applications](https://aws.amazon.com/chatbot/) to relay alerts to Amazon Chime, Microsoft Teams, and Slack.

1.  **Alert based on logs**: Use [log metric filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html) in CloudWatch to create alarms based on specific log events.

1.  **Review and iterate**: Regularly revisit and refine alert configurations.

## Resources
### Related Best Practices
- [OPS04-BP01 Identify key performance indicators](ops_observability_identify_kpis.md)
- [OPS04-BP02 Implement application telemetry](ops_observability_application_telemetry.md)
- [OPS04-BP03 Implement user experience telemetry](ops_observability_customer_telemetry.md)
- [OPS04-BP04 Implement dependency telemetry](ops_observability_dependency_telemetry.md)
- [OPS04-BP05 Implement distributed tracing](ops_observability_dist_trace.md)
- [OPS08-BP01 Analyze workload metrics](ops_workload_observability_analyze_workload_metrics.md)
- [OPS08-BP02 Analyze workload logs](ops_workload_observability_analyze_workload_logs.md)
- [OPS08-BP03 Analyze workload traces](ops_workload_observability_analyze_workload_traces.md)
### Related Documents
- [Using Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [Create a composite alarm](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html)
- [Create a CloudWatch alarm based on anomaly detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Anomaly_Detection_Alarm.html)
- [DevOps Guru Notifications](https://docs.aws.amazon.com/devops-guru/latest/userguide/update-notifications.html)
- [X-ray insights notifications](https://docs.aws.amazon.com/xray/latest/devguide/xray-console-insights.html#xray-console-insight-notifications)
- [Monitor, operate, and troubleshoot your AWS resources with interactive ChatOps](https://aws.amazon.com/chatbot/)
- [Amazon CloudWatch Integration Guide \$1 PagerDuty](https://support.pagerduty.com/docs/amazon-cloudwatch-integration-guide)
- [Integrate Opsgenie with Amazon CloudWatch](https://support.atlassian.com/opsgenie/docs/integrate-opsgenie-with-amazon-cloudwatch/)
### Related Videos
- [Create Composite Alarms in Amazon CloudWatch](https://www.youtube.com/watch?v=0LMQ-Mu-ZCY)
- [Amazon Q Developer in chat applications Overview](https://www.youtube.com/watch?v=0jUSEfHbTYk)
- [AWS On Air ft. Mutative Commands in Amazon Q Developer in chat applications](https://www.youtube.com/watch?v=u2pkw2vxrtk)
### Related Examples
- [Alarms, incident management, and remediation in the cloud with Amazon CloudWatch](https://aws.amazon.com/bloarms-incident-management-and-remediation-in-the-cloud-with-amazon-cloudwatch/)
- [Tutorial: Creating an Amazon EventBridge rule that sends notifications to Amazon Q Developer in chat applications](https://docs.aws.amazon.com/chatbot/latest/adminguide/create-eventbridge-rule.html)
- [One Observability Workshop](https://catalog.workshops.aws/observability/en-US/intro)
