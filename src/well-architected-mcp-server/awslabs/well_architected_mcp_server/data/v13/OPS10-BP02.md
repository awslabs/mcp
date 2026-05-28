---
id: "OPS10-BP02"
title: "Have a process per alert"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you manage workload and operations events?"
risk_level: "High"
---

# OPS10-BP02 Have a process per alert

## Desired Outcome
Every alert initiates a specific, well-defined response plan. Where possible, responses are automated, with clear ownership and a defined escalation path. Alerts are linked to an up-to-date knowledge base so that any operator can respond consistently and effectively. Responses are quick and uniform across the board, enhancing operational efficiency and reliability.

## Anti-Patterns
- Alerts have no predefined response process, leading to makeshift and delayed resolutions.
- Alert overload causes important alerts to be overlooked.
- Alerts are inconsistently handled due to lack of clear ownership and responsibility.

## Implementation Guidance
 Having a process per alert involves establishing a clear response plan for each alert, automating responses where possible, and continually refining these processes based on operational feedback and evolving requirements.

## Implementation Steps
 The following diagram illustrates the incident management workflow within [AWS Systems Manager Incident Manager](https://aws.amazon.com/systems-manager/features/incident-manager/). It is designed to respond swiftly to operational issues by automatically creating incidents in response to specific events from [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) or [Amazon EventBridge](https://aws.amazon.com/eventbridge/). When an incident is created, either automatically or manually, Incident Manager centralizes the management of the incident, organizes relevant AWS resource information, and initiates predefined response plans. This includes running Systems Manager Automation runbooks for immediate action, as well as creating a parent operational work item in OpsCenter to track related tasks and analyses. This streamlined process speeds up and coordinates incident response across your AWS environment.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/incident-manager-how-it-works.png)

1.  **Use composite alarms:** Create [composite alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html) in CloudWatch to group related alarms, reducing noise and allowing for more meaningful responses.

1.  **Stay informed with [AWS Health](https://docs.aws.amazon.com/health/latest/ug/what-is-aws-health.html):** AWS Health is the authoritative source of information about the health of your AWS Cloud resources. Use AWS Health to visualize and get notified of any current service events and upcoming changes, such as planned lifecycle events, so you can take steps to mitigate impacts.

   1.  [Create purpose-fit AWS Health event notifications](https://docs.aws.amazon.com/health/latest/ug/user-notifications.html) to e-mail and chat channels through [AWS User Notifications](https://docs.aws.amazon.com/notifications/latest/userguide/what-is-service.html), and integrate programatically with [your monitoring and alerting tools through Amazon EventBridge](https://docs.aws.amazon.com/health/latest/ug/cloudwatch-events-health.html) or the [AWS Health API](https://docs.aws.amazon.com/health/latest/APIReference/Welcome.html).

   1.  Plan and track progress on health events that require action by integrating with change management or ITSM tools (like [Jira](https://docs.aws.amazon.com/smc/latest/ag/cloud-sys-health.html) or [ServiceNow](https://docs.aws.amazon.com/smc/latest/ag/sn-aws-health.html)) that you may already use through Amazon EventBridge or the AWS Health API.

   1.  If you use AWS Organizations, enable [organization view for AWS Health](https://docs.aws.amazon.com/health/latest/ug/aggregate-events.html) to aggregate AWS Health events across accounts.

1.  **Integrate Amazon CloudWatch alarms with Incident Manager:** Configure CloudWatch alarms to automatically create incidents in [AWS Systems Manager Incident Manager](https://docs.aws.amazon.com/incident-manager/latest/userguide/response-plans.html).

1.  **Integrate Amazon EventBridge with Incident Manager:** Create [EventBridge rules](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule.html) to react to events and create incidents using defined response plans.

1.  **Prepare for incidents in Incident Manager:**
   - Establish detailed [response plans](https://docs.aws.amazon.com/incident-manager/latest/userguide/response-plans.html) in Incident Manager for each type of alert.
   - Establish chat channels through [Amazon Q Developer in chat applications](https://docs.aws.amazon.com/incident-manager/latest/userguide/chat.html) connected to response plans in Incident Manager, facilitating real-time communication during incidents across platforms like Slack, Microsoft Teams, and Amazon Chime.
   - Incorporate [Systems Manager Automation runbooks](https://docs.aws.amazon.com/incident-manager/latest/userguide/runbooks.html) within Incident Manager to drive automated responses to incidents.

## Resources
### Related Best Practices
- [OPS04-BP01 Identify key performance indicators](ops_observability_identify_kpis.md)
- [OPS08-BP04 Create actionable alerts](ops_workload_observability_create_alerts.md)
### Related Documents
- [AWS Cloud Adoption Framework: Operations Perspective - Incident and problem management ](https://docs.aws.amazon.com/whitepapers/latest/aws-caf-operations-perspective/incident-and-problem-management.html)
- [Using Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [ Setting up AWS Systems Manager Incident Manager](https://docs.aws.amazon.com/incident-manager/latest/userguide/setting-up.html)
- [ Preparing for incidents in Incident Manager ](https://docs.aws.amazon.com/incident-manager/latest/userguide/incident-response.html)
### Related Videos
- [ Top incident response tips from AWS](https://www.youtube.com/watch?v=Cu20aOvnHwA)
- [ re:Invent 2023 \$1 Manage resource lifecycle events at scale with AWS Health](https://www.youtube.com/watch?v=VoLLNL5j9NA)
### Related Examples
- [AWS Workshops - AWS Systems Manager Incident Manager - Automate incident response to security events ](https://catalog.workshops.aws/automate-incident-response/en-US/settingupim/onboarding)
