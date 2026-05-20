---
id: "OPS08-BP02"
title: "Analyze workload logs"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you utilize workload observability in your organization?"
risk_level: "Medium"
effort: "Medium"
---

# OPS08-BP02 Analyze workload logs

## Desired Outcome
Rich insights into application behavior and operations derived from thorough log analysis, ensuring proactive issue detection and mitigation.

## Anti-Patterns
- Neglecting the analysis of logs until a critical issue arises.
- Not using the full suite of tools available for log analysis, missing out on critical insights.
- Solely relying on manual review of logs without leveraging automation and querying capabilities.

## Implementation Guidance
 [Amazon CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html) is a powerful tool for log analysis. Integrated features like CloudWatch Logs Insights and Contributor Insights make the process of deriving meaningful information from logs intuitive and efficient.

## Implementation Steps
1.  **Set up CloudWatch Logs**: Configure applications and services to send logs to CloudWatch Logs.

1.  **Use log anomaly detection:** Utilize [Amazon CloudWatch Logs anomaly detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html) to automatically identify and alert on unusual log patterns. This tool helps you proactively manage anomalies in your logs and detect potential issues early.

1.  **Set up CloudWatch Logs Insights**: Use [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html) to interactively search and analyze your log data.

   1.  Craft queries to extract patterns, visualize log data, and derive actionable insights.

   1.  Use [CloudWatch Logs Insights pattern analysis](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData_Patterns.html) to analyze and visualize frequent log patterns. This feature helps you understand common operational trends and potential outliers in your log data.

   1.  Use [CloudWatch Logs compare (diff)](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData_Compare.html) to perform differential analysis between different time periods or across different log groups. Use this capability to pinpoint changes and assess their impacts on your system's performance or behavior.

1.  **Monitor logs in real-time with Live Tail:** Use [Amazon CloudWatch Logs Live Tail](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatchLogs_LiveTail.html) to view log data in real-time. You can actively monitor your application's operational activities as they occur, which provides immediate visibility into system performance and potential issues.

1.  **Leverage Contributor Insights**: Use [CloudWatch Contributor Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContributorInsights.html) to identify top talkers in high cardinality dimensions like IP addresses or user-agents.

1.  **Implement CloudWatch Logs metric filters**: Configure [CloudWatch Logs metric filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html) to convert log data into actionable metrics. This allows you to set alarms or further analyze patterns.

1.  **Implement [CloudWatch cross-account observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html):** Monitor and troubleshoot applications that span multiple accounts within a Region.

1.  **Regular review and refinement**: Periodically review your log analysis strategies to capture all relevant information and continually optimize application performance.

## Resources
### Related Best Practices
- [OPS04-BP01 Identify key performance indicators](ops_observability_identify_kpis.md)
- [OPS04-BP02 Implement application telemetry](ops_observability_application_telemetry.md)
- [OPS08-BP01 Analyze workload metrics](ops_workload_observability_analyze_workload_metrics.md)
### Related Documents
- [Analyzing Log Data with CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)
- [Using CloudWatch Contributor Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContributorInsights.html)
- [Creating and Managing CloudWatch Log Metric Filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html)
### Related Videos
- [Analyze Log Data with CloudWatch Logs Insights](https://www.youtube.com/watch?v=2s2xcwm8QrM)
- [Use CloudWatch Contributor Insights to Analyze High-Cardinality Data](https://www.youtube.com/watch?v=ErWRBLFkjGI)
### Related Examples
- [CloudWatch Logs Sample Queries](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-examples.html)
- [One Observability Workshop](https://catalog.workshops.aws/observability/en-US/intro)
