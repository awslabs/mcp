---
id: "OPS04-BP05"
title: "Implement distributed tracing"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How do you implement observability in your workload?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_observability_dist_trace.html"
description: "Distributed tracing offers a way to monitor and visualize requests as they traverse through various components of a distributed system. By capturing trace data from multiple sources and analyzing it in a unified view, teams can better understand how requests flow, where bottlenecks exist, and where optimization efforts should focus."
area: ["Prepare", "Implement observability"]
relatedIds: ["OPS04-BP01", "OPS04-BP02", "OPS04-BP03", "OPS04-BP04"]
---

# OPS04-BP05 Implement distributed tracing

Distributed tracing offers a way to monitor and visualize requests as they traverse through various components of a distributed system. By capturing trace data from multiple sources and analyzing it in a unified view, teams can better understand how requests flow, where bottlenecks exist, and where optimization efforts should focus.

**Desired outcome:** Achieve a holistic view of requests flowing through your distributed system, allowing for precise debugging, optimized performance, and improved user experiences.

**Common anti-patterns:**

- Inconsistent instrumentation: Not all services in a distributed system are instrumented for tracing.
- Ignoring latency: Only focusing on errors and not considering the latency or gradual performance degradations.

**Benefits of establishing this best
practice:**

- Comprehensive system overview: Visualizing the entire path of requests, from entry to exit.
- Enhanced debugging: Quickly identifying where failures or performance issues occur.
- Improved user experience: Monitoring and optimizing based on actual user data, ensuring the system meets real-world demands.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Begin by identifying all of the elements of your workload that require instrumentation. Once all components are accounted for, leverage tools such as AWS X-Ray and OpenTelemetry to gather trace data for analysis with tools like X-Ray and Amazon CloudWatch ServiceLens Map. Engage in regular reviews with developers, and supplement these discussions with tools like Amazon DevOps Guru, X-Ray Analytics and X-Ray Insights to help uncover deeper findings. Establish alerts from trace data to notify when outcomes, as defined in the workload monitoring plan, are at risk.

### Implementation steps

To implement distributed tracing effectively:

- **Adopt [AWS X-Ray](https://aws.amazon.com/xray/):** Integrate X-Ray into your application to gain insights into its behavior, understand its performance, and pinpoint bottlenecks. Utilize X-Ray Insights for automatic trace analysis.
- **Instrument your services:** Verify that every service, from an [AWS Lambda](https://aws.amazon.com/lambda/) function to an [EC2 instance](https://aws.amazon.com/ec2/), sends trace data. The more services you instrument, the clearer the end-to-end view.
- **Incorporate [CloudWatch Real User Monitoring](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html) and [synthetic monitoring](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html):** Integrate Real User Monitoring (RUM) and synthetic monitoring with X-Ray. This allows for capturing real-world user experiences and simulating user interactions to identify potential issues.
- **Use the [CloudWatch agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html):** The agent can send traces from either X-Ray or OpenTelemetry, enhancing the depth of insights obtained.
- **Use [Amazon DevOps Guru](https://aws.amazon.com/devops-guru/):** DevOps Guru uses data from X-Ray, CloudWatch, AWS Config, and AWS CloudTrail to provide actionable recommendations.
- **Analyze traces:** Regularly review the trace data to discern patterns, anomalies, or bottlenecks that might impact your application's performance.
- **Set up alerts:** Configure alarms in [CloudWatch](https://aws.amazon.com/cloudwatch/) for unusual patterns or extended latencies, allowing proactive issue addressing.
- **Continuous improvement:** Revisit your tracing strategy as services are added or modified to capture all relevant data points.

**Level of effort for the implementation plan:** Medium

## Resources

**Related best practices:**

- OPS04-BP01 Identify key performance indicators
- OPS04-BP02 Implement application telemetry
- OPS04-BP03 Implement user experience telemetry
- OPS04-BP04 Implement dependency telemetry

**Related documents:**

- [AWS X-Ray Developer Guide](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
- [Amazon CloudWatch agent User Guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [Amazon DevOps Guru User Guide](https://docs.aws.amazon.com/devops-guru/latest/userguide/welcome.html)

**Related videos:**

- [Use AWS X-Ray Insights](https://www.youtube.com/watch?v=tl8OWHl6jxw)
- [AWS on Air ft. Observability: Amazon CloudWatch and AWS X-Ray](https://www.youtube.com/watch?v=qBDBnPkZ-KI)

**Related examples:**

- [Instrumenting your application for AWS X-Ray](https://aws.amazon.com/xray/latest/devguide/xray-instrumenting-your-app.html)
