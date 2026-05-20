---
id: "SUS05-BP01"
title: "Use the minimum amount of hardware to meet your needs"
framework: "WAF"
domain: "Sustainability"
capability: "How do you select and use cloud hardware and services in your architecture to support your sustainability goals?"
risk_level: "Medium"
---

# SUS05-BP01 Use the minimum amount of hardware to meet your needs

## Anti-Patterns
- You do not monitor resource utilization.
- You have resources with a low utilization level in your architecture.
- You do not review the utilization of static hardware to determine if it should be resized.
- You do not set hardware utilization goals for your compute infrastructure based on business KPIs.

## Implementation Guidance
 Optimally select the total number of hardware required for your workload to improve its overall efficiency. The AWS Cloud provides the flexibility to expand or reduce the number of resources dynamically through a variety of mechanisms, such as [AWS Auto Scaling](https://aws.amazon.com/autoscaling/), and meet changes in demand. It also provides [APIs and SDKs](https://aws.amazon.com/developer/tools/) that allow resources to be modified with minimal effort. Use these capabilities to make frequent changes to your workload implementations. Additionally, use rightsizing guidelines from AWS tools to efficiently operate your cloud resource and meet your business needs.

## Implementation Steps
- **Choose the instances type:** Choose the right instances type to best fit your needs. To learn about how to choose Amazon Elastic Compute Cloud instances and use mechanisms such as attribute-based instance selection, see the following:
  - [ How do I choose the appropriate Amazon EC2 instance type for my workload? ](https://aws.amazon.com/premiumsupport/knowledge-center/ec2-instance-choose-type-for-workload/)
  - [ Attribute-based instance type selection for Amazon EC2 Fleet. ](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-fleet-attribute-based-instance-type-selection.html)
  - [ Create an Auto Scaling group using attribute-based instance type selection. ](https://docs.aws.amazon.com/autoscaling/ec2/userguide/create-asg-instance-type-requirements.html)
- **Scale:** Use small increments to scale variable workloads.
- **Use multiple compute purchase options:** Balance instance flexibility, scalability, and cost savings with multiple compute purchase options.
  - [Amazon EC2 On-Demand Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-on-demand-instances.html) are best suited for new, stateful, and spiky workloads which can’t be instance type, location, or time flexible.
  - [Amazon EC2 Spot Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html) are a great way to supplement the other options for applications that are fault tolerant and flexible.
  - Leverage [Compute Savings Plans](https://aws.amazon.com/savingsplans/compute-pricing/) for steady state workloads that allow flexibility if your needs (like AZ, Region, instance families, or instance types) change.
- **Use instance and Availability Zone diversity:** Maximize application availability and take advantage of excess capacity by diversifying your instances and Availability Zones.
- **Rightsize instances:** Use the rightsizing recommendations from AWS tools to make adjustments on your workload. For more information, see [Optimizing your cost with Rightsizing Recommendations](https://docs.aws.amazon.com/latest/userguide/ce-rightsizing.html) and [Right Sizing: Provisioning Instances to Match Workloads](https://docs.aws.amazon.com/latest/cost-optimization-right-sizing/cost-optimization-right-sizing.html)
  - Use rightsizing recommendations in AWS Cost Explorer or [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/) to identify rightsizing opportunities.
- **Negotiate service-level agreements (SLAs):** Negotiate SLAs that permit temporarily reducing capacity while automation deploys replacement resources.

## Resources
### Related Documents
- [ Optimizing your AWS Infrastructure for Sustainability, Part I: Compute ](https://aws.amazon.com/blogs/architecture/optimizing-your-aws-infrastructure-for-sustainability-part-i-compute/)
- [ Attirbute based Instance Type Selection for Auto Scaling for Amazon EC2 Fleet ](https://aws.amazon.com/blogs/aws/new-attribute-based-instance-type-selection-for-ec2-auto-scaling-and-ec2-fleet/)
- [AWS Compute Optimizer Documentation ](https://docs.aws.amazon.com/compute-optimizer/index.html)
- [Operating Lambda: Performance optimization](https://aws.amazon.com/blogs/compute/operating-lambda-performance-optimization-part-2/)
- [Auto Scaling Documentation](https://docs.aws.amazon.com/autoscaling/index.html)
### Related Videos
- [AWS re:Invent 2023 - What's new with Amazon EC2](https://www.youtube.com/watch?v=mjHw_wgJJ5g)
- [AWS re:Invent 2023 - Smart savings: Amazon Elastic Compute Cloud cost-optimization strategies](https://www.youtube.com/watch?v=_AHPbxzIGV0)
- [AWS re:Invent 2022 - Optimizing Amazon Elastic Kubernetes Service for performance and cost on AWS](https://www.youtube.com/watch?v=5B4-s_ivn1o)
- [AWS re:Invent 2023 - Sustainable compute: reducing costs and carbon emissions with AWS](https://www.youtube.com/watch?v=0Bl1SDU2HxI)
