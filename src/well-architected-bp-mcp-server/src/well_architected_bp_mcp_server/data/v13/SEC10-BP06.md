---
id: "SEC10-BP06"
title: "Pre-deploy tools"
framework: "WAF"
domain: "Security"
capability: "How do you anticipate, respond to, and recover from incidents?"
risk_level: "Medium"
---

# SEC10-BP06 Pre-deploy tools

## Implementation Guidance
 To automate security response and operations functions, you can use a comprehensive set of APIs and tools from AWS. You can fully automate identity management, network security, data protection, and monitoring capabilities and deliver them using popular software development methods that you already have in place. When you build security automation, your system can monitor, review, and initiate a response, rather than having people monitor your security position and manually react to events.

 If your incident response teams continue to respond to alerts in the same way, they risk alert fatigue. Over time, the team can become desensitized to alerts and can either make mistakes handling ordinary situations or miss unusual alerts. Automation helps avoid alert fatigue by using functions that process the repetitive and ordinary alerts, leaving humans to handle the sensitive and unique incidents. Integrating anomaly detection systems, such as Amazon GuardDuty, AWS CloudTrail Insights, and Amazon CloudWatch Anomaly Detection, can reduce the burden of common threshold-based alerts.

 You can improve manual processes by programmatically automating steps in the process. After you define the remediation pattern to an event, you can decompose that pattern into actionable logic, and write the code to perform that logic. Responders can then run that code to remediate the issue. Over time, you can automate more and more steps, and ultimately automatically handle whole classes of common incidents.

 During a security investigation, you need to be able to review relevant logs to record and understand the full scope and timeline of the incident. Logs are also required for alert generation, indicating certain actions of interest have happened. It is critical to select, enable, store, and set up querying and retrieval mechanisms, and set up alerting. Additionally, an effective way to provide tools to search log data is [Amazon Detective](https://aws.amazon.com/detective/).

 AWS oﬀers over 200 cloud services and thousands of features. We recommend that you review the services that can support and simplify your incident response strategy.

 In addition to logging, you should develop and implement a [tagging strategy](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html). Tagging can help provide context around the purpose of an AWS resource. Tagging can also be used for automation.

## Implementation Steps
 **Select and set up logs for analysis and alerting**

 See the following documentation on configuring logging for incident response:
- [ Logging strategies for security incident response ](https://aws.amazon.com/blogs/security/logging-strategies-for-security-incident-response/)
- [SEC04-BP01 Configure service and application logging](sec_detect_investigate_events_app_service_logging.md)

 **Enable security services to support detection and response**

 AWS provides native detective, preventative, and responsive capabilities, and other services can be used to architect custom security solutions. For a list of the most relevant services for security incident response, see [Cloud capability definitions](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/appendix-a-cloud-capability-definitions.html).

 **Develop and implement a tagging strategy**

 Obtaining contextual information on the business use case and relevant internal stakeholders surrounding an AWS resource can be difficult. One way to do this is in the form of tags, which assign metadata to your AWS resources and consist of a user-defined key and value. You can create tags to categorize resources by purpose, owner, environment, type of data processed, and other criteria of your choice.

 Having a consistent tagging strategy can speed up response times and minimize time spent on organizational context by allowing you to quickly identify and discern contextual information about an AWS resource. Tags can also serve as a mechanism to initiate response automations. For more detail on what to tag, see [Tagging your AWS resources](https://docs.aws.amazon.com/tag-editor/latest/userguide/tagging.html). You’ll want to first define the tags you want to implement across your organization. After that, you’ll implement and enforce this tagging strategy. For more detail on implementation and enforcement, see [Implement AWS resource tagging strategy using AWS Tag Policies and Service Control Policies (SCPs)](https://aws.amazon.com/blogs/mt/implement-aws-resource-tagging-strategy-using-aws-tag-policies-and-service-control-policies-scps/).

## Resources
### Related Best Practices
- [SEC04-BP01 Configure service and application logging](sec_detect_investigate_events_app_service_logging.md)
- [SEC04-BP02 Capture logs, findings, and metrics in standardized locations](sec_detect_investigate_events_logs.md)
### Related Documents
- [ Logging strategies for security incident response ](https://aws.amazon.com/blogs/security/logging-strategies-for-security-incident-response/)
- [ Incident response cloud capability definitions ](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/appendix-a-cloud-capability-definitions.html)
### Related Examples
- [ Threat Detection and Response with Amazon GuardDuty and Amazon Detective ](https://catalog.workshops.aws/guardduty/en-US)
- [ Security Hub Workshop ](https://catalog.workshops.aws/security)
- [ Vulnerability Management with Amazon Inspector ](https://catalog.workshops.aws/inspector/en-US)
