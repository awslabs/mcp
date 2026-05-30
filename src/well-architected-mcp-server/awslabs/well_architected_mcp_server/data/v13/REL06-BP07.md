---
id: "REL06-BP07"
title: "Monitor end-to-end tracing of requests through your system"
framework: "WAF"
domain: "Reliability"
capability: "How do you monitor workload resources?"
risk_level: "Medium"
---

# REL06-BP07 Monitor end-to-end tracing of requests through your system

## Desired Outcome
Workloads with comprehensive tracing across all components are easy to debug, improving [mean time to resolution](https://docs.aws.amazon.com/whitepapers/latest/availability-and-beyond-improving-resilience/reducing-mttr.html) (MTTR) of errors and latency by simplifying root cause discovery. End-to-end tracing reduces the time it takes to discover impacted components and drill into the detailed root causes of errors or latency.

## Anti-Patterns
- Tracing is used for some components but not for all. For example, without tracing for AWS Lambda, teams might not clearly understand latency caused by cold starts in a spiky workload.
- Synthetic canaries or real-user monitoring (RUM) are not configured with tracing. Without canaries or RUM, client interaction telemetry is omitted from the trace analysis yielding an incomplete performance profile.
- Hybrid workloads include both cloud native and third party tracing tools, but steps have not been taken elect and fully integrate a single tracing solution. Based on the elected tracing solution, cloud native tracing SDKs should be used to instrument components that are not cloud native or third party tools should be configured to ingest cloud native trace telemetry.

## Implementation Guidance
 Teams that operate distributed applications can use tracing tools to establish a correlation identifier, collect traces of requests, and build service maps of connected components. All application components should be included in request traces including service clients, middleware gateways and event buses, compute components, and storage, including key value stores and databases. Include synthetic canaries and real-user monitoring in your end-to-end tracing configuration to measure remote client interactions and latency so that you can accurately evaluate your systems performance against your service level agreements and objectives.

 You can use [AWS X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html) and [Amazon CloudWatch Application Monitoring](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Monitoring-Sections.html) instrumentation services to provide a complete view of requests as they travel through your application. X-Ray collects application telemetry and allows you to visualize and filter it across payloads, functions, traces, services, APIs, and can be turned on for system components with no-code or low-code. CloudWatch application monitoring includes ServiceLens to integrate your traces with metrics, logs, and alarms. CloudWatch application monitoring also includes synthetics to monitor your endpoints and APIs, as well as real-user monitoring to instrument your web application clients.

## Implementation Steps
- Use AWS X-Ray on all supported native services like [Amazon S3, AWS Lambda, and Amazon API Gateway](https://docs.aws.amazon.com/xray/latest/devguide/xray-services.html). These AWS services enable X-Ray with configuration toggles using infrastructure as code, AWS SDKs, or the AWS Management Console.
- Instrument applications [AWS Distro for Open Telemetry and X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-adot.html) or third-party collection agents.
- Review the [AWS X-Ray Developer Guide](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html) for programming language specific implementation. These documentation sections detail how to instrument HTTP requests, SQL queries, and other processes specific to your application programming language.
- Use X-Ray tracing for [Amazon CloudWatch Synthetic Canaries](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html) and [Amazon CloudWatch RUM](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html) to analyze the request path from your end user client through your downstream AWS infrastructure.
- Configure CloudWatch metrics and alarms based on resource health and canary telemetry so that teams are alerted to issues quickly, and can then deep dive into traces and service maps with ServiceLens.
- Enable X-Ray integration for third party tracing tools like [Datadog](https://docs.datadoghq.com/tracing/guide/serverless_enable_aws_xray/), [New Relic](https://docs.newrelic.com/docs/infrastructure/amazon-integrations/aws-integrations-list/aws-x-ray-monitoring-integration/), or [Dynatrace](https://www.dynatrace.com/support/help/setup-and-configuration/setup-on-cloud-platforms/amazon-web-services/amazon-web-services-integrations/aws-service-metrics) if you are using third party tools for your primary tracing solution.

## Resources
### Related Best Practices
- [REL06-BP01 Monitor all components for the workload (Generation)](rel_monitor_aws_resources_monitor_resources.md)
- [REL11-BP01 Monitor all components of the workload to detect failures](rel_withstand_component_failures_monitoring_health.md)
### Related Documents
- [What is AWS X-Ray?](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
- [ Amazon CloudWatch: Application Monitoring ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Monitoring-Sections.html)
- [Debugging with Amazon CloudWatch Synthetics and AWS X-Ray](https://aws.amazon.com/blogs/devops/debugging-with-amazon-cloudwatch-synthetics-and-aws-x-ray/)
- [The Amazon Builders' Library: Instrumenting distributed systems for operational visibility](https://aws.amazon.com/builders-library/instrumenting-distributed-systems-for-operational-visibility/)
- [ Integrating AWS X-Ray with other AWS services ](https://docs.aws.amazon.com/xray/latest/devguide/xray-services.html)
- [AWS Distro for OpenTelemetry and AWS X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-adot.html)
- [ Amazon CloudWatch: Using synthetic monitoring ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html)
- [ Amazon CloudWatch: Use CloudWatch RUM ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html)
- [ Set up Amazon CloudWatch synthetics canary and Amazon CloudWatch alarm ](https://docs.aws.amazon.com/solutions/latest/devops-monitoring-dashboard-on-aws/set-up-amazon-cloudwatch-synthetics-canary-and-amazon-cloudwatch-alarm.html)
- [ Availability and Beyond: Understanding and Improving the Resilience of Distributed Systems on AWS](https://docs.aws.amazon.com/whitepapers/latest/availability-and-beyond-improving-resilience/reducing-mttr.html)
### Related Examples
- [ One Observability Workshop ](https://catalog.workshops.aws/observability/en-US)
### Related Videos
- [AWS re:Invent 2022 - How to monitor applications across multiple accounts ](https://www.youtube.com/watch?v=kFGOkywu-rw)
- [ How to Monitor your AWS Applications ](https://www.youtube.com/watch?v=UxWU9mrSbmA)
### Related Tools
- [AWS X-Ray](https://aws.amazon.com/xray/)
- [ Amazon CloudWatch ](https://aws.amazon.com/pm/cloudwatch/)
- [ Amazon Route 53 ](https://aws.amazon.com/route53/)
