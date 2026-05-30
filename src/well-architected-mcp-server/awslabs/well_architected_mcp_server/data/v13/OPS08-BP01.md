---
id: "OPS08-BP01"
title: "Analyze workload metrics"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you utilize workload observability in your organization?"
risk_level: "Medium"
effort: "Medium"
---

# OPS08-BP01 Analyze workload metrics

## Desired Outcome
Accurate insights into workload performance that drive data-informed decisions, ensuring alignment with business objectives.

## Anti-Patterns
- Analyzing metrics in isolation without considering their impact on business outcomes.
- Over-reliance on technical metrics while sidelining business metrics.
- Infrequent review of metrics, missing out on real-time decision-making opportunities.

## Implementation Guidance
 Leverage tools like Amazon CloudWatch to perform metric analysis. AWS services such as CloudWatch anomaly detection and Amazon DevOps Guru can be used to detect anomalies, especially when static thresholds are unknown or when patterns of behavior are more suited for anomaly detection.

## Implementation Steps
1.  **Analyze and review:** Regularly review and interpret your workload metrics.

   1.  Prioritize business outcome metrics over purely technical metrics.

   1.  Understand the significance of spikes, drops, or patterns in your data.

1.  **Utilize Amazon CloudWatch:** Use Amazon CloudWatch for a centralized view and deep-dive analysis.

   1.  Configure CloudWatch dashboards to visualize your metrics and compare them over time.

   1.  Use [percentiles in CloudWatch](https://aws-observability.github.io/observability-best-practices/guides/operational/business/sla-percentile/) to get a clear view of metric distribution, which can help in defining SLAs and understanding outliers.

   1.  Set up [CloudWatch anomaly detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html) to identify unusual patterns without relying on static thresholds.

   1.  Implement [CloudWatch cross-account observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html) to monitor and troubleshoot applications that span multiple accounts within a Region.

   1.  Use [CloudWatch Metric Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/query_with_cloudwatch-metrics-insights.html) to query and analyze metric data across accounts and Regions, identifying trends and anomalies.

   1.  Apply [CloudWatch Metric Math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html) to transform, aggregate, or perform calculations on your metrics for deeper insights.

1.  **Employ Amazon DevOps Guru:** Incorporate [Amazon DevOps Guru](https://aws.amazon.com/devops-guru/) for its machine learning-enhanced anomaly detection to identify early signs of operational issues for your serverless applications and remediate them before they impact your customers.

1.  **Optimize based on insights:** Make informed decisions based on your metric analysis to adjust and improve your workloads.

## Resources
### Related Best Practices
- [OPS04-BP01 Identify key performance indicators](ops_observability_identify_kpis.md)
- [OPS04-BP02 Implement application telemetry](ops_observability_application_telemetry.md)
### Related Documents
- [ The Wheel Blog - Emphasizing the importance of continually reviewing metrics ](https://aws.amazon.com/blogs/opensource/the-wheel/)
- [ Percentile are important ](https://aws-observability.github.io/observability-best-practices/guides/operational/business/sla-percentile/)
- [ Using AWS Cost Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)
- [ CloudWatch cross-account observability ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html)
- [ Query your metrics with CloudWatch Metrics Insights ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/query_with_cloudwatch-metrics-insights.html)
### Related Videos
- [ Enable Cross-Account Observability in Amazon CloudWatch ](https://www.youtube.com/watch?v=lUaDO9dqISc)
- [ Introduction to Amazon DevOps Guru ](https://www.youtube.com/watch?v=2uA8q-8mTZY)
- [ Continuously Analyze Metrics using AWS Cost Anomaly Detection](https://www.youtube.com/watch?v=IpQYBuay5OE)
### Related Examples
- [ One Observability Workshop ](https://catalog.workshops.aws/observability/en-US/intro)
- [ Gaining operation insights with AIOps using Amazon DevOps Guru ](https://catalog.us-east-1.prod.workshops.aws/workshops/f92df379-6add-4101-8b4b-38b788e1222b/en-US)
