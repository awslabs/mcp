---
id: "PERF05-BP04"
title: "Load test your workload"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do your organizational practices and culture contribute to performance efficiency in your workload?"
risk_level: "Low"
---

# PERF05-BP04 Load test your workload

## Anti-Patterns
- You load test individual parts of your workload but not your entire workload.
- You load test on infrastructure that is not the same as your production environment.
- You only conduct load testing to your expected load and not beyond, to help foresee where you may have future problems.
- You perform load testing without consulting the [Amazon EC2 Testing Policy](https://aws.amazon.com/ec2/testing/) and submitting a Simulated Event Submissions Form. This results in your test failing to run, as it looks like a denial-of-service event.

## Implementation Guidance
 Load testing in the cloud is a process to measure the performance of cloud workload under realistic conditions with expected user load. This process involves provisioning a production-like cloud environment, using load testing tools to generate load, and analyzing metrics to assess the ability of your workload handling a realistic load. Load tests must be run using synthetic or sanitized versions of production data (remove sensitive or identifying information). Automatically carry out load tests as part of your delivery pipeline, and compare the results against pre-defined KPIs and thresholds. This process helps you continue to achieve required performance.

## Implementation Steps
- **Define your testing objectives:** Identify the performance aspects of your workload that you want to evaluate, such as throughput and response time.
- **Select a testing tool:** Choose and configure the load testing tool that suits your workload.
- **Set up your environment:** Set up the test environment based on your production environment. You can use AWS services to run production-scale environments to test your architecture.
- **Implement monitoring:** Use monitoring tools such as [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) to collect metrics across the resources in your architecture. You can also collect and publish custom metrics.
- **Define scenarios:** Define the load testing scenarios and parameters (like test duration and number of users).
- **Conduct load testing:** Perform test scenarios at scale. Take advantage of the AWS Cloud to test your workload to discover where it fails to scale, or if it scales in a non-linear way. For example, use Spot Instances to generate loads at low cost and discover bottlenecks before they are experienced in production.
- **Analyze test results:** Analyze the results to identify performance bottlenecks and areas for improvements.
- **Document and share findings:** Document and report on findings and recommendations. Share this information with stakeholders to help them make informed decision regarding performance optimization strategies.
- **Continually iterate:** Load testing should be performed at regular cadence, especially after a system change of update.

## Resources
### Related Documents
- [Amazon CloudWatch RUM](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html)
- [Amazon CloudWatch Synthetics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html)
- [Distributed Load Testing on AWS](https://docs.aws.amazon.com/solutions/latest/distributed-load-testing-on-aws/welcome.html)
### Related Videos
- [AWS Summit ANZ 2023: Accelerate with confidence through AWS Distributed Load Testing ](https://www.youtube.com/watch?v=4J6lVqa6Yh8)
- [AWS re:Invent 2022 - Scaling on AWS for your first 10 million users ](https://www.youtube.com/watch?v=yrP3M4_13QM)
- [Solving with AWS Solutions: Distributed Load Testing](https://www.youtube.com/watch?v=Y-2rk0sSyOM)
- [AWS re:Invent 2021 - Optimize applications through end user insights with Amazon CloudWatch RUM ](https://www.youtube.com/watch?v=NMaeujY9A9Y)
- [Demo of Amazon CloudWatch Synthetics](https://www.youtube.com/watch?v=hF3NM9j-u7I)
### Related Examples
- [Distributed Load Testing on AWS](https://aws.amazon.com/solutions/implementations/distributed-load-testing-on-aws/)
