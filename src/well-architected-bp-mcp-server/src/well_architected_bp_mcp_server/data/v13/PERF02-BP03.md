---
id: "PERF02-BP03"
title: "Collect compute-related metrics"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you select and use compute resources in your workload?"
risk_level: "High"
---

# PERF02-BP03 Collect compute-related metrics

## Anti-Patterns
- You only use manual log file searching for metrics.
- You only use the default metrics recorded by your monitoring software.
- You only review metrics when there is an issue.

## Implementation Guidance
 Cloud workloads can generate large volumes of data such as metrics, logs, and events. In the AWS Cloud, collecting metrics is a crucial step to improve security, cost efficiency, performance, and sustainability. AWS provides a wide range of performance-related metrics using monitoring services such as [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) to provide you with valuable insights. Metrics such as CPU utilization, memory utilization, disk I/O, and network inbound and outbound can provide insight into utilization levels or performance bottlenecks. Use these metrics as part of a data-driven approach to actively tune and optimize your workload's resources.  In an ideal case, you should collect all metrics related to your compute resources in a single platform with retention policies implemented to support cost and operational goals.

## Implementation Steps
- Identify which performance-related metrics are relevant to your workload. You should collect metrics around resource utilization and the way your cloud workload is operating (like response time and throughput).
  - [Amazon EC2 default metrics](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/viewing_metrics_with_cloudwatch.html)
  - [Amazon ECS default metrics](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cloudwatch-metrics.html)
  - [Amazon EKS default metrics](https://docs.aws.amazon.com/prescriptive-guidance/latest/implementing-logging-monitoring-cloudwatch/kubernetes-eks-metrics.html)
  - [Lambda default metrics](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-functions-access-metrics.html)
  - [Amazon EC2 memory and disk metrics](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/mon-scripts.html)
- Choose and set up the right logging and monitoring solution for your workload.
  - [AWS native Observability](https://catalog.workshops.aws/observability/en-US/aws-native)
  - [AWS Distro for OpenTelemetry](https://aws.amazon.com/otel/)
  - [Amazon Managed Service for Prometheus](https://docs.aws.amazon.com/grafana/latest/userguide/prometheus-data-source.html)
- Define the required filter and aggregation for the metrics based on your workload requirements.
  - [Quantify custom application metrics with Amazon CloudWatch Logs and metric filters](https://aws.amazon.com/blogs/mt/quantify-custom-application-metrics-with-amazon-cloudwatch-logs-and-metric-filters/)
  - [Collect custom metrics with Amazon CloudWatch strategic tagging](https://aws.amazon.com/blogs/infrastructure-and-automation/collect-custom-metrics-with-amazon-cloudwatch-strategic-tagging/)
- Configure data retention policies for your metrics to match your security and operational goals.
  - [Default data retention for CloudWatch metrics](https://aws.amazon.com/cloudwatch/faqs/#AWS_resource_.26_custom_metrics_monitoring)
  - [Default data retention for CloudWatch Logs](https://aws.amazon.com/cloudwatch/faqs/#Log_management)
- If required, create alarms and notifications for your metrics to help you proactively respond to performance-related issues.
  - [Create alarms for custom metrics using Amazon CloudWatch anomaly detection](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/create-alarms-for-custom-metrics-using-amazon-cloudwatch-anomaly-detection.html)
  - [Create metrics and alarms for specific web pages with Amazon CloudWatch RUM](https://aws.amazon.com/blogs/mt/create-metrics-and-alarms-for-specific-web-pages-amazon-cloudwatch-rum/)
- Use automation to deploy your metric and log aggregation agents.
  - [AWS Systems Manager automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html?ref=wellarchitected)
  - [OpenTelemetry Collector](https://aws-otel.github.io/docs/getting-started/collector)

## Resources
### Related Documents
- [Monitoring and observability](https://aws.amazon.com/cloudops/monitoring-and-observability/)
- [Best practices: implementing observability with AWS](https://aws.amazon.com/blogs/mt/best-practices-implementing-observability-with-aws/)
- [Amazon CloudWatch documentation](https://docs.aws.amazon.com/cloudwatch/index.html?ref=wellarchitected)
- [Collect metrics and logs from Amazon EC2 instances and on-premises servers with the CloudWatch Agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html?ref=wellarchitected)
- [Accessing Amazon CloudWatch Logs for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-functions-logs.html?ref=wellarchitected)
- [Using CloudWatch Logs with container instances](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_cloudwatch_logs.html?ref=wellarchitected)
- [Publish custom metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html?ref=wellarchitected)
- [AWS Answers: Centralized Logging](https://aws.amazon.com/answers/logging/centralized-logging/?ref=wellarchitected)
- [AWS Services That Publish CloudWatch Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CW_Support_For_AWS.html?ref=wellarchitected)
- [Monitoring Amazon EKS on AWS Fargate](https://aws.amazon.com/blogs/containers/monitoring-amazon-eks-on-aws-fargate-using-prometheus-and-grafana/)
### Related Videos
- [AWS re:Invent 2023 – [LAUNCH] Application monitoring for modern workloads](https://www.youtube.com/watch?v=T2TovTLje8w)
- [AWS re:Invent 2023 – Implementing application observability](https://www.youtube.com/watch?v=IcTcwUSwIs4)
- [AWS re:Invent 2023 – Building an effective observability strategy](https://www.youtube.com/watch?v=7PQv9eYCJW8)
- [AWS re:Invent 2023 – Seamless observability with AWS Distro for OpenTelemetry](https://www.youtube.com/watch?v=S4GfA2R0N_A)
- [Application Performance Management on AWS](https://www.youtube.com/watch?v=5T4stR-HFas&ref=wellarchitected)
### Related Examples
- [AWS for Linux Workloads Immersion Day- Amazon CloudWatch](https://catalog.us-east-1.prod.workshops.aws/workshops/a8e9c6a6-0ba9-48a7-a90d-378a440ab8ba/en-US/300-cloudwatch)
- [Monitoring Amazon ECS clusters and containers](https://ecsworkshop.com/monitoring/)
- [Monitoring with Amazon CloudWatch dashboards](https://catalog.workshops.aws/well-architected-performance-efficiency/en-US/3-monitoring/monitoring-with-cloudwatch-dashboards)
- [Amazon EKS workshop](https://www.eksworkshop.com/)
