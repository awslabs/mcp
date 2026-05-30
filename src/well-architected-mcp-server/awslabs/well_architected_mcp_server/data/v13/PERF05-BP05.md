---
id: "PERF05-BP05"
title: "Use automation to proactively remediate performance-related issues"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do your organizational practices and culture contribute to performance efficiency in your workload?"
risk_level: "Low"
---

# PERF05-BP05 Use automation to proactively remediate performance-related issues

## Anti-Patterns
- You only allow operations staff the ability to make operational changes to the workload.
- You let all alarms filter to the operations team with no proactive remediation.

## Implementation Guidance
 Use alarms to trigger automated actions to remediate issues where possible. Escalate the alarm to those able to respond if automated response is not possible. For example, you may have a system that can predict expected key performance indicator (KPI) values and alarm when they breach certain thresholds, or a tool that can automatically halt or roll back deployments if KPIs are outside of expected values.

 Implement processes that provide visibility into performance as your workload is running. Build monitoring dashboards and establish baseline norms for performance expectations to determine if the workload is performing optimally.

## Implementation Steps
- **Identify remediation workflow:** Identify and understand the performance issue that can be remediated automatically. Use AWS monitoring solutions such as [Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html) or AWS X-Ray to help you better understand the root cause of the issue.
- **Define the automation process:** Create a step-by-step remediation process that can be used to automatically fix the issue.
- **Configure the initiation event:** Configure the event to automatically initiate the remediation process. For example, you can define a trigger to automatically restart an instance when it reaches a certain threshold of CPU utilization.
- **Automate the remediation:** Use AWS services and technologies to automate the remediation process. For example, [AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html) provides a secure and scalable way to automate the remediation process. Make sure to use self-healing logic to revert changes if they do not successfully resolve the issue.
- **Test the workflow** Test the automated remediation process in a pre-production environment.
- **Implement the workflow:** Implement the automated remediation in the production environment.
- **Develop a playbook:** Develop and document a playbook that outlines the steps for the remediation plan, including the initiation events, remediation logic, and actions taken. Make sure to train stakeholders to help them effectively respond to automated remediation events.
- **Review and refine:** Regularly assess the effectiveness of the automated remediation workflow. Adjust initiation events and remediation logic if necessary.

## Resources
### Related Documents
- [CloudWatch Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
- [Monitoring, Logging, and Performance AWS Partner Network Partners](https://aws.amazon.com/devops/partner-solutions/#_Monitoring.2C_Logging.2C_and_Performance)
- [X-Ray Documentation](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
- [Using Alarms and Alarm Actions in CloudWatch](https://docs.aws.amazon.com/sdk-for-go/v1/developer-guide/cw-example-using-alarm-actions.html)
- [ Build a Cloud Automation Practice for Operational Excellence: Best Practices from AWS Managed Services](https://aws.amazon.com/blogs/mt/build-a-cloud-automation-practice-for-operational-excellence-best-practices-from-aws-managed-services/)
- [ Automate your Amazon Redshift performance tuning with automatic table optimization ](https://aws.amazon.com/blogs/big-data/automate-your-amazon-redshift-performance-tuning-with-automatic-table-optimization/)
### Related Videos
- [AWS re:Invent 2023 - Strategies for automated scaling, remediation, and smart self-healing ](https://www.youtube.com/watch?v=nlGyIa3UQYU)
- [AWS re:Invent 2023 - [LAUNCH] Application monitoring for modern workloads ](https://www.youtube.com/watch?v=T2TovTLje8w)
- [AWS re:Invent 2023 - Implementing application observability ](https://www.youtube.com/watch?v=IcTcwUSwIs4)
- [AWS re:Invent 2021 - Intelligently automating cloud operations](https://www.youtube.com/watch?v=m0S8eAF0l54)
- [AWS re:Invent 2022 - Setting up controls at scale in your AWS environment](https://www.youtube.com/watch?v=NkE9_okfPG8)
- [AWS re:Invent 2022 - Automating patch management and compliance using AWS](https://www.youtube.com/watch?v=gL3baXQJvc0)
- [AWS re:Invent 2022 - How Amazon uses better metrics for improved website performance](https://www.youtube.com/watch?v=_uaaCiyJCFA&ab_channel=AWSEvents)
- [AWS re:Invent 2023 - Take a load off: Diagnose & resolve performance issues with Amazon RDS ](https://www.youtube.com/watch?v=Ulj88e5Aqzg)
- [AWS re:Invent 2021 -\$1New Launch\$1 Automatically detect and resolve issues with Amazon DevOps Guru ](https://www.youtube.com/watch?v=iwQNQHwoXfk)
- [AWS re:Invent 2023 - Centralize your operations ](https://www.youtube.com/watch?v=9-RBjmhDdaM)
### Related Examples
- [CloudWatch Logs Customize Alarms](https://github.com/awslabs/cloudwatch-logs-customize-alarms)
