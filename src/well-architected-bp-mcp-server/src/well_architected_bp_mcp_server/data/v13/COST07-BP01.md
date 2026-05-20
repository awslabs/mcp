---
id: "COST07-BP01"
title: "Perform pricing model analysis"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you use pricing models to reduce cost?"
risk_level: "High"
---

# COST07-BP01 Perform pricing model analysis

## Implementation Guidance
AWS has multiple [pricing models](https://aws.amazon.com/pricing/) that allow you to pay for your resources in the most cost-effective way that suits your organization’s needs and depending on product. Work with your teams to determine the most appropriate pricing model. Often your pricing model consists of a combination of multiple options, as determined by your availability

 **On-Demand Instances** allow you to pay for compute or database capacity by the hour or by the second (60 seconds minimum) depending on which instances you run, without long-term commitments or upfront payments.

 **Savings Plans** are a flexible pricing model that offers low prices on Amazon EC2, Lambda, and AWS Fargate usage, in exchange for a commitment to a consistent amount of usage (measured in dollars per hour) over one year or three years terms.

 **Spot Instances** are an Amazon EC2 pricing mechanism that allows you request spare compute capacity at discounted hourly rate (up to 90% off the on-demand price) without upfront commitment.

 **Reserved Instances** allow you up to 75 percent discount by prepaying for capacity. For more details, see [Optimizing costs with reservations](https://docs.aws.amazon.com/whitepapers/latest/how-aws-pricing-works/aws-cost-optimization.html).

 You might choose to include a Savings Plans for the resources associated with the production, quality, and development environments. Alternatively, because sandbox resources are only powered on when needed, you might choose an on-demand model for the resources in that environment. Use Amazon [Spot Instances](https://docs.aws.amazon.com/whitepapers/latest/how-aws-pricing-works/amazon-elastic-compute-cloud-amazon-ec2.html#spot-instances) to reduce Amazon EC2 costs or use [Compute Savings Plans](https://docs.aws.amazon.com/whitepapers/latest/how-aws-pricing-works/amazon-elastic-compute-cloud-amazon-ec2.html#savings-plans) to reduce Amazon EC2, Fargate, and Lambda cost. The [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) recommendations tool provides opportunities for commitment discounts with Saving plans.

 If you have been purchasing [Reserved Instances](https://aws.amazon.com/aws-cost-management/aws-cost-optimization/reserved-instances/?track=costop) for Amazon EC2 in the past or have established cost allocation practices inside your organization, you can continue using Amazon EC2 Reserved Instances for the time being. However, we recommend working on a strategy to use Savings Plans in the future as a more flexible cost savings mechanism. You can refresh Savings Plans (SP) Recommendations in AWS Cost Management to generate new Savings Plans Recommendations at any time. Use Reserved Instances (RI) to reduce Amazon RDS, Amazon Redshift, Amazon ElastiCache, and Amazon OpenSearch Service costs. Saving Plans and Reserved Instances are available in three options: all upfront, partial upfront and no upfront payments. Use the recommendations provided in AWS Cost Explorer RI and SP purchase recommendations.

 To find opportunities for Spot workloads, use an hourly view of your overall usage, and look for regular periods of changing usage or elasticity. You can use Spot Instances for various fault-tolerant and flexible applications. Examples include stateless web servers, API endpoints, big data and analytics applications, containerized workloads, CI/CD, and other flexible workloads.

 Analyze your Amazon EC2 and Amazon RDS instances whether they can be turned off when you don’t use (after hours and weekends). This approach will allow you to reduce costs by 70% or more compared to using them 24/7. If you have Amazon Redshift clusters that only need to be available at specific times, you can pause the cluster and later resume it. When the Amazon Redshift cluster or Amazon EC2 and Amazon RDS Instance is stopped, the compute billing halts and only the storage charge applies.

 Note that [On-Demand Capacity reservations](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/capacity-reservations-pricing-billing.html) (ODCR) are not a pricing discount. Capacity Reservations are charged at the equivalent On-Demand rate, whether you run instances in reserved capacity or not. They should be considered when you need to provide enough capacity for the resources you plan to run. ODCRs don't have to be tied to long-term commitments, as they can be cancelled when you no longer need them, but they can also benefit from the discounts that Savings Plans or Reserved Instances provide.

## Implementation Steps
- **Analyze workload elasticity: **Using the hourly granularity in Cost Explorer or a custom dashboard, analyze your workload's elasticity. Look for regular changes in the number of instances that are running. Short duration instances are candidates for Spot Instances or Spot Fleet.
  - [Well-Architected Lab: Cost Explorer](https://wellarchitectedlabs.com/Cost/Cost_Fundamentals/100_5_Cost_Visualization/Lab_Guide.html#Elasticity)
  - [Well-Architected Lab: Cost Visualization](https://wellarchitectedlabs.com/Cost/Cost_Fundamentals/200_5_Cost_Visualization/README.html)
- **Review existing pricing contracts:** Review current contracts or commitments for long term needs. Analyze what you currently have and how much those commitments are in use. Leverage pre-existing contractual discounts or enterprise agreements. [Enterprise Agreements](https://aws.amazon.com/pricing/enterprise/) give customers the option to tailor agreements that best suit their needs. For long term commitments, consider reserved pricing discounts, Reserved Instances or Savings Plans for the specific instance type, instance family, AWS Region, and Availability Zones.
- ** Perform a commitment discount analysis:** Using Cost Explorer in your account, review the Savings Plans and Reserved Instance recommendations. To verify that you implement the correct recommendations with the required discounts and risk, follow the [Well-Architected labs](https://wellarchitectedlabs.com/cost/costeffectiveresources/).

## Resources
### Related Documents
- [Accessing Reserved Instance recommendations](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ri-recommendations.html)
- [Instance purchasing options](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-purchasing-options.html)
- [AWS Enterprise ](https://aws.amazon.com/pricing/enterprise/)
### Related Videos
- [Save up to 90% and run production workloads on Spot](https://www.youtube.com/watch?v=BlNPZQh2wXs)
### Related Examples
- [Well-Architected Lab: Cost Explorer](https://wellarchitectedlabs.com/Cost/Cost_Fundamentals/100_5_Cost_Visualization/Lab_Guide.html#Elasticity)
- [Well-Architected Lab: Cost Visualization](https://wellarchitectedlabs.com/Cost/Cost_Fundamentals/200_5_Cost_Visualization/README.html)
- [Well-Architected Lab: Pricing Models](https://wellarchitectedlabs.com/Cost/CostEffectiveResources.html)
