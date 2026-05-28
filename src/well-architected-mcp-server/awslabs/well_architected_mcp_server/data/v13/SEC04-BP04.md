---
id: "SEC04-BP04"
title: "Initiate remediation for non-compliant resources"
framework: "WAF"
domain: "Security"
capability: "How do you detect and investigate security events?"
risk_level: "Medium"
---

# SEC04-BP04 Initiate remediation for non-compliant resources

## Desired Outcome
You define resource configuration standards along with the steps to remediate when resources are detected to be non-compliant. Where possible, you've defined remediations programmatically so they can be initiated either manually or through automation. Detection systems are in place to identify non-compliant resources and publish alerts into centralized tools that are monitored by your security personnel. These tools support running your programmatic remediations, either manually or automatically. Automatic remediations have appropriate oversight and control mechanisms in place to govern their use.

## Anti-Patterns
- You implement automation, but fail to thoroughly test and validate remediation actions. This can result in unintended consequences, such as disrupting legitimate business operations or causing system instability.
- You improve response times and procedures through automation, but without proper monitoring and mechanisms that allow human intervention and judgment when needed.
- You rely solely on remediations, rather than having remediations as one part of a broader incident response and recovery program.

## Implementation Guidance
 As described in [SEC01-BP03 Identify and validate control objectives](sec_securely_operate_control_objectives.md), services such as [AWS Config](https://aws.amazon.com/config/) and [AWS Security Hub](https://aws.amazon.com/security-hub/) can help you monitor the configuration of resources in your accounts for adherence to your requirements. When non-compliant resources are detected, services such as AWS Security Hub, can help with routing alerts appropriately and remediation. These solutions provide a central place for your security investigators to monitor for issues and take corrective action.

 While some non-compliant resource situations are unique and require human judgment to remediate, other situations have a standard response that you can define programmatically. For example, a standard response to a misconfigured VPC security group could be to remove the disallowed rules and notify the owner. Responses can be defined in [AWS Lambda](https://aws.amazon.com/pm/lambda) functions, [AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html) documents, or through other code environments you prefer. Make sure the environment is able to authenticate to AWS using an IAM role with the least amount of permission needed to take corrective action.

 Once you define the desired remediation, you can then determine your preferred means for initiating it. AWS Config can [initiate remediations](https://docs.aws.amazon.com/config/latest/developerguide/remediation.html) for you. If you are using Security Hub, you can do this through [custom actions](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cwe-custom-actions.html), which publishes the finding information to [Amazon EventBridge](https://aws.amazon.com/eventbridge/). An EventBridge rule can then initiate your remediation. You can configure remediations through Security Hub to run either automatically or manually.

 For programmatic remediation, we recommend that you have comprehensive logs and audits for the actions taken, as well as their outcomes. Review and analyze these logs to assess the effectiveness of the automated processes, and identify areas of improvement. Capture logs in [Amazon CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html) and remediation outcomes as [finding notes](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-findings.html) in Security Hub.

 As a starting point, consider [Automated Security Response on AWS](https://aws.amazon.com/solutions/implementations/automated-security-response-on-aws/), which has pre-built remediations for resolving common security misconfigurations.

## Implementation Steps
1.  Analyze and prioritize alerts.

   1.  Consolidate security alerts from various AWS services into Security Hub for centralized visibility, prioritization, and remediation.

1.  Develop remediations.

   1.  Use services such as Systems Manager and AWS Lambda to run programmatic remediations.

1.  Configure how remediations are initiated.

   1.  Using Systems Manager, define custom actions that publish findings to EventBridge. Configure these actions to be initiated manually or automatically.

   1.  You can also use [Amazon Simple Notification Service (SNS)](https://aws.amazon.com/sns/) to send notifications and alerts to relevant stakeholders (like security team or incident response teams) for manual intervention or escalation, if required.

1.  Review and analyze remediation logs for effectiveness and improvement.

   1.  Send log output to CloudWatch Logs. Capture outcomes as finding notes in Security Hub.

## Resources
### Related Best Practices
- [SEC06-BP03 Reduce manual management and interactive access](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_protect_compute_reduce_manual_management.html)
### Related Documents
- [AWS Security Incident Response Guide - Detection](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/detection.html)
### Related Examples
- [Automated Security Response on AWS](https://aws.amazon.com/solutions/implementations/automated-security-response-on-aws/)
- [Monitor EC2 instance key pairs using AWS Config](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/monitor-ec2-instance-key-pairs-using-aws-config.html)
- [Create AWS Config custom rules by using AWS CloudFormation Guard policies](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/create-aws-config-custom-rules-by-using-aws-cloudformation-guard-policies.html)
- [Automatically remediate unencrypted Amazon RDS DB instances and clusters](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/automatically-remediate-unencrypted-amazon-rds-db-instances-and-clusters.html)
### Related Tools
- [AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)
- [Automated Security Response on AWS](https://aws.amazon.com/solutions/implementations/automated-security-response-on-aws/)
