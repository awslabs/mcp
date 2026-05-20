---
id: "REL06-BP03"
title: "Send notifications (Real-time processing and alarming)"
framework: "WAF"
domain: "Reliability"
capability: "How do you monitor workload resources?"
risk_level: "High"
---

# REL06-BP03 Send notifications (Real-time processing and alarming)

## Desired Outcome
Rapid responses to operational events are possible through configuration of relevant alarms based on service and application metrics. When alarm thresholds are breached, the appropriate personnel and systems are notified so they can address underlying issues.

## Anti-Patterns
- Configuring alarms with an excessively high threshold, resulting in the failure to send vital notifications.
- Configuring alarms with a threshold that is too low, resulting in inaction on important alerts due to the noise of excessive notifications.
- Not updating alarms and their threshold when usage changes.
- For alarms best addressed through automated actions, sending the notification to personnel instead of generating the automated action results in excessive notifications being sent.

## Implementation Guidance
 Workloads should be equipped with real-time processing and alarming to improve the detectability of issues that could impact the availability of the application and serve as triggers for automated response. Organizations can perform real-time processing and alarming by creating alerts with defined metrics in order to receive notifications whenever significant events occur or a metric exceeds a threshold.

 [Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html) allows you to create [metric](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html) and composite alarms using CloudWatch alarms based on static threshold, anomaly detection, and other criteria. For more detail on the types of alarms you can configure using CloudWatch, see the [alarms section of the CloudWatch documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html).

 You can construct customized views of metrics and alerts of your AWS resources for your teams using [CloudWatch dashboards](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html). The customizable home pages in the CloudWatch console allow you to monitor your resources in a single view across multiple Regions.

 Alarms can perform one or more actions, like sending a notification to an [Amazon SNS topic](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/US_SetupSNS.html), performing an [Amazon EC2](https://aws.amazon.com/ec2/) action or an [Amazon EC2 Auto Scaling](https://aws.amazon.com/ec2/autoscaling/) action, or [creating an OpsItem](https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter-create-OpsItems-from-CloudWatch-Alarms.html) or [incident](https://docs.aws.amazon.com/incident-manager/latest/userguide/incident-creation.html) in AWS Systems Manager.

 Amazon CloudWatch uses [Amazon SNS](https://docs.aws.amazon.com/sns/latest/dg/welcome.html) to send notifications when the alarm changes state, providing message delivery from the publishers (producers) to the subscribers (consumers). For more detail on setting up Amazon SNS notifications, see [Configuring Amazon SNS](https://docs.aws.amazon.com/sns/latest/dg/sns-configuring.html).

 CloudWatch sends [EventBridge](https://aws.amazon.com/eventbridge/) [events](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-and-eventbridge.html) whenever a CloudWatch alarm is created, updated, deleted, or its state changes. You can use EventBridge with these events to create rules that perform actions, such as notifying you whenever the state of an alarm changes or automatically triggering events in your account using [Systems Manager automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html).

 Stay informed with [AWS Health](https://aws.amazon.com/premiumsupport/technology/aws-health/). AWS Health is the authoritative source of information about the health of your AWS Cloud resources. Use AWS Health to get notified of any confirmed service events so you can quickly take steps to mitigate any impact. Create purpose-fit AWS Health event notifications to e-mail and chat channels through [AWS User Notifications](https://docs.aws.amazon.com/notifications/latest/userguide/what-is-service.html) and integrate programmatically with [your monitoring and alerting tools through Amazon EventBridge](https://docs.aws.amazon.com/health/latest/ug/cloudwatch-events-health.html). If you use AWS Organizations, aggregate AWS Health events across accounts.

** When should you use EventBridge or Amazon SNS? **

 Both EventBridge and Amazon SNS can be used to develop event-driven applications, and your choice will depend on your specific needs.

 Amazon EventBridge is recommended when you want to build an application that reacts to events from your own applications, SaaS applications, and AWS services. EventBridge is the only event-based service that integrates directly with third-party SaaS partners. EventBridge also automatically ingests events from over 200 AWS services without requiring developers to create any resources in their account.

 EventBridge uses a defined JSON-based structure for events, and helps you create rules that are applied across the entire event body to select events to forward to a [target](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html). EventBridge currently supports over 20 AWS services as targets, including [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html), [Amazon SQS](https://aws.amazon.com/sqs/), Amazon SNS, [Amazon Kinesis Data Streams](https://aws.amazon.com/kinesis/data-streams/), and [Amazon Data Firehose](https://aws.amazon.com/kinesis/data-firehose/).

 Amazon SNS is recommended for applications that need high fan out (thousands or millions of endpoints). A common pattern we see is that customers use Amazon SNS as a target for their rule to filter the events that they need, and fan out to multiple endpoints.

 Messages are unstructured and can be in any format. Amazon SNS supports forwarding messages to six different types of targets, including Lambda, Amazon SQS, HTTP/S endpoints, SMS, mobile push, and email. Amazon SNS [typical latency is under 30 milliseconds](https://aws.amazon.com/sns/faqs/). A wide range of AWS services send Amazon SNS messages by configuring the service to do so (more than 30, including Amazon EC2, [Amazon S3](https://aws.amazon.com/s3/), and [Amazon RDS](https://aws.amazon.com/rds/)).

## Implementation Steps
1.  Create an alarm using [Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html).

   1.  A metric alarm monitors a single CloudWatch metric or an expression dependent on CloudWatch metrics. The alarm initiates one or more actions based on the value of the metric or expression in comparison to a threshold over a number of time intervals. The action may consist of sending a notification to an [Amazon SNS topic](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/US_SetupSNS.html), performing an [Amazon EC2](https://aws.amazon.com/ec2/) action or an [Amazon EC2 Auto Scaling](https://aws.amazon.com/ec2/autoscaling/) action, or [creating an OpsItem](https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter-create-OpsItems-from-CloudWatch-Alarms.html) or [incident](https://docs.aws.amazon.com/incident-manager/latest/userguide/incident-creation.html) in AWS Systems Manager.

   1.  A composite alarm consists of a rule expression that considers the alarm conditions of other alarms you've created. The composite alarm only enters alarm state if all rule conditions are met. The alarms specified in the rule expression of a composite alarm can include metric alarms and additional composite alarms. Composite alarms can send Amazon SNS notifications when their state changes and can create Systems Manager [OpsItems](https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter-create-OpsItems-from-CloudWatch-Alarms.html) or [incidents](https://docs.aws.amazon.com/incident-manager/latest/userguide/incident-creation.html) when they enter the alarm state, but they cannot perform Amazon EC2 or Auto Scaling actions.

1.  Set up [Amazon SNS notifications](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/US_SetupSNS.html). When creating a CloudWatch alarm, you can include an Amazon SNS topic to send a notification when the alarm changes state.

1.  [Create rules in EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-get-started.html) that matches specified CloudWatch alarms. Each rule supports multiple targets, including Lambda functions. For example, you can define an alarm that initiates when available disk space is running low, which triggers a Lambda function through an EventBridge rule, to clean up the space. For more detail on EventBridge targets, see [EventBridge targets](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html).

## Resources
### Related Best Practices
- [REL06-BP01 Monitor all components for the workload (Generation)](rel_monitor_aws_resources_monitor_resources.md)
- [REL06-BP02 Define and calculate metrics (Aggregation)](rel_monitor_aws_resources_notification_aggregation.md)
- [REL12-BP01 Use playbooks to investigate failures](rel_testing_resiliency_playbook_resiliency.md)
### Related Documents
- [ Amazon CloudWatch ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
- [ CloudWatch Logs insights ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)
- [Using Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [Using Amazon CloudWatch dashboards](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html)
- [Using Amazon CloudWatch metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html)
- [ Setting up Amazon SNS notifications ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/US_SetupSNS.html)
- [ CloudWatch anomaly detection ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)
- [ CloudWatch Logs data protection ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/protect-sensitive-log-data-types.html)
- [ Amazon EventBridge ](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html)
- [ Amazon Simple Notification Service ](https://aws.amazon.com/sns/)
### Related Videos
- [ reinvent 2022 observability videos ](https://www.youtube.com/results?search_query=reinvent+2022+observability)
- [AWS re:Invent 2022 - Observability best practices at Amazon ](https://www.youtube.com/watch?v=zZPzXEBW4P8)
### Related Examples
- [One Observability Workshop](https://observability.workshop.aws/)
- [ Amazon EventBridge to AWS Lambda with feedback control by Amazon CloudWatch Alarms ](https://serverlessland.com/patterns/cdk-closed-loop-serverless-control-pattern)
