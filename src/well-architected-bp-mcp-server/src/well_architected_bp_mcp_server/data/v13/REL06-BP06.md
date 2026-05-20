---
id: "REL06-BP06"
title: "Regularly review monitoring scope and metrics"
framework: "WAF"
domain: "Reliability"
capability: "How do you monitor workload resources?"
risk_level: "Medium"
---

# REL06-BP06 Regularly review monitoring scope and metrics

## Desired Outcome
You have an effective monitoring strategy that is regularly reviewed and updated periodically, as well as after any significant events or changes. You verify that key application health indicators are still relevant as your workload and business requirements evolve.

## Anti-Patterns
- You collect only default metrics.
- You set up a monitoring strategy, but you never review it.
- You don't discuss monitoring when major changes are deployed.
- You trust outdated metrics to determine workload health.
- Your operations teams are overwhelmed with false-positive alerts due to outdated metrics and thresholds.
- You lack observability of application components that are not being monitored.
- You focus only on low-level technical metrics and excluding business metrics in your monitoring.

## Implementation Guidance
 Review monitoring metrics and scope during your [operational readiness review (ORR)](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/wa-operational-readiness-reviews.html) process. Perform periodic operational readiness reviews on a consistent schedule to evaluate whether there are any gaps between your current workload and the monitoring you have configured. Establish a regular cadence for operational performance reviews and knowledge sharing to enhance your ability to achieve higher performance from your operational teams. Validate whether existing alert thresholds are still adequate, and check for situations where operational teams are receiving false-positive alerts or not monitoring aspects of the application that should be monitored.

 The [Resilience Analysis Framework](https://docs.aws.amazon.com/prescriptive-guidance/latest/resilience-analysis-framework/introduction.html) provides useful guidance that can help you navigate the process. The focus of the framework is to identify potential failure modes and the preventive and corrective controls you can use to mitigate their impact. This knowledge can help you identify the right metrics and events to monitor and alert upon.

## Implementation Steps
1.  Schedule and conduct regular reviews of the workload dashboards. You may have different cadences for the depth at which you inspect.

1.  Inspect for trends in the metrics. Compare the metric values to historic values to see if there are trends that may indicate that something that needs investigation. Examples of this include increased latency, decreased primary business function, and increased failure responses.

1.  Inspect for outliers and anomalies in your metrics, which can be masked by averages or medians. Look at the highest and lowest values during the time frame, and investigate the causes of observations that are far outside of normal bounds. As you continue to remove these causes, you can tighten your expected metric bounds in response to the improved consistency of your workload performance.

1.  Look for sharp changes in behavior. An immediate change in quantity or direction of a metric may indicate that there has been a change in the application or external factors that you may need to add additional metrics to track.

1.  Review whether the current monitoring strategy remains relevant for the application. Based on an analysis of previous incidents (or the Resilience Analysis Framework), assess if there are additional aspects of the application that should be incorporated into the monitoring scope.

1.  Review your Real User Monitoring (RUM) metrics to determine whether there are any gaps in application functionality coverage.

1.  Review your change management process. Update your procedures if necessary to include a monitoring analysis step that should be performed before you approve a change.

1.  Implement monitoring review as part of your operational readiness review and correction of error processes.

## Resources
### Related Best Practices
- [REL06-BP01 Monitor all components for the workload (Generation)](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_monitor_aws_resources_monitor_resources.html)
- [REL06-BP02 Define and calculate metrics (Aggregation)](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_monitor_aws_resources_notification_aggregation.html)
- [REL06-BP07 Monitor end-to-end tracing of requests through your system](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_monitor_aws_resources_end_to_end.html)
- [REL12-BP02 Perform post-incident analysis](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_testing_resiliency_rca_resiliency.html)
- [REL12-BP06 Conduct game days regularly](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_testing_resiliency_game_days_resiliency.html)
### Related Documents
- [Why you should develop a correction of error (COE)](https://aws.amazon.com/blogs/mt/why-you-should-develop-a-correction-of-error-coe/)
- [Using Amazon CloudWatch Dashboards](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html)
- [Building dashboards for operational visibility](https://aws.amazon.com/builders-library/building-dashboards-for-operational-visibility/?did=ba_card&trk=ba_card)
- [Advanced Multi-AZ Resilience Patterns - Gray failures](https://docs.aws.amazon.com/whitepapers/latest/advanced-multi-az-resilience-patterns/gray-failures.html)
- [Amazon CloudWatch Logs Insights Sample Queries](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-examples.html)
- [Debugging with Amazon CloudWatch Synthetics and AWS X-Ray](https://aws.amazon.com/blogs/devops/debugging-with-amazon-cloudwatch-synthetics-and-aws-x-ray/)
- [One Observability Workshop](https://observability.workshop.aws/)
- [The Amazon Builders' Library: Instrumenting distributed systems for operational visibility](https://aws.amazon.com/builders-library/instrumenting-distributed-systems-for-operational-visibility/)
- [Using Amazon CloudWatch Dashboards](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html)
- [AWS Observability Best Practices](https://aws-observability.github.io/observability-best-practices/)
- [Resilience Analysis Framework](https://docs.aws.amazon.com/prescriptive-guidance/latest/resilience-analysis-framework/introduction.html)
- [Resilience Analysis Framework - Observability](https://docs.aws.amazon.com/prescriptive-guidance/latest/resilience-analysis-framework/observability.html)
- [Operational Readiness Review - ORR](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/wa-operational-readiness-reviews.html)
