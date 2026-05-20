---
id: "REL06-BP04"
title: "Automate responses (Real-time processing and alarming)"
framework: "WAF"
domain: "Reliability"
capability: "How do you monitor workload resources?"
risk_level: "Medium"
---

# REL06-BP04 Automate responses (Real-time processing and alarming)

## Desired Outcome
Real-time alarms are identified, and automated processing of alarms is set up to invoke the appropriate actions taken to maintain service level objectives and service-level agreements (SLAs). Automation can range from self-healing activities of single components to full-site failover.

## Anti-Patterns
- Not having a clear inventory or catalog of key real-time alarms.
- No automated responses on critical alarms (for example, when compute is nearing exhaustion, autoscaling occurs).
- Contradictory alarm response actions.
- No standard operating procedures (SOPs) for operators to follow when they receive alert notifications.
- Not monitoring configuration changes, as undetected configuration changes can cause downtime for workloads.
- Not having a strategy to undo unintended configuration changes.

## Implementation Guidance
 To effectively manage alerts and automate their response, categorize alerts based on their criticality and impact, document response procedures, and plan responses before ranking tasks.

 Identify tasks requiring specific actions (often detailed in runbooks), and examine all runbooks and playbooks to determine which tasks can be automated. If actions can be defined, often they can be automated. If actions cannot be automated, document manual steps in an SOP and train operators on them. Continually challenge manual processes for automation opportunities where you can establish and maintain a plan to automate alert responses.

## Implementation Steps
1.  **Create an inventory of alarms:** To obtain a list of all alarms, you can use the [AWS CLI](https://aws.amazon.com/cli/) using the [Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html) command `[describe-alarms](https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/describe-alarms.html)`. Depending upon how many alarms you have set up, you might have to use pagination to retrieve a subset of alarms for each call, or alternatively you can use the AWS SDK to obtain the alarms [using an API call](https://docs.aws.amazon.com/sdk-for-go/v1/developer-guide/cw-example-describing-alarms.html).

1.  **Document all alarm actions:** Update a runbook with all alarms and their actions, irrespective if they are manual or automated. [AWS Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/APIReference/Welcome.html) provides predefined runbooks. For more information about runbooks, see [Working with runbooks](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-documents.html). For detail on how to view runbook content, see [View runbook content](https://docs.aws.amazon.com/systems-manager-automation-runbooks/latest/userguide/automation-runbook-reference.html#view-automation-json).

1.  **Set up and manage alarm actions:** For any of the alarms that require an action, specify the [automated action using the CloudWatch SDK](https://docs.aws.amazon.com/sdk-for-go/v1/developer-guide/cw-example-using-alarm-actions.html). For example, you can change the state of your Amazon EC2 instances automatically based on a CloudWatch alarm by creating and enabling actions on an alarm or disabling actions on an alarm.

    You can also use [Amazon EventBridge](https://aws.amazon.com/eventbridge/) to respond automatically to system events, such as application availability issues or resource changes. You can create rules to indicate which events you're interested in, and the actions to take when an event matches a rule. The actions that can be automatically initiated include invoking an [AWS Lambda](https://aws.amazon.com/lambda/) function, invoking [Amazon EC2](https://aws.amazon.com/ec2/) `Run Command`, relaying the event to [Amazon Kinesis Data Streams](https://aws.amazon.com/kinesis/data-streams/), and seeing [Automate Amazon EC2 using EventBridge](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/automating_with_eventbridge.html).

1.  **Standard Operating Procedures (SOPs):** Based on your application components, [AWS Resilience Hub](https://docs.aws.amazon.com/resilience-hub/latest/userguide/what-is.html) recommends multiple [SOP templates](https://docs.aws.amazon.com/resilience-hub/latest/userguide/sops.html). You can use these SOPs to document all the processes an operator should follow in case an alert is raised. You can also [construct a SOP](https://docs.aws.amazon.com/resilience-hub/latest/userguide/building-sops.html) based on Resilience Hub recommendations, where you need an Resilience Hub application with an associated resiliency policy, as well as a historic resiliency assessment against that application. The recommendations for your SOP are produced by the resiliency assessment.

    Resilience Hub works with Systems Manager to automate the steps of your SOPs by providing a number of [SSM documents](https://docs.aws.amazon.com/resilience-hub/latest/userguide/create-custom-ssm-doc.html) you can use as the basis for those SOPs. For example, Resilience Hub may recommend an SOP for adding disk space based on an existing SSM automation document.

1.  **Perform automated actions using Amazon DevOps Guru:** You can use [Amazon DevOps Guru](https://aws.amazon.com/devops-guru/) to automatically monitor application resources for anomalous behavior and deliver targeted recommendations to speed up problem identification and remediation times. With DevOps Guru, you can monitor streams of operational data in near real time from multiple sources including Amazon CloudWatch metrics, [AWS Config](https://aws.amazon.com/config/), [AWS CloudFormation](https://aws.amazon.com/cloudformation/), and [AWS X-Ray](https://aws.amazon.com/xray/). You can also use DevOps Guru to automatically create [OpsItems](https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter-create-OpsItems-from-CloudWatch-Alarms.html) in OpsCenter and send events to [EventBridge for additional automation](https://docs.aws.amazon.com/devops-guru/latest/userguide/working-with-eventbridge.html).

## Resources
### Related Best Practices
- [REL06-BP01 Monitor all components for the workload (Generation)](rel_monitor_aws_resources_monitor_resources.md)
- [REL06-BP02 Define and calculate metrics (Aggregation)](rel_monitor_aws_resources_notification_aggregation.md)
- [REL06-BP03 Send notifications (Real-time processing and alarming)](rel_monitor_aws_resources_notification_monitor.md)
- [REL08-BP01 Use runbooks for standard activities such as deployment](rel_tracking_change_management_planned_changemgmt.md)
### Related Documents
- [AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)
- [Creating an EventBridge Rule That Triggers on an Event from an AWS Resource](https://docs.aws.amazon.com/eventbridge/latest/userguide/create-eventbridge-rule.html)
- [One Observability Workshop](https://observability.workshop.aws/)
- [The Amazon Builders' Library: Instrumenting distributed systems for operational visibility](https://aws.amazon.com/builders-library/instrumenting-distributed-systems-for-operational-visibility/)
- [What is Amazon DevOps Guru?](https://docs.aws.amazon.com/devops-guru/latest/userguide/welcome.html)
- [Working with Automation Documents (Playbooks)](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-documents.html)
### Related Videos
- [AWS re:Invent 2022 - Observability best practices at Amazon ](https://www.youtube.com/watch?v=zZPzXEBW4P8)
- [AWS re:Invent 2020: Automate anything with AWS Systems Manager](https://www.youtube.com/watch?v=AaI2xkW85yE)
- [ Introduction to AWS Resilience Hub](https://www.youtube.com/watch?v=_OTTCOjWqPo)
- [ Create Custom Ticket Systems for Amazon DevOps Guru Notifications ](https://www.youtube.com/watch?v=Mu8IqWVGUfg)
- [ Enable Multi-Account Insight Aggregation with Amazon DevOps Guru ](https://www.youtube.com/watch?v=MHezNcTSTbI)
### Related Examples
- [ Amazon CloudWatch and Systems Manager Workshop ](https://catalog.us-east-1.prod.workshops.aws/workshops/a8e9c6a6-0ba9-48a7-a90d-378a440ab8ba/en-US)
