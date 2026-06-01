---
id: "REL11-BP01"
title: "Monitor all components of the workload to detect failures"
pillar: "Reliability"
risk_level: "HIGH"
capability: "How do you design your workload to withstand component failures?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_monitoring_health.html"
description: "Continually monitor the health of your workload so that you and your automated systems are aware of failures or degradations as soon as they occur. Monitor for key performance indicators (KPIs) based on business value."
area: ["Failure management", "Design your workload to withstand component failures"]
relatedIds: ["REL11-BP06"]
---

# REL11-BP01 Monitor all components of the workload to detect failures

Continually monitor the health of your workload so that you and your
automated systems are aware of failures or degradations as soon as
they occur. Monitor for key performance indicators (KPIs) based on
business value.

All recovery and healing mechanisms must start with the ability to
detect problems quickly. Technical failures should be detected first
so that they can be resolved. However, availability is based on the
ability of your workload to deliver business value, so key
performance indicators (KPIs) that measure this need to be a part of
your detection and remediation strategy.

**Desired outcome:** Essential components of a workload are monitored independently to
detect and alert on failures when and where they happen.

**Common anti-patterns:**

- No alarms have been configured, so outages occur without
notification.
- Alarms exist, but at thresholds that don't provide adequate time
to react.
- Metrics are not collected often enough to meet the recovery time
objective (RTO).
- Only the customer facing interfaces of the workload are actively
monitored.
- Only collecting technical metrics, no business function metrics.
- No metrics measuring the user experience of the workload.
- Too many monitors are created.

**Benefits of establishing this best
practice:** Having appropriate monitoring at all layers allows you to reduce
recovery time by reducing time to detection.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Identify all workloads that will be reviewed for monitoring. Once
you have identified all components of the workload that will need
to monitored, you will now need to determine the monitoring
interval. The monitoring interval will have a direct impact on how
fast recovery can be initiated based on the time it takes to
detect a failure. The mean time to detection (MTTD) is the amount
of time between a failure occurring and when repair operations
begin. The list of services should be extensive and complete.

Monitoring must cover all layers of the application stack
including application, platform, infrastructure, and network.

Your monitoring strategy should consider the impact of
*gray failures*. For more detail on gray
failures, see
[Gray failures](https://docs.aws.amazon.com/whitepapers/latest/advanced-multi-az-resilience-patterns/gray-failures.html) in the Advanced Multi-AZ Resilience Patterns whitepaper.

### Implementation steps

- Your monitoring interval is dependent on how quickly you
must recover. Your recovery time is driven by the time it
takes to recover, so you must determine the frequency of
collection by accounting for this time and your recovery
time objective (RTO).
- Configure detailed monitoring for components and managed
services.

Determine if
[detailed
monitoring for EC2 instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-cloudwatch-new.html) and
[Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-instance-monitoring.html) is necessary. Detailed monitoring
provides one minute interval metrics, and default
monitoring provides five minute interval metrics.
- Determine if
[enhanced
monitoring](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Monitoring.html) for RDS is necessary. Enhanced
monitoring uses an agent on RDS instances to get useful
information about different process or threads.
- Determine the monitoring requirements of critical
serverless components for
[Lambda](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics.html),
[API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/monitoring_automated_manual.html),
[Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/eks-observe.html),
[Amazon ECS](https://catalog.workshops.aws/observability/en-US/aws-managed-oss/amp/ecs),
and all types of
[load
balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-monitoring.html).
- Determine the monitoring requirements of storage
components for
[Amazon S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/monitoring-overview.html),
[Amazon FSx](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/monitoring_overview.html),
[Amazon EFS](https://docs.aws.amazon.com/efs/latest/ug/monitoring_overview.html),
and
[Amazon EBS](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-volume-status.html).

- Create
[custom
metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html) to measure business key performance
indicators (KPIs). Workloads implement key business
functions, which should be used as KPIs that help identify
when an indirect problem happens.
- Monitor the user experience for failures using user
canaries.
[Synthetic
transaction testing](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html) (also known as canary testing,
but not to be confused with canary deployments) that can run
and simulate customer behavior is among the most important
testing processes. Run these tests constantly against your
workload endpoints from diverse remote locations.
- Create
[custom
metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html) that track the user's experience. If you can
instrument the experience of the customer, you can determine
when the consumer experience degrades.
- [Set
alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html) to detect when any part of your workload is
not working properly and to indicate when to automatically
scale resources. Alarms can be visually displayed on
dashboards, send alerts through Amazon SNS or email, and
work with Auto Scaling to scale workload resources up or
down.
- Create
[dashboards](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html)
to visualize your metrics. Dashboards can be used to
visually see trends, outliers, and other indicators of
potential problems or to provide an indication of problems
you may want to investigate.
- Create
[distributed
tracing monitoring](https://aws.amazon.com/xray/faqs/) for your services. With
distributed monitoring, you can understand how your
application and its underlying services are performing to
identify and troubleshoot the root cause of performance
issues and errors.
- Create monitoring systems (using
[CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_xaxr_dashboard.html)
or
[X-Ray](https://aws.amazon.com/xray/faqs/))
dashboards and data collection in a separate Region and
account.
- Stay informed about service degradations with [AWS Health](https://aws.amazon.com/premiumsupport/technology/aws-health/). [Create purpose-fit AWS Health event notifications](https://docs.aws.amazon.com/health/latest/ug/user-notifications.html) to e-mail and chat channels through [AWS User Notifications](https://docs.aws.amazon.com/notifications/latest/userguide/what-is-service.html) and integrate programmatically with [your monitoring and alerting tools through Amazon EventBridge](https://docs.aws.amazon.com/health/latest/ug/cloudwatch-events-health.html).

## Resources

**Related best practices:**

- [Availability
Definition](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/availability.html)
- [REL11-BP06
Send Notifications when events impact availability](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_notifications_sent_system.html)

**Related documents:**

- [Amazon CloudWatch Synthetics enables you to create user
canaries](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html)
- [Enable
or Disable Detailed Monitoring for Your Instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-cloudwatch-new.html)
- [Enhanced
Monitoring](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_Monitoring.OS.html)
- [Monitoring
Your Auto Scaling Groups and Instances Using Amazon CloudWatch](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-instance-monitoring.html)
- [Publishing
Custom Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html)
- [Using
Amazon CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [Using
CloudWatch Dashboards](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html)
- [Using
Cross Region Cross Account CloudWatch Dashboards](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_xaxr_dashboard.html)
- [Using
Cross Region Cross Account X-Ray Tracing](https://aws.amazon.com/xray/faqs/)
- [Understanding
availability](https://docs.aws.amazon.com/whitepapers/latest/availability-and-beyond-improving-resilience/understanding-availability.html)

**Related videos:**

- [Mitigating
gray failures](https://docs.aws.amazon.com/whitepapers/latest/advanced-multi-az-resilience-patterns/gray-failures.html)

**Related examples:**

- [One
Observability Workshop: Explore X-Ray](https://catalog.workshops.aws/observability/en-US/aws-native/xray/explore-xray)

**Related tools:**

- [CloudWatch](https://aws.amazon.com/cloudwatch/)
- [CloudWatch
X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/security-logging-monitoring.html)
