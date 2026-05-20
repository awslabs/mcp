---
id: "PERF01-BP03"
title: "Factor cost into architectural decisions"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you select appropriate cloud resources and architecture for your workload?"
risk_level: "Medium"
---

# PERF01-BP03 Factor cost into architectural decisions

## Anti-Patterns
- You only use one family of instances.
- You do not evaluate licensed solutions against open-source solutions.
- You do not define storage lifecycle policies.
- You do not review new services and features of the AWS Cloud.
- You only use block storage.

## Implementation Guidance
 Optimizing workloads for cost can improve resource utilization and avoid waste in a cloud workload. Factoring cost into architectural decisions usually includes right-sizing workload components and enabling elasticity, which results in improved cloud workload performance efficiency.

## Implementation Steps
- Establish cost objectives like budget limits for your cloud workload.
- Identify the key components (like instances and storage) that drive cost of your workload. You can use [AWS Pricing Calculator](https://calculator.aws/#/) and [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) to identify key cost drivers in your workload.
- Understand [pricing models](https://aws.amazon.com/pricing/) in the cloud, such as On-Demand, Reserved Instances, Savings Plans, and Spot Instances.
- Use [Well-Architected cost optimization best practices](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html) to optimize these key components for cost.
- Continually monitor and analyze cost to identify cost optimization opportunities in your workload.
  - Use [AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/) to get alerts for unacceptable costs.
  - Use [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/) or [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/) to get cost optimization recommendations.
  - Use [AWS Cost Anomaly Detection](https://aws.amazon.com/aws-cost-management/aws-cost-anomaly-detection/) to get automated cost anomaly detection and root cause analysis.

## Resources
### Related Documents
- [ What is AWS Billing and Cost Management? ](https://docs.aws.amazon.com/cost-management/latest/userguide/what-is-costmanagement.html)
- [ Cost Optimization with AWS](https://aws.amazon.com/aws-cost-management/cost-optimization/)
- [ Choosing an AWS cost management strategy ](https://aws.amazon.com/getting-started/decision-guides/cost-management-on-aws-how-to-choose/)
- [ A Beginner’s Guide to AWS Cost Management ](https://aws.amazon.com/blogs/aws-cloud-financial-management/beginners-guide-to-aws-cost-management/)
- [A Detailed Overview of the Cost Intelligence Dashboard](https://aws.amazon.com/blogs/aws-cloud-financial-management/a-detailed-overview-of-the-cost-intelligence-dashboard/)
- [AWS Architecture Center](https://aws.amazon.com/architecture/)
- [AWS Solutions Library](https://aws.amazon.com/solutions/)
- [AWS Knowledge Center](https://aws.amazon.com/premiumsupport/knowledge-center/)
### Related Videos
- [This is my Architecture](https://aws.amazon.com/architecture/this-is-my-architecture/)
- [AWS re:Invent 2023 - What’s new with AWS cost optimization ](https://www.youtube.com/watch?v=EOUTf2Dxo0Y)
- [AWS re:Invent 2023 - Optimize cost and performance and track progress toward mitigation ](https://www.youtube.com/watch?v=keAfy8f84E0)
- [AWS re:Invent 2023 - AWS storage cost-optimization best practices ](https://www.youtube.com/watch?v=8LVKNHcA6RY)
- [AWS re:Invent 2023 - Optimize costs in your multi-account environments ](https://www.youtube.com/watch?v=ie_Mqb-eC4A)
### Related Examples
- [AWS Compute Optimizer Demo code ](https://github.com/awslabs/ec2-spot-labs/tree/master/aws-compute-optimizer)
- [ Cost Optimization Workshop ](https://catalog.us-east-1.prod.workshops.aws/workshops/11959269-3506-4bcb-aa2a-f257709cb8ca/en-US)
- [ Cloud Financial Management Technical Implementation Playbooks ](https://catalog.workshops.aws/awscff/en-US)
- [ Startup optimization: Tuning application performance for maximum efficiency ](https://catalog.workshops.aws/performance-tuning/en-US)
- [ Serverless Optimization Workshop (Performance and Cost) ](https://catalog.us-east-1.prod.workshops.aws/workshops/2d960419-7d15-44e7-b540-fd3ebeb7ce2e/en-US)
- [ Scaling cost effective architectures ](https://catalog.us-east-1.prod.workshops.aws/workshops/f238037c-8f0b-446e-9c15-ebcc4908901a/en-US)
