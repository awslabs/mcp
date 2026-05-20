---
id: "PERF05-BP07"
title: "Review metrics at regular intervals"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do your organizational practices and culture contribute to performance efficiency in your workload?"
risk_level: "Medium"
---

# PERF05-BP07 Review metrics at regular intervals

## Anti-Patterns
- You allow metrics to stay in an alarm state for an extended period of time.
- You create alarms that are not actionable by an automation system.

## Implementation Guidance
 Constantly improve metric collection and monitoring. As part of responding to incidents or events, evaluate which metrics were helpful in addressing the issue and which metrics could have helped that are not currently being tracked. Use this method to improve the quality of metrics you collect so that you can prevent, or more quickly resolve future incidents.

 As part of responding to incidents or events, evaluate which metrics were helpful in addressing the issue and which metrics could have helped that are not currently being tracked. Use this to improve the quality of metrics you collect so that you can prevent or more quickly resolve future incidents.

## Implementation Steps
- **Define metrics:** Define critical performance metrics to monitor that are aligned to your workload objective, including metrics such as response time and resource utilization.
- **Establish baselines:** Set a baseline and desirable value for each metric. The baseline should provide reference points to identify deviation or anomalies.
- **Set up a cadence:** Set a cadence (like weekly or monthly) to review critical metrics.
- **Identify performance issues:** During each review, assess trends and deviation from the baseline values. Look for any performance bottlenecks or anomalies. For identified issues, conduct in-depth root cause analysis to understand the main reason behind the issue.
- **Identify corrective actions:** Use your analysis to identify corrective actions. This may include parameter tuning, fixing bugs, and scaling resources.
- **Document findings:** Document your findings, including identified issues, root causes, and corrective actions.
- **Iterate and improve:** Continually assess and improve the metrics review process. Use the lesson learned from previous review to enhance the process over time.

## Resources
### Related Documents
- [CloudWatch Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
- [Collect metrics and logs from Amazon EC2 Instances and on-premises servers with the CloudWatch Agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html?ref=wellarchitected)
- [ Query your metrics with CloudWatch Metrics Insights ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/query_with_cloudwatch-metrics-insights.html)
- [Monitoring, Logging, and Performance AWS Partner Network Partners](https://aws.amazon.com/devops/partner-solutions/#_Monitoring.2C_Logging.2C_and_Performance)
- [X-Ray Documentation](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
### Related Videos
- [AWS re:Invent 2022 - Setting up controls at scale in your AWS environment](https://www.youtube.com/watch?v=NkE9_okfPG8)
- [AWS re:Invent 2022 - How Amazon uses better metrics for improved website performance](https://www.youtube.com/watch?v=_uaaCiyJCFA&ab_channel=AWSEvents)
- [AWS re:Invent 2023 - Building an effective observability strategy ](https://www.youtube.com/watch?v=7PQv9eYCJW8)
- [AWS Summit SF 2022 - Full-stack observability and application monitoring with AWS](https://www.youtube.com/watch?v=or7uFFyHIX0)
- [AWS re:Invent 2023 - Take a load off: Diagnose & resolve performance issues with Amazon RDS ](https://www.youtube.com/watch?v=Ulj88e5Aqzg)
### Related Examples
- [Creating a dashboard with Quick Suite](https://github.com/aws-samples/amazon-quicksight-sdk-proserve)
- [ CloudWatch Dashboards ](https://catalog.us-east-1.prod.workshops.aws/workshops/a8e9c6a6-0ba9-48a7-a90d-378a440ab8ba/en-US/300-cloudwatch/340-cloudwatch-dashboards)
