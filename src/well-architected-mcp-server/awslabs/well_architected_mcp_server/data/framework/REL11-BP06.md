---
id: "REL11-BP06"
title: "Send notifications when events impact availability"
pillar: "Reliability"
risk_level: "MEDIUM"
capability: "How do you design your workload to withstand component failures?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_notifications_sent_system.html"
---

# REL11-BP06 Send notifications when events impact availability

Notifications are sent upon the detection of thresholds breached,
even if the event causing the issue was automatically resolved.

Automated healing allows your workload to be reliable. However, it
can also obscure underlying problems that need to be addressed.
Implement appropriate monitoring and events so that you can detect
patterns of problems, including those addressed by auto healing, so
that you can resolve root cause issues.

Resilient systems are designed so that degradation events are
immediately communicated to the appropriate teams. These
notifications should be sent through one or many communication
channels.

**Desired outcome:**Alerts are
immediately sent to operations teams when thresholds are breached,
such as error rates, latency, or other critical key performance
indicator (KPI) metrics, so that these issues are resolved as soon as
possible and user impact is avoided or minimized.

**Common anti-patterns:**

- Sending too many alarms.
- Sending alarms that are not actionable.
- Setting alarm thresholds too high (over sensitive) or too low
(under sensitive).
- Not sending alarms for external dependencies.
- Not considering
[gray
failures](https://docs.aws.amazon.com/whitepapers/latest/advanced-multi-az-resilience-patterns/gray-failures.html) when designing monitoring and alarms.
- Performing healing automation, but not notifying the appropriate
team that healing was needed.

**Benefits of establishing this best
practice:** Notifications of recovery make operational and
business teams aware of service degradations so that they can react
immediately to minimize both mean time to detect (MTTD) and mean
time to repair (MTTR). Notifications of recovery events also assure
that you don't ignore problems that occur infrequently.

**Level of risk exposed if this best practice
is not established:** Medium. Failure to implement
appropriate monitoring and events notification mechanisms can result
in failure to detect patterns of problems, including those addressed
by auto healing. A team will only be made aware of system
degradation when users contact customer service or by chance.

## Implementation guidance

When defining a monitoring strategy, a triggered alarm is a common
event. This event would likely contain an identifier for the
alarm, the alarm state (such as IN ALARM or OK), and details of
what triggered it. In many cases, an alarm event should be
detected and an email notification sent. This is an example of an
action on an alarm. Alarm notification is critical in
observability, as it informs the right people that there is an
issue. However, when action on events mature in your observability
solution, it can automatically remediate the issue without the
need for human intervention.

Once KPI-monitoring alarms have been established, alerts should be
sent to appropriate teams when thresholds are exceeded. Those
alerts may also be used to trigger automated processes that will
attempt to remediate the degradation.

For more complex threshold monitoring, composite alarms should be
considered. Composite alarms use a number of KPI-monitoring alarms
to create an alert based on operational business logic. CloudWatch
Alarms can be configured to send emails, or to log incidents in
third-party incident tracking systems using Amazon SNS integration
or Amazon EventBridge.

### Implementation steps

Create various types of alarms based on how the workloads are
monitored, such as:

- Application alarms are used to detect when
any part of your workload is not working properly.
- [Infrastructure
alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html) indicate when to scale resources. Alarms
can be visually displayed on dashboards, send alerts
through Amazon SNS or email, and work with Auto Scaling to
scale workload resources in or out.
- Simple
[static
alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ConsoleAlarms.html) can be created to monitor when a
metric breaches a static threshold for a specified number
of evaluation periods.
- [Composite
alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html) can account for complex alarms from multiple sources.
- Once the alarm has been created,
create appropriate notification events. You can directly
invoke an
[Amazon SNS
API](https://docs.aws.amazon.com/sns/latest/dg/welcome.html) to send notifications and link any automation
for remediation or communication.
- Stay informed about service degradations with [AWS Health](https://aws.amazon.com/premiumsupport/technology/aws-health/). [Create purpose-fit AWS Health event notifications](https://docs.aws.amazon.com/health/latest/ug/user-notifications.html) to e-mail and chat channels through [AWS User Notifications](https://docs.aws.amazon.com/notifications/latest/userguide/what-is-service.html) and integrate programmatically with [your monitoring and alerting tools through Amazon EventBridge](https://docs.aws.amazon.com/health/latest/ug/cloudwatch-events-health.html).

## Resources

**Related Well-Architected best
practices:**

- [Availability
Definition](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/availability.html)

**Related documents:**

- [Creating
a CloudWatch Alarm Based on a Static Threshold](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ConsoleAlarms.html)
- [What
Is Amazon EventBridge?](https://docs.aws.amazon.com/eventbridge/latest/userguide/what-is-amazon-eventbridge.html)
- [What
is Amazon Simple Notification Service?](https://docs.aws.amazon.com/sns/latest/dg/welcome.html)
- [Publishing
Custom Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html)
- [Using
Amazon CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [Setup
CloudWatch Composite alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html)
- [What's
new in AWS Observability at re:Invent 2022](https://aws.amazon.com/blogs/mt/whats-new-in-aws-observability-at-reinvent-2022/)

**Related tools:**

- [CloudWatch](https://aws.amazon.com/cloudwatch/)
- [CloudWatch
X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/security-logging-monitoring.html)
