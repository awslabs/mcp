---
id: "REL06-BP01"
title: "Monitor all components for the workload (Generation)"
pillar: "Reliability"
risk_level: "HIGH"
capability: "How do you monitor workload resources?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_monitor_aws_resources_monitor_resources.html"
description: "Monitor the components of the workload with Amazon CloudWatch or third-party tools. Monitor AWS services with AWS Health Dashboard."
area: ["Change management", "Monitor workload resources"]
relatedIds: ["REL11-BP03"]
---

# REL06-BP01 Monitor all components for the workload (Generation)

Monitor the components of the workload with Amazon CloudWatch or
third-party tools. Monitor AWS services with AWS Health Dashboard.

All components of your workload should be monitored, including the
front-end, business logic, and storage tiers. Define key metrics,
describe how to extract them from logs (if necessary), and set
thresholds for invoking corresponding alarm events. Ensure metrics
are relevant to the key performance indicators (KPIs) of your
workload, and use metrics and logs to identify early warning signs
of service degradation. For example, a metric related to business
outcomes such as the number of orders successfully processed per
minute, can indicate workload issues faster than technical metric,
such as CPU Utilization. Use AWS Health Dashboard for a personalized
view into the performance and availability of the AWS services
underlying your AWS resources.

Monitoring in the cloud offers new opportunities. Most cloud
providers have developed customizable hooks and can deliver insights
to help you monitor multiple layers of your workload. AWS services
such as Amazon CloudWatch apply statistical and machine learning
algorithms to continually analyze metrics of systems and
applications, determine normal baselines, and surface anomalies with
minimal user intervention. Anomaly detection algorithms account for
the seasonality and trend changes of metrics.

AWS makes an abundance of monitoring and log information available
for consumption that can be used to define workload-specific
metrics, change-in-demand processes, and adopt machine learning
techniques regardless of ML expertise.

In addition, monitor all of your external endpoints to ensure that
they are independent of your base implementation. This active
monitoring can be done with synthetic transactions (sometimes
referred to as *user canaries*, but not to be
confused with canary deployments) which periodically run a number of
common tasks matching actions performed by clients of the workload.
Keep these tasks short in duration and be sure not to overload your
workload during testing. Amazon CloudWatch Synthetics allows you
to [create
synthetic canaries](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html) to monitor your endpoints and APIs. You
can also combine the synthetic canary client nodes with AWS X-Ray
console to pinpoint which synthetic canaries are experiencing issues
with errors, faults, or throttling rates for the selected time
frame.

**Desired Outcome:**

Collect and use critical metrics from all components of the workload
to ensure workload reliability and optimal user experience.
Detecting that a workload is not achieving business outcomes allows
you to quickly declare a disaster and recover from an incident.

**Common anti-patterns:**

- Only monitoring external interfaces to your workload.
- Not generating any workload-specific metrics and only relying on
metrics provided to you by the AWS services your workload uses.
- Only using technical metrics in your workload and not monitoring
any metrics related to non-technical KPIs the workload
contributes to.
- Relying on production traffic and simple health checks to
monitor and evaluate workload state.

**Benefits of establishing this best
practice:** Monitoring at all tiers in your workload
allows you to more rapidly anticipate and resolve problems in the
components that comprise the workload.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

- **Turn on logging where
available.** Monitoring data should be obtained from
all components of the workloads. Turn on additional logging,
such as S3 Access Logs, and permit your workload to log
workload specific data. Collect metrics for CPU, network I/O,
and disk I/O averages from services such as Amazon ECS, Amazon EKS, Amazon EC2, Elastic Load Balancing, AWS Auto Scaling, and
Amazon EMR. See
[AWS Services That Publish CloudWatch Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CW_Support_For_AWS.html) for a list of
AWS services that publish metrics to CloudWatch.
- **Review all default metrics and explore
any data collection gaps.** Every service generates
default metrics. Collecting default metrics allows you to
better understand the dependencies between workload
components, and how component reliability and performance
affect the workload. You can also create and
[publish
your own metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html) to CloudWatch using the AWS CLI or an
API.
- **Evaluate all the metrics to decide
which ones to alert on for each AWS service in your
workload.** You may choose to select a subset of
metrics that have a major impact on workload reliability.
Focusing on critical metrics and threshold allows you to
refine the number of
[alerts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
and can help minimize false-positives.
- **Define alerts and the recovery process
for your workload after the alert is invoked.**
Defining alerts allows you to quickly notify, escalate, and
follow steps necessary to recover from an incident and meet
your prescribed Recovery Time Objective (RTO). You can use
[Amazon CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html#alarms-and-actions) to invoke automated
workflows and initiate recovery procedures based on defined
thresholds.
- **Explore use of synthetic transactions
to collect relevant data about workloads state.**
Synthetic monitoring follows the same routes and perform the
same actions as a customer, which makes it possible for you to
continually verify your customer experience even when you
don't have any customer traffic on your workloads. By using
[synthetic
transactions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html), you can discover issues before your
customers do.

## Resources

**Related best practices:**

- REL11-BP03 Automate healing on all layers

**Related documents:**

- [Getting
started with your AWS Health Dashboard – Your account
health](https://docs.aws.amazon.com/health/latest/ug/getting-started-health-dashboard.html)
- [AWS Services That Publish CloudWatch Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CW_Support_For_AWS.html)
- [Access
Logs for Your Network Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-access-logs.html)
- [Access
logs for your application load balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html)
- [Accessing
Amazon CloudWatch Logs for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-functions-logs.html)
- [Amazon S3 Server Access Logging](https://docs.aws.amazon.com/AmazonS3/latest/dev/ServerLogs.html)
- [Enable
Access Logs for Your Classic Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/enable-access-logs.html)
- [Exporting
log data to Amazon S3](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/S3Export.html)
- [Install
the CloudWatch agent on an Amazon EC2 instance](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Agent-on-EC2-Instance.html)
- [Publishing
Custom Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html)
- [Using
Amazon CloudWatch Dashboards](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html)
- [Using
Amazon CloudWatch Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html)
- [Using
Canaries (Amazon CloudWatch Synthetics)](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html)
- [What
are Amazon CloudWatch Logs?](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html)

**User guides:**
- [Creating
a trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-create-a-trail-using-the-console-first-time.html)
- [Monitoring
memory and disk metrics for Amazon EC2 Linux instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/mon-scripts.html)
- [Using
CloudWatch Logs with container instances](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_cloudwatch_logs.html)
- [VPC
Flow Logs](https://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/flow-logs.html)
- [What
is Amazon DevOps Guru?](https://docs.aws.amazon.com/devops-guru/latest/userguide/welcome.html)
- [What
is AWS X-Ray?](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)

**Related blogs:**

- [Debugging
with Amazon CloudWatch Synthetics and AWS X-Ray](https://aws.amazon.com/blogs/devops/debugging-with-amazon-cloudwatch-synthetics-and-aws-x-ray/)

**Related examples:**

- [The
Amazon Builders' Library: Instrumenting distributed systems
for operational visibility](https://aws.amazon.com/builders-library/instrumenting-distributed-systems-for-operational-visibility/)
- [Observability
workshop](https://catalog.workshops.aws/observability/en-US)
