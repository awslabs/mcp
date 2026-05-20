---
id: "SUS03-BP02"
title: "Remove or refactor workload components with low or no use"
framework: "WAF"
domain: "Sustainability"
capability: "How do you take advantage of software and architecture patterns to support your sustainability goals?"
risk_level: "Medium"
---

# SUS03-BP02 Remove or refactor workload components with low or no use

## Anti-Patterns
- You do not regularly check the utilization level of individual components of your workload.
- You do not check and analyze recommendations from AWS rightsizing tools such as [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/).

## Implementation Guidance
Unused or underutilized components in a cloud workload consume unnecessary compute, storage or network resources. Remove or refactor these components to directly reduce waste and improve the overall efficiency of a cloud workload. This is an iterative improvement process which can be initiated by changes in demand or the release of a new cloud service. For example, a significant drop in [AWS Lambda](https://docs.aws.amazon.com/lambda/) function run time can be indicate a need to lower the memory size. Also, as AWS releases new services and features, the optimal services and architecture for your workload may change.

 Continually monitor workload activity and look for opportunities to improve the utilization level of individual components. By removing idle components and performing rightsizing activities, you meet your business requirements with the fewest cloud resources.

## Implementation Steps
- **Inventory your AWS resourceds:** Create an inventory of your AWS resources. In AWS, you can turn on [AWS Resource Explorer](https://docs.aws.amazon.com/resource-explorer/latest/userguide/welcome.html) to explore and organize your AWS resources. For more details, see [AWS re:Invent 2022 - How to manage resources and applications at scale on AWS](https://www.youtube.com/watch?v=bbgUnKq6PAU).
- **Monitor utilization:** Monitor and capture the utilization metrics for critical components of your workload (like CPU utilization, memory utilization, or network throughput in [Amazon CloudWatch metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html)).
- **Identify unused components: **Identify unused or under-utilized components in your architecture.
  - For stable workloads, check AWS rightsizing tools such as [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/) at regular intervals to identify idle, unused, or underutilized components.
  - For ephemeral workloads, evaluate utilization metrics to identify idle, unused, or underutilized components.
- **Remove unused components:** Retire components and associated assets (like Amazon ECR images) that are no longer needed.
  - [ Automated Cleanup of Unused Images in Amazon ECR ](https://aws.amazon.com/blogs/compute/automated-cleanup-of-unused-images-in-amazon-ecr/)
  - [ Delete unused Amazon Elastic Block Store (Amazon EBS) volumes by using AWS Config and AWS Systems Manager](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/delete-unused-amazon-elastic-block-store-amazon-ebs-volumes-by-using-aws-config-and-aws-systems-manager.html)
- **Refactor underutilized components:** Refactor or consolidate underutilized components with other resources to improve utilization efficiency. For example, you can provision multiple small databases on a single [Amazon RDS](https://aws.amazon.com/rds/) database instance instead of running databases on individual underutilized instances.
- **Evaluate improvements:** Understand the [resources provisioned by your workload to complete a unit of work](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/evaluate-specific-improvements.html). Use this information to evaluate improvements achieved by removing or refactoring components.
  - [ Measure and track cloud efficiency with sustainability proxy metrics, Part I: What are proxy metrics? ](https://aws.amazon.com/blogs/aws-cloud-financial-management/measure-and-track-cloud-efficiency-with-sustainability-proxy-metrics-part-i-what-are-proxy-metrics/)
  - [ Measure and track cloud efficiency with sustainability proxy metrics, Part II: Establish a metrics pipeline ](https://aws.amazon.com/blogs/aws-cloud-financial-management/measure-and-track-cloud-efficiency-with-sustainability-proxy-metrics-part-ii-establish-a-metrics-pipeline/)

## Resources
### Related Documents
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
- [What is Amazon CloudWatch?](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
- [ Right Sizing: Provisioning Instances to Match Workloads ](https://docs.aws.amazon.com/whitepapers/latest/cost-optimization-right-sizing/cost-optimization-right-sizing.html)
- [ Optimizing your cost with Rightsizing Recommendations ](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-rightsizing.html)
### Related Videos
- [AWS re:Invent 2023 - Capacity, availability, cost efficiency: Pick three ](https://www.youtube.com/watch?v=E0dYLPXrX_w)
