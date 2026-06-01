---
id: "REL12-BP03"
title: "Test scalability and performance requirements"
pillar: "Reliability"
risk_level: "HIGH"
capability: "How do you test reliability?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_testing_resiliency_test_non_functional.html"
description: "Use techniques such as load testing to validate that the workload meets scaling and performance requirements."
area: ["Failure management", "Test reliability"]
relatedIds: ["REL01-BP04", "REL06-BP01", "REL06-BP03"]
---

# REL12-BP03 Test scalability and performance requirements

Use techniques such as load testing to validate that the workload
meets scaling and performance requirements.

In the cloud, you can create a production-scale test environment for
your workload on demand. Instead of reliance on a scaled-down test
environment, which could lead to inaccurate predictions of
production behaviors, you can use the cloud to provision a test
environment that closely mirrors your expected production
environment. This environment helps you test in a more accurate
simulation of the real-world conditions your application faces.

Alongside your performance testing efforts, it's essential to
validate that your base resources, scaling settings, service quotas,
and resiliency design operate as expected under load. This holistic
approach verifies that your application can reliably scale and
perform as required, even under the most demanding conditions.

**Desired outcome:** Your workload
maintains its expected behavior even while subject to peak load. You
proactively address any performance-related issues that may arise as
the application grows and evolves.

**Common anti-patterns:**

- You use test environments that do not closely match the
production environment.
- You treat load testing as a separate, one-time activity rather
than an integrated part of the deployment continuous integration
(CI) pipeline.
- You don't define clear and measurable performance requirements,
such as response time, throughput, and scalability targets.
- You perform tests with unrealistic or insufficient load
scenarios, and you fail to test for peak loads, sudden spikes,
and sustained high load.
- You don't stress test the workload by exceeding expected load
limits.
- You use inadequate or inappropriate load testing and performance
profiling tools.
- You lack comprehensive monitoring and alerting systems to track
performance metrics and detect anomalies.

**Benefits of establishing this best
practice:**

- Load testing helps you identify potential performance
bottlenecks in your system before it goes into production. When
you simulate production-level traffic and workloads, you can
identify areas where your system may struggle to handle the
load, such as slow response times, resource constraints, or
system failures.
- As you test your system under various load conditions, you can
better understand the resource requirements needed to support
your workload. This information can help you make informed
decisions about resource allocation and prevent
over-provisioning or under-provisioning of resources.
- To identify potential failure points, you can observe how your
workload performs under high load conditions. This information
helps you improve your workload's reliability and resiliency by
implementing fault-tolerance mechanisms, failover strategies,
and redundancy measures, as appropriate.
- You identify and address performance issues early, which helps
you avoid the costly consequences of system outages, slow
response times, and dissatisfied users.
- Detailed performance data and profiling information collected
during testing can help you troubleshoot performance-related
issues that may arise in production. This can lead to faster
incident response and resolution, which reduces the impact on
users and your organization's operations.
- In certain industries, proactive performance testing can help
your workload meet compliance standards, which reduces the risk
of penalties or legal issues.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

The first step is to define a comprehensive testing strategy that
covers all aspects of scaling and performance requirements. To
start, clearly define your workload's service-level objectives
(SLOs) based on your business needs, such as throughput, latency
histogram, and error rate. Next, design a suite of tests that can
simulate various load scenarios that range from average usage to
sudden spikes and sustained peak loads, and verify that the
workload's behavior meets your SLOs. These tests should be
automated and integrated into your continuous integration and
deployment pipeline to catch performance regressions early in the
development process.

To effectively test scaling and performance, invest in the right
tools and infrastructure. This includes load testing tools that
can generate realistic user traffic, performance profiling tools
to identify bottlenecks, and monitoring solutions to track key
metrics. Importantly, you should verify that your test
environments closely match the production environment in terms of
infrastructure and environment conditions to make your test
results as accurate as possible. To make it easier to reliably
replicate and scale production-like setups, use infrastructure as
code and container-based applications.

Scaling and performance tests are an ongoing process, not a
one-time activity. Implement comprehensive monitoring and alerting
to track the application's performance in production, and use this
data to continually refine your test strategies and optimization
efforts. Regularly analyze performance data to identify emerging
issues, test new scaling strategies, and implement optimizations
to improve the application's efficiency and reliability. When you
adopt an iterative approach and constantly learn from production
data, you can verify that your application can adapt to variable
user demands and maintain resiliency and optimal performance over
time.

### Implementation steps

- Establish clear and measurable performance requirements,
such as response time, throughput, and scalability targets.
These requirements should be based on your workload's usage
patterns, user expectations, and business needs.
- Select and configure a load testing tool that can accurately
mimic the load patterns and user behavior in your production
environment.
- Set up a test environment that closely matches the
production environment, including infrastructure and
environment conditions, to improve the accuracy of your test
results.
- Create a test suite that covers a wide range of scenarios,
from average usage patterns to peak loads, rapid spikes, and
sustained high loads. Integrate the tests into your
continuous integration and deployment pipelines to catch
performance regressions early in the development process.
- Conduct load testing to simulate real-world user traffic and
understand how your application behaves under different load
conditions. To stress test your application, exceed the
expected load and observe its behavior, such as response
time degradation, resource exhaustion, or system failures,
which helps identify the breaking point of your application
and inform scaling strategies. Evaluate the scalability of
your workload by incrementally increasing the load, and
measure the performance impact to identify scaling limits
and plan for future capacity needs.
- Implement comprehensive monitoring and alerting to track
performance metrics, detect anomalies, and initiate scaling
actions or notifications when thresholds are exceeded.
- Continually monitor and analyze performance data to identify
areas for improvement. Iterate on your testing strategies
and optimization efforts.

## Resources

**Related best practices:**

- [REL01-BP04
Monitor and manage quotas](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_manage_service_limits_monitor_manage_limits.html)
- [REL06-BP01
Monitor all components for the workload (Generation)](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_monitor_aws_resources_monitor_resources.html)
- [REL06-BP03
Send notifications (Real-time processing and alarming)](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_monitor_aws_resources_notification_monitor.html))

**Related documents:**

- [Load
testing applications](https://docs.aws.amazon.com/prescriptive-guidance/latest/load-testing/welcome.html)
- [Distributed
Load Testing on AWS](https://aws.amazon.com/solutions/implementations/distributed-load-testing-on-aws/)
- [Application
Performance Monitoring](https://aws.amazon.com/what-is/application-performance-monitoring/)
- [Amazon EC2 Testing Policy](https://aws.amazon.com/ec2/testing/)

**Related examples:**

- [Distributed
Load Testing on AWS (GitHub)](https://github.com/aws-solutions/distributed-load-testing-on-aws)

**Related tools:**

- [Amazon CodeGuru Profiler](https://docs.aws.amazon.com/codeguru/latest/profiler-ug/what-is-codeguru-profiler.html)
- [Amazon CloudWatch RUM](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html)
- [Apache
JMeter](https://jmeter.apache.org/)
- [K6](https://k6.io/)
- [Vegeta](https://github.com/tsenart/vegeta)
- [Hey](https://github.com/rakyll/hey)
- [ab](https://httpd.apache.org/docs/2.4/programs/ab.html)
- [wrk](https://github.com/wg/wrk)
- [Distributed Load Testing on AWS](https://aws.amazon.com/solutions/implementations/distributed-load-testing-on-aws/)
