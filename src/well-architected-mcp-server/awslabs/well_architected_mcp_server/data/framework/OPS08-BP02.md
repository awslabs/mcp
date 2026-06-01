---
id: "OPS08-BP02"
title: "Analyze workload logs"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How do you utilize workload observability in your organization?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_workload_observability_analyze_workload_logs.html"
description: "Regularly analyzing workload logs is essential for gaining a deeper understanding of the operational aspects of your application. By efficiently sifting through, visualizing, and interpreting log data, you can continually optimize application performance and security."
area: ["Operate", "Utilizing workload observability"]
relatedIds: ["OPS04-BP01", "OPS04-BP02", "OPS08-BP01"]
---

# OPS08-BP02 Analyze workload logs

Regularly analyzing workload logs is essential for gaining a deeper
understanding of the operational aspects of your application. By
efficiently sifting through, visualizing, and interpreting log data,
you can continually optimize application performance and security.

**Desired outcome:** Rich insights
into application behavior and operations derived from thorough log
analysis, ensuring proactive issue detection and mitigation.

**Common anti-patterns:**

- Neglecting the analysis of logs until a critical issue arises.
- Not using the full suite of tools available for log analysis,
missing out on critical insights.
- Solely relying on manual review of logs without leveraging
automation and querying capabilities.

**Benefits of establishing this best
practice:**

- Proactive identification of operational bottlenecks, security
threats, and other potential issues.
- Efficient utilization of log data for continuous application
optimization.
- Enhanced understanding of application behavior, aiding in
debugging and troubleshooting.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

[Amazon CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html) is a powerful tool for log analysis.
Integrated features like CloudWatch Logs Insights and Contributor
Insights make the process of deriving meaningful information from
logs intuitive and efficient.

### Implementation steps

- **Set up CloudWatch Logs**:
Configure applications and services to send logs to
CloudWatch Logs.
- **Use log anomaly
detection:** Utilize
[Amazon CloudWatch Logs anomaly detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html) to automatically
identify and alert on unusual log patterns. This tool helps
you proactively manage anomalies in your logs and detect
potential issues early.
- **Set up CloudWatch Logs
Insights**: Use
[CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html) to interactively search and analyze
your log data.

Craft queries to extract patterns, visualize log data,
and derive actionable insights.
- Use
[CloudWatch Logs Insights pattern analysis](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData_Patterns.html) to analyze and
visualize frequent log patterns. This feature helps you
understand common operational trends and potential
outliers in your log data.
- Use
[CloudWatch Logs compare (diff)](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData_Compare.html) to perform differential
analysis between different time periods or across
different log groups. Use this capability to pinpoint
changes and assess their impacts on your system's
performance or behavior.

- **Monitor logs in real-time with Live
Tail:** Use
[Amazon CloudWatch Logs Live Tail](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatchLogs_LiveTail.html) to view log data in
real-time. You can actively monitor your application's
operational activities as they occur, which provides
immediate visibility into system performance and potential
issues.
- **Leverage Contributor
Insights**: Use
[CloudWatch
Contributor Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContributorInsights.html) to identify top talkers in high
cardinality dimensions like IP addresses or user-agents.
- **Implement CloudWatch Logs metric
filters**: Configure
[CloudWatch Logs metric filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html) to convert log data into
actionable metrics. This allows you to set alarms or further
analyze patterns.
- **Implement
[CloudWatch
cross-account observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html):** Monitor and
troubleshoot applications that span multiple accounts within
a Region.
- **Regular review and
refinement**: Periodically review your log analysis
strategies to capture all relevant information and
continually optimize application performance.

**Level of effort for the implementation
plan:** Medium

## Resources

**Related best practices:**

- OPS04-BP01 Identify key performance indicators
- OPS04-BP02 Implement application telemetry
- OPS08-BP01 Analyze workload metrics

**Related documents:**

- [Analyzing
Log Data with CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)
- [Using
CloudWatch Contributor Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContributorInsights.html)
- [Creating
and Managing CloudWatch Log Metric Filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html)

**Related videos:**

- [Analyze
Log Data with CloudWatch Logs Insights](https://www.youtube.com/watch?v=2s2xcwm8QrM)
- [Use
CloudWatch Contributor Insights to Analyze High-Cardinality
Data](https://www.youtube.com/watch?v=ErWRBLFkjGI)

**Related examples:**

- [CloudWatch Logs Sample Queries](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-examples.html)
- [One
Observability Workshop](https://catalog.workshops.aws/observability/en-US/intro)
