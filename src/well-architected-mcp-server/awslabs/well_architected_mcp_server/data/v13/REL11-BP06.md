---
id: "REL11-BP06"
title: "Send notifications when events impact availability"
framework: "WAF"
domain: "Reliability"
capability: "How do you design your workload to withstand component failures?"
risk_level: "Medium"
---

# REL11-BP06 Send notifications when events impact availability

## Anti-Patterns
- Sending too many alarms.
- Sending alarms that are not actionable.
- Setting alarm thresholds too high (over sensitive) or too low (under sensitive).
- Not sending alarms for external dependencies.
- Not considering [gray failures](https://docs.aws.amazon.com/whitepapers/latest/advanced-multi-az-resilience-patterns/gray-failures.html) when designing monitoring and alarms.
- Performing healing automation, but not notifying the appropriate team that healing was needed.

## Implementation Guidance
 When defining a monitoring strategy, a triggered alarm is a common event. This event would likely contain an identifier for the alarm, the alarm state (such as `IN ALARM` or `OK`), and details of what triggered it. In many cases, an alarm event should be detected and an email notification sent. This is an example of an action on an alarm. Alarm notification is critical in observability, as it informs the right people that there is an issue. However, when action on events mature in your observability solution, it can automatically remediate the issue without the need for human intervention.

 Once KPI-monitoring alarms have been established, alerts should be sent to appropriate teams when thresholds are exceeded. Those alerts may also be used to trigger automated processes that will attempt to remediate the degradation.

 For more complex threshold monitoring, composite alarms should be considered. Composite alarms use a number of KPI-monitoring alarms to create an alert based on operational business logic. CloudWatch Alarms can be configured to send emails, or to log incidents in third-party incident tracking systems using Amazon SNS integration or Amazon EventBridge.

## Implementation Steps
 Create various types of alarms based on how the workloads are monitored, such as:
- Application alarms are used to detect when any part of your workload is not working properly.
- [Infrastructure alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html) indicate when to scale resources. Alarms can be visually displayed on dashboards, send alerts through Amazon SNS or email, and work with Auto Scaling to scale workload resources in or out.
- Simple [static alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ConsoleAlarms.html) can be created to monitor when a metric breaches a static threshold for a specified number of evaluation periods.
- [Composite alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html) can account for complex alarms from multiple sources.
- Once the alarm has been created, create appropriate notification events. You can directly invoke an [Amazon SNS API](https://docs.aws.amazon.com/sns/latest/dg/welcome.html) to send notifications and link any automation for remediation or communication.
- Stay informed about service degradations with [AWS Health](https://aws.amazon.com/premiumsupport/technology/aws-health/). [Create purpose-fit AWS Health event notifications](https://docs.aws.amazon.com/health/latest/ug/user-notifications.html) to e-mail and chat channels through [AWS User Notifications](https://docs.aws.amazon.com/notifications/latest/userguide/what-is-service.html) and integrate programmatically with [your monitoring and alerting tools through Amazon EventBridge](https://docs.aws.amazon.com/health/latest/ug/cloudwatch-events-health.html).

## Resources
### Related Best Practices
- [Availability Definition](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/availability.html)
### Related Documents
- [Creating a CloudWatch Alarm Based on a Static Threshold](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ConsoleAlarms.html)
- [What Is Amazon EventBridge?](https://docs.aws.amazon.com/eventbridge/latest/userguide/what-is-amazon-eventbridge.html)
- [What is Amazon Simple Notification Service?](https://docs.aws.amazon.com/sns/latest/dg/welcome.html)
- [Publishing Custom Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html)
- [Using Amazon CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [Setup CloudWatch Composite alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html)
- [What's new in AWS Observability at re:Invent 2022](https://aws.amazon.com/blogs/mt/whats-new-in-aws-observability-at-reinvent-2022/)
### Related Tools
- [CloudWatch](https://aws.amazon.com/cloudwatch/)
- [CloudWatch X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/security-logging-monitoring.html)
