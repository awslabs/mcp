---
id: "PERF01-BP06"
title: "Use benchmarking to drive architectural decisions"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you select appropriate cloud resources and architecture for your workload?"
risk_level: "Medium"
---

# PERF01-BP06 Use benchmarking to drive architectural decisions

## Anti-Patterns
- You rely on common benchmarks that are not indicative of your workload’s characteristics.
- You rely on customer feedback and perceptions as your only benchmark.

## Implementation Guidance
 Use benchmarking with synthetic tests to assess how your workload’s components perform. Benchmarking is generally quicker to set up than load testing and is used to evaluate the technology for a particular component. Benchmarking is often used at the start of a new project, when you lack a full solution to load test.

 You can either build your own custom benchmark tests or use an industry standard test, such as [TPC-DS](http://www.tpc.org/tpcds/), to benchmark your workloads. Industry benchmarks are helpful when comparing environments. Custom benchmarks are useful for targeting specific types of operations that you expect to make in your architecture.

 When benchmarking, it is important to pre-warm your test environment to get valid results. Run the same benchmark multiple times to verify that you’ve captured any variance over time.

 Because benchmarks are generally faster to run than load tests, they can be used earlier in the deployment pipeline and provide faster feedback on performance deviations. When you evaluate a significant change in a component or service, a benchmark can be a quick way to see if you can justify the effort to make the change. Using benchmarking in conjunction with load testing is important because load testing informs you about how your workload performs in production.

## Implementation Steps
- Plan and define:
  - Define the objectives, baseline, testing scenarios, metrics (like CPU utilization, latency, or throughput), and KPIs for your benchmark.
  - Focus on user requirements in terms of user experience and factors such as response time and accessibility.
  - Identify a benchmarking tool that is suitable for your workload. You can use AWS services like [Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html) or a third-party tool that is compatible with your workload.
- Configure and instrument:
  - Set up your environment and configure your resources.
  - Implement monitoring and logging to capture testing results.
- Benchmark and monitor:
  - Perform your benchmark tests and monitor the metrics during the test.
- Analyze and document:
  - Document your benchmarking process and findings.
  - Analyze the results to identify bottlenecks, trends, and areas of improvement.
  - Use test results to make architectural decisions and adjust your workload. This may include changing services or adopting new features.
- Optimize and repeat:
  - Adjust resource configurations and allocations based on your benchmarks.
  - Retest your workload after the adjustment to validate your improvements.
  - Document your learnings, and repeat the process to identify other areas of improvement.

## Resources
### Related Documents
- [AWS Architecture Center](https://aws.amazon.com/architecture/)
- [AWS Partner Network](https://aws.amazon.com/partners/)
- [AWS Solutions Library](https://aws.amazon.com/solutions/)
- [AWS Knowledge Center](https://aws.amazon.com/premiumsupport/knowledge-center/)
- [Amazon CloudWatch RUM](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html)
- [Amazon CloudWatch Synthetics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html)
- [Genomics workflows, Part 5: automated benchmarking](https://aws.amazon.com/blogs/architecture/genomics-workflows-part-5-automated-benchmarking/)
- [Benchmark and optimize endpoint deployment in Amazon SageMaker AI JumpStart](https://aws.amazon.com/blogs/machine-learning/benchmark-and-optimize-endpoint-deployment-in-amazon-sagemaker-jumpstart/)
### Related Videos
- [AWS re:Invent 2023 - Benchmarking AWS Lambda cold starts](https://www.youtube.com/watch?v=bGMEPI-va-Q&ab_channel=AWSEvents)
- [Benchmarking stateful services in the cloud](https://www.youtube.com/watch?v=rtW4a4DvcWU&ab_channel=AWSEvents)
- [This is my Architecture](https://aws.amazon.com/architecture/this-is-my-architecture/)
- [Optimize applications through Amazon CloudWatch RUM](https://www.youtube.com/watch?v=NMaeujY9A9Y)
- [Demo of Amazon CloudWatch Synthetics](https://www.youtube.com/watch?v=hF3NM9j-u7I)
### Related Examples
- [AWS Samples](https://github.com/aws-samples)
- [AWS SDK Examples](https://github.com/awsdocs/aws-doc-sdk-examples)
- [Distributed Load Tests](https://aws.amazon.com/solutions/implementations/distributed-load-testing-on-aws/)
- [Measure page load time with Amazon CloudWatch Synthetics](https://github.com/aws-samples/amazon-cloudwatch-synthetics-page-performance)
- [Amazon CloudWatch RUM Web Client](https://github.com/aws-observability/aws-rum-web)
