---
id: "PERF02-BP04"
title: "Configure and right-size compute resources"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you select and use compute resources in your workload?"
risk_level: "Medium"
---

# PERF02-BP04 Configure and right-size compute resources

## Anti-Patterns
- You ignore your workload performance requirements resulting in over-provisioned or under-provisioned compute resources.
- You only choose the largest or smallest instance available for all workloads.
- You only use one instance family for ease of management.
- You ignore recommendations from AWS Cost Explorer or Compute Optimizer for right-sizing.
- You do not re-evaluate the workload for suitability of new instance types.
- You certify only a small number of instance configurations for your organization.

## Implementation Guidance
 Right-sizing allows organizations to operate their cloud infrastructure in an efficient and cost-effective manner while addressing their business needs. Over-provisioning cloud resources can lead to extra costs, while under-provisioning can result in poor performance and a negative customer experience. AWS provides tools such as [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/) and [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/) that use historical data to provide recommendations to right-size your compute resources.

## Implementation Steps
- Choose an instance type to best fit your needs:
  - [How do I choose the appropriate Amazon EC2 instance type for my workload?](https://aws.amazon.com/premiumsupport/knowledge-center/ec2-instance-choose-type-for-workload/)
  - [Attribute-based instance type selection for Amazon EC2 Fleet](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-fleet-attribute-based-instance-type-selection.html)
  - [Create an Auto Scaling group using attribute-based instance type selection](https://docs.aws.amazon.com/autoscaling/ec2/userguide/create-asg-instance-type-requirements.html)
  - [Optimizing your Kubernetes compute costs with Karpenter consolidation](https://aws.amazon.com/blogs/containers/optimizing-your-kubernetes-compute-costs-with-karpenter-consolidation/)
- Analyze the various performance characteristics of your workload and how these characteristics relate to memory, network, and CPU usage. Use this data to choose resources that best match your workload's profile and performance goals.
- Monitor your resource usage using AWS monitoring tools such as Amazon CloudWatch.
- Select the right configuration for compute resources.
  - For ephemeral workloads, evaluate [instance Amazon CloudWatch metrics](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/viewing_metrics_with_cloudwatch.html) such as `CPUUtilization` to identify if the instance is under-utilized or over-utilized.
  - For stable workloads, check AWS rightsizing tools such as AWS Compute Optimizer and AWS Trusted Advisor at regular intervals to identify opportunities to optimize and right-size the compute resource.
- Test configuration changes in a non-production environment before implementing in a live environment.
- Continually re-evaluate new compute offerings and compare against your workload’s needs.

## Resources
### Related Documents
- [Cloud Compute with AWS](https://aws.amazon.com/products/compute/)
- [Amazon EC2 Instance Types](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html)
- [Amazon ECS Containers: Amazon ECS Container Instances](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_instances.html)
- [Amazon EKS Containers: Amazon EKS Worker Nodes](https://docs.aws.amazon.com/eks/latest/userguide/worker.html)
- [Functions: Lambda Function Configuration](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html#function-configuration)
- [Processor State Control for Your Amazon EC2 Instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/processor_state_control.html)
### Related Videos
- [Amazon EC2 foundations](https://www.youtube.com/watch?v=kMMybKqC2Y0)
- [AWS re:Invent 2023 – AWS Graviton: The best price performance for your AWS workloads](https://www.youtube.com/watch?v=T_hMIjKtSr4)
- [AWS re:Invent 2023 – New Amazon EC2 generative AI capabilities in AWS Management Console](https://www.youtube.com/watch?v=sSpJ8tWCEiA)
- [AWS re:Invent 2023 – What’s new with Amazon EC2](https://www.youtube.com/watch?v=mjHw_wgJJ5g)
- [AWS re:Invent 2023 – Smart savings: Amazon EC2 cost-optimization strategies](https://www.youtube.com/watch?v=_AHPbxzIGV0)
- [AWS re:Invent 2021 – Powering next-gen Amazon EC2: Deep dive on the Nitro System](https://www.youtube.com/watch?v=2uc1vaEsPXU)
- [AWS re:Invent 2019 – Amazon EC2 foundations](https://www.youtube.com/watch?v=kMMybKqC2Y0)
### Related Examples
- [AWS Compute Optimizer Demo code](https://github.com/awslabs/ec2-spot-labs/tree/master/aws-compute-optimizer)
- [Amazon EKS workshop ](https://www.eksworkshop.com/)
- [Right-sizing recommendations](https://catalog.workshops.aws/well-architected-cost-optimization/en-US/3-cost-effective-resources/40-rightsizing-recommendations-100)
