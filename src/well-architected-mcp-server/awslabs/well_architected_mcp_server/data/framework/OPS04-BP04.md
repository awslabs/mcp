---
id: "OPS04-BP04"
title: "Implement dependency telemetry"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How do you implement observability in your workload?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_observability_dependency_telemetry.html"
---

# OPS04-BP04 Implement dependency telemetry

Dependency telemetry is essential for monitoring the health and
performance of the external services and components your workload
relies on. It provides valuable insights into reachability,
timeouts, and other critical events related to dependencies such as
DNS, databases, or third-party APIs. When you instrument your
application to emit metrics, logs, and traces about these
dependencies, you gain a clearer understanding of potential
bottlenecks, performance issues, or failures that might impact your
workload.

**Desired outcome:** Ensure that the
dependencies your workload relies on are performing as expected,
allowing you to proactively address issues and ensure optimal
workload performance.

**Common anti-patterns:**

- **Overlooking external dependencies:** Focusing only on internal
application metrics while neglecting metrics related to external
dependencies.
- **Lack of proactive monitoring:** Waiting for issues to arise
instead of continuously monitoring dependency health and
performance.
- **Siloed monitoring:** Using multiple, disparate monitoring tools
which can result in fragmented and inconsistent views of
dependency health.

**Benefits of establishing this best
practice:**

- **Improved workload reliability:** By ensuring that external
dependencies are consistently available and performing
optimally.
- **Faster issue detection and resolution:** Proactively identifying
and addressing issues with dependencies before they impact the
workload.
- **Comprehensive view:** Gaining a holistic view of both internal and
external components that influence workload health.
- **Enhanced workload scalability:** By understanding the scalability
limits and performance characteristics of external dependencies.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Implement dependency telemetry by starting with identifying the
services, infrastructure, and processes that your workload depends
on. Quantify what good conditions look like when those
dependencies are functioning as expected, and then determine what
data will be needed to measure those. With that information you
can craft dashboards and alerts that provide insights to your
operations teams on the state of those dependencies. Use AWS tools
to discover and quantify the impacts when dependencies cannot
deliver as needed. Continually revisit your strategy to account
for changes in priorities, goals, and gained insights.

### Implementation steps

To implement dependency telemetry effectively:

- **Identify external
dependencies:** Collaborate with stakeholders to
pinpoint the external dependencies your workload relies on.
External dependencies can encompass services like external
databases, third-party APIs, network connectivity routes to
other environments, and DNS services. The first step towards
effective dependency telemetry is being comprehensive in
understanding what those dependencies are.
- **Develop a monitoring
strategy:** Once you have a clear picture of your
external dependencies, architect a monitoring strategy
tailored to them. This involves understanding the
criticality of each dependency, its expected behavior, and
any associated service-level agreements or targets (SLA or
SLTs). Set up proactive alerts to notify you of status
changes or performance deviations.
- **Use
[network
monitoring](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Network-Monitoring-Sections.html):** Use
[Internet
Monitor](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-InternetMonitor.html) and
[Network
Monitor](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/what-is-network-monitor.html), which provide comprehensive insights into
global internet and network conditions. These tools help you
understand and respond to outages, disruptions, or
performance degradations that affect your external
dependencies.
- **Stay informed with
[AWS Health](https://aws.amazon.com/premiumsupport/technology/aws-health/):** AWS Health is the authoritative source of information about the health of your AWS Cloud resources. Use AWS Health to visualize and receive notifications about any current service events and upcoming changes, such as planned lifecycle events, so you can take steps to mitigate impacts.

[Create purpose-fit AWS Health event notifications](https://docs.aws.amazon.com/health/latest/ug/user-notifications.html) to e-mail and chat channels through [AWS User Notifications](https://docs.aws.amazon.com/notifications/latest/userguide/what-is-service.html), and integrate programatically with [your monitoring and alerting tools through Amazon EventBridge](https://docs.aws.amazon.com/health/latest/ug/cloudwatch-events-health.html) or the [AWS Health API](https://docs.aws.amazon.com/health/latest/APIReference/Welcome.html).
- Plan and track progress on health events that require action by integrating with change management or ITSM tools (like [Jira](https://docs.aws.amazon.com/smc/latest/ag/cloud-sys-health.html) or [ServiceNow](https://docs.aws.amazon.com/smc/latest/ag/sn-aws-health.html)) that you may already use through Amazon EventBridge or the AWS Health API.
- If you use AWS Organizations, enable
[organization view for
AWS Health](https://docs.aws.amazon.com/health/latest/ug/aggregate-events.html) to aggregate AWS Health events across accounts.

- **Instrument your application with
[AWS X-Ray](https://aws.amazon.com/xray/):** AWS X-Ray provides insights into
how applications and their underlying dependencies are
performing. By tracing requests from start to end, you can
identify bottlenecks or failures in the external services or
components your application relies on.
- **Use
[Amazon DevOps Guru](https://aws.amazon.com/devops-guru/):** This machine learning-driven
service identifies operational issues, predicts when
critical issues might occur, and recommends specific actions
to take. It's invaluable for gaining insights into
dependencies and ensuring they're not the source of
operational problems.
- **Monitor regularly:**
Continually monitor metrics and logs related to external
dependencies. Set up alerts for unexpected behavior or
degraded performance.
- **Validate after changes:**
Whenever there's an update or change in any of the external
dependencies, validate their performance and check their
alignment with your application's requirements.

**Level of effort for the implementation
plan:** Medium

## Resources

**Related best practices:**

- [OPS04-BP01
Define workload KPIs](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_observability_identify_kpis.html)
- [OPS04-BP02
Implement application telemetry](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_observability_application_telemetry.html)
- [OPS04-BP03
Implement user activity telemetry](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_observability_customer_telemetry.html)
- [OPS04-BP05
Implement transaction traceability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_observability_dist_trace.html)
- [OP08-BP04
Create actionable alerts](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_workload_observability_create_alerts.html)

**Related documents:**

- [Amazon
Personal Health Dashboard User Guide](https://docs.aws.amazon.com/health/latest/ug/what-is-aws-health.html)
- [AWS Internet Monitor User Guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-InternetMonitor.html)
- [AWS X-Ray Developer Guide](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
- [AWS DevOps Guru User Guide](https://docs.aws.amazon.com/devops-guru/latest/userguide/welcome.html)

**Related videos:**

- [Visibility
into how internet issues impact app performance](https://www.youtube.com/watch?v=Kuc_SG_aBgQ)
- [Introduction
to Amazon DevOps Guru](https://www.youtube.com/watch?v=2uA8q-8mTZY)
- [Manage
resource lifecycle events at scale with AWS Health](https://www.youtube.com/watch?v=VoLLNL5j9NA)

**Related examples:**

- [AWS Health Aware](https://github.com/aws-samples/aws-health-aware/)
- [Using
Tag-Based Filtering to Manage AWS Health Monitoring and
Alerting at Scale](https://aws.amazon.com/blogs/mt/using-tag-based-filtering-to-manage-health-monitoring-and-alerting-at-scale/)
