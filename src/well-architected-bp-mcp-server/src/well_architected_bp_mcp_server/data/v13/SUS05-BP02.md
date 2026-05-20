---
id: "SUS05-BP02"
title: "Use instance types with the least impact"
framework: "WAF"
domain: "Sustainability"
capability: "How do you select and use cloud hardware and services in your architecture to support your sustainability goals?"
risk_level: "Medium"
---

# SUS05-BP02 Use instance types with the least impact

## Anti-Patterns
- You are only using one family of instances.
- You are only using x86 instances.
- You specify one instance type in your Amazon EC2 Auto Scaling configuration.
- You use AWS instances in a manner that they were not designed for (for example, you use compute-optimized instances for a memory-intensive workload).
- You do not evaluate new instance types regularly.
- You do not check recommendations from AWS rightsizing tools such as [AWS Compute Optimizer.](https://aws.amazon.com/compute-optimizer/)

## Implementation Guidance
 Using efficient instances in cloud workload is crucial for lower resource usage and cost-effectiveness. Continually monitor the release of new instance types and take advantage of energy efficiency improvements, including those instance types designed to support specific workloads such as machine learning training and inference, and video transcoding.

## Implementation Steps
- **Learn and explore instance types:** Find instance types that can lower your workload's environmental impact.
  - Subscribe to [What's New with AWS](https://aws.amazon.com/new/) to stay up-to-date with the latest AWS technologies and instances.
  - Learn about different AWS instance types.
  - Learn about AWS Graviton-based instances which offer the best performance per watt of energy use in Amazon EC2 by watching [re:Invent 2020 - Deep dive on AWS Graviton2 processor-powered Amazon EC2 instances](https://www.youtube.com/watch?v=NLysl0QvqXU) and [Deep dive into AWS Graviton3 and Amazon EC2 C7g instances](https://www.youtube.com/watch?v=WDKwwFQKfSI&ab_channel=AWSEvents).
- **Use instance types with the least impact:** Plan and transition your workload to instance types with the least impact.
  - Define a process to evaluate new features or instances for your workload. Take advantage of agility in the cloud to quickly test how new instance types can improve your workload environmental sustainability. Use proxy metrics to measure how many resources it takes you to complete a unit of work.
  - If possible, modify your workload to work with different numbers of vCPUs and different amounts of memory to maximize your choice of instance type.
  - Consider transitioning your workload to Graviton-based instances to improve the performance efficiency of your workload. For more information on moving workloads to AWS Graviton, see [AWS Graviton Fast Start](https://aws.amazon.com/ec2/graviton/fast-start/) and [Considerations when transitioning workloads to AWS Graviton-based Amazon Elastic Compute Cloud instances](https://github.com/aws/aws-graviton-getting-started/blob/main/transition-guide.md).
  - Consider selecting the AWS Graviton option in your usage of [AWS managed services.](https://github.com/aws/aws-graviton-getting-started/blob/main/managed_services.md)
  - Migrate your workload to Regions that offer instances with the least sustainability impact and still meet your business requirements.
  - For machine learning workloads, take advantage of purpose-built hardware that is specific to your workload such as [AWS Trainium](https://aws.amazon.com/machine-learning/trainium/), [AWS Inferentia](https://aws.amazon.com/machine-learning/inferentia/), and [Amazon EC2 DL1.](https://aws.amazon.com/ec2/instance-types/dl1/) AWS Inferentia instances such as Inf2 instances offer up to 50% better performance per watt over comparable Amazon EC2 instances.
  - Use [Amazon SageMaker AI Inference Recommender](https://docs.aws.amazon.com/sagemaker/latest/dg/inference-recommender.html) to right size ML inference endpoint.
  - For spiky workloads (workloads with infrequent requirements for additional capacity), use [burstable performance instances.](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances.html)
  - For stateless and fault-tolerant workloads, use [Amazon EC2 Spot Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html) to increase overall utilization of the cloud, and reduce the sustainability impact of unused resources.
- **Operate and optimize:** Operate and optimize your workload instance.
  - For ephemeral workloads, evaluate [instance Amazon CloudWatch metrics](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/viewing_metrics_with_cloudwatch.html#ec2-cloudwatch-metrics) such as `CPUUtilization` to identify if the instance is idle or under-utilized.
  - For stable workloads, check AWS rightsizing tools such as [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/) at regular intervals to identify opportunities to optimize and right-size the instances. For further examples and recommendations, see the following labs:
    - [ Well-Architected Lab - Rightsizing Recommendations ](https://catalog.workshops.aws/well-architected-cost-optimization/en-US/3-cost-effective-resources/40-rightsizing-recommendations-100)
    - [ Well-Architected Lab - Rightsizing with Compute Optimizer ](https://catalog.workshops.aws/well-architected-cost-optimization/en-US/3-cost-effective-resources/50-rightsizing-recommendations-200)
    - [ Well-Architected Lab - Optimize Hardware Patterns and Observice Sustainability KPIs ](https://catalog.workshops.aws/well-architected-sustainability/en-US/4-hardware-and-services/optimize-hardware-patterns-observe-sustainability-kpis)

## Resources
### Related Documents
- [Optimizing your AWS Infrastructure for Sustainability, Part I: Compute](https://aws.amazon.com/blogs/architecture/optimizing-your-aws-infrastructure-for-sustainability-part-i-compute/)
- [AWS Graviton](https://aws.amazon.com/ec2/graviton/)
- [Amazon EC2 DL1](https://aws.amazon.com/ec2/instance-types/dl1/)
- [Amazon EC2 Capacity Reservation Fleets](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/cr-fleets.html)
- [Amazon EC2 Spot Fleet](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-fleet.html)
- [Functions: Lambda Function Configuration](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html#function-configuration)
- [ Attribute-based instance type selection for Amazon EC2 Fleet ](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-fleet-attribute-based-instance-type-selection.html)
- [Building Sustainable, Efficient, and Cost-Optimized Applications on AWS](https://aws.amazon.com/blogs/compute/building-sustainable-efficient-and-cost-optimized-applications-on-aws/)
- [ How the Contino Sustainability Dashboard Helps Customers Optimize Their Carbon Footprint ](https://aws.amazon.com/blogs/apn/how-the-contino-sustainability-dashboard-helps-customers-optimize-their-carbon-footprint/)
### Related Videos
- [AWS re:Invent 2023 - AWS Graviton: The best price performance for your AWS workloads](https://www.youtube.com/watch?v=T_hMIjKtSr4)
- [AWS re:Invent 2023 - New Amazon Elastic Compute Cloud generative AI capabilities in AWS Management Console](https://www.youtube.com/watch?v=sSpJ8tWCEiA)
- [AWS re:Invent 2023 = What's new with Amazon Elastic Compute Cloud](https://www.youtube.com/watch?v=mjHw_wgJJ5g)
- [AWS re:Invent 2023 - Smart savings: Amazon Elastic Compute Cloud cost-optimization strategies](https://www.youtube.com/watch?v=_AHPbxzIGV0)
- [AWS re:Invent 2021 - Deep dive into AWS Graviton3 and Amazon EC2 C7g instances](https://www.youtube.com/watch?v=WDKwwFQKfSI&ab_channel=AWSEvents)
- [AWS re:Invent 2022 - Build a cost-, energy-, and resource-efficient compute environment ](https://www.youtube.com/watch?v=8zsC5e1eLCg)
### Related Examples
- [ Solution: Guidance for Optimizing Deep Learning Workloads for Sustainability on AWS](https://aws.amazon.com/solutions/guidance/optimizing-deep-learning-workloads-for-sustainability-on-aws/)
