---
id: "OPS04-BP05"
title: "Implement distributed tracing"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you implement observability in your workload?"
risk_level: "High"
effort: "Medium"
---

# OPS04-BP05 Implement distributed tracing

## Desired Outcome
Achieve a holistic view of requests flowing through your distributed system, allowing for precise debugging, optimized performance, and improved user experiences.

## Anti-Patterns
- Inconsistent instrumentation: Not all services in a distributed system are instrumented for tracing.
- Ignoring latency: Only focusing on errors and not considering the latency or gradual performance degradations.

## Implementation Guidance
 Begin by identifying all of the elements of your workload that require instrumentation. Once all components are accounted for, leverage tools such as AWS X-Ray and OpenTelemetry to gather trace data for analysis with tools like X-Ray and Amazon CloudWatch ServiceLens Map. Engage in regular reviews with developers, and supplement these discussions with tools like Amazon DevOps Guru, X-Ray Analytics and X-Ray Insights to help uncover deeper findings. Establish alerts from trace data to notify when outcomes, as defined in the workload monitoring plan, are at risk.

## Implementation Steps
 To implement distributed tracing effectively:

1.  **Adopt [AWS X-Ray](https://aws.amazon.com/xray/):** Integrate X-Ray into your application to gain insights into its behavior, understand its performance, and pinpoint bottlenecks. Utilize X-Ray Insights for automatic trace analysis.

1.  **Instrument your services:** Verify that every service, from an [AWS Lambda](https://aws.amazon.com/lambda/) function to an [EC2 instance](https://aws.amazon.com/ec2/), sends trace data. The more services you instrument, the clearer the end-to-end view.

1.  **Incorporate [CloudWatch Real User Monitoring](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html) and [synthetic monitoring](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html):** Integrate Real User Monitoring (RUM) and synthetic monitoring with X-Ray. This allows for capturing real-world user experiences and simulating user interactions to identify potential issues.

1.  **Use the [CloudWatch agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html):** The agent can send traces from either X-Ray or OpenTelemetry, enhancing the depth of insights obtained.

1.  **Use [Amazon DevOps Guru](https://aws.amazon.com/devops-guru/):** DevOps Guru uses data from X-Ray, CloudWatch, AWS Config, and AWS CloudTrail to provide actionable recommendations.

1.  **Analyze traces:** Regularly review the trace data to discern patterns, anomalies, or bottlenecks that might impact your application's performance.

1.  **Set up alerts:** Configure alarms in [CloudWatch](https://aws.amazon.com/cloudwatch/) for unusual patterns or extended latencies, allowing proactive issue addressing.

1.  **Continuous improvement:** Revisit your tracing strategy as services are added or modified to capture all relevant data points.

## Resources
### Related Best Practices
- [OPS04-BP01 Identify key performance indicators](ops_observability_identify_kpis.md)
- [OPS04-BP02 Implement application telemetry](ops_observability_application_telemetry.md)
- [OPS04-BP03 Implement user experience telemetry](ops_observability_customer_telemetry.md)
- [OPS04-BP04 Implement dependency telemetry](ops_observability_dependency_telemetry.md)
### Related Documents
- [AWS X-Ray Developer Guide ](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
- [ Amazon CloudWatch agent User Guide ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [ Amazon DevOps Guru User Guide ](https://docs.aws.amazon.com/devops-guru/latest/userguide/welcome.html)
### Related Videos
- [ Use AWS X-Ray Insights ](https://www.youtube.com/watch?v=tl8OWHl6jxw)
- [AWS on Air ft. Observability: Amazon CloudWatch and AWS X-Ray](https://www.youtube.com/watch?v=qBDBnPkZ-KI)
### Related Examples
- [ Instrumenting your application for AWS X-Ray](https://aws.amazon.com/xray/latest/devguide/xray-instrumenting-your-app.html)
