---
id: "COST07-BP05"
title: "Perform pricing model analysis at the management account level"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you use pricing models to reduce cost?"
risk_level: "Low"
---

# COST07-BP05 Perform pricing model analysis at the management account level

## Implementation Guidance
 Performing regular cost modeling helps you implement opportunities to optimize across multiple workloads. For example, if multiple workloads use On-Demand Instances at an aggregate level, the risk of change is lower, and implementing a commitment-based discount can achieve a lower overall cost. It is recommended to perform analysis in regular cycles of two weeks to one month. This allows you to make small adjustment purchases, so the coverage of your pricing models continues to evolve with your changing workloads and their components.

 Use the [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) recommendations tool to find opportunities for commitment discounts in your management account. Recommendations at the management account level are calculated considering usage across all of the accounts in your AWS organization that have Reserve Instances (RI) or Savings Plans (SP). They're also calculated when discount sharing is activated to recommend a commitment that maximizes savings across accounts.

 While purchasing at the management account level optimizes for max savings in many cases, there may be situations where you might consider purchasing SPs at the linked account level, like when you want the discounts to apply first to usage in that particular linked account. Member account recommendations are calculated at the individual account level, to maximize savings for each isolated account. If your account owns both RI and SP commitments, they will be applied in this order:

1.  Zonal RI

1.  Standard RI

1.  Convertible RI

1.  Instance Savings Plan

1.  Compute Savings Plan

 If you purchase an SP at the management account level, the savings will be applied based on highest to lowest discount percentage. SPs at the management account level look across all linked accounts and apply the savings wherever the discount will be the highest. If you wish to restrict where the savings are applied, you can purchase a Savings Plan at the linked account level and any time that account is running eligible compute services, the discount will be applied there first. When the account is not running eligible compute services, the discount will be shared across the other linked accounts under the same management account. Discount sharing is turned on by default, but can be turned off if needed.

 In a Consolidated Billing Family, Savings Plans are applied first to the owner account's usage, and then to other accounts' usage. This occurs only if you have sharing enabled. Your Savings Plans are applied to your highest savings percentage first. If there are multiple usages with equal savings percentages, Savings Plans are applied to the first usage with the lowest Savings Plans rate. Savings Plans continue to apply until there are no more remaining uses or your commitment is exhausted. Any remaining usage is charged at the On-Demand rates. You can refresh Savings Plans Recommendations in AWS Cost Management to generate new Savings Plans Recommendations at any time.

 After analyzing flexibility of instances, you can commit by following recommendations. Create cost modeling by analyzing the workload’s short-term costs with potential different resource options, analyzing AWS pricing models, and aligning them with your business requirements to find out total cost of ownership and [cost optimization](https://docs.aws.amazon.com/whitepapers/latest/how-aws-pricing-works/aws-cost-optimization.html) opportunities.

## Implementation Steps
 **Perform a commitment discount analysis**: Use Cost Explorer in your account review the Savings Plans and Reserved Instance recommendations. Make sure you understand Saving Plan recommendations, and estimate your monthly spend and monthly savings. Review recommendations at the management account level, which are calculated considering usage across all of the member accounts in your AWS organization that have RI or Savings Plans discount sharing enabled for maximum savings across accounts. You can verify that you implemented the correct recommendations with the required discounts and risk by following the Well-Architected labs.

## Resources
### Related Documents
- [How does AWS pricing work?](https://aws.amazon.com/pricing/?nc2=h_ql_pr_ln)
- [Instance purchasing options](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-purchasing-options.html)
- [Saving Plan Overview](file:///Users/mergenf/Documents/WELL%20ARCHITECTED/COST%20OPT%20PILLAR/phase3a/COST06/•%09https:/docs.aws.amazon.com/savingsplans/latest/userguide/sp-overview.html)
- [Saving Plan recommendations](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-recommendations.html)
- [Accessing Reserved Instance recommendations](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ri-recommendations.html)
- [Understanding your Saving Plans recommendation](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-recommendations.html)
- [How Savings Plans apply to your AWS usage](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-applying.html)
- [Saving Plans with Consolidated Billing](https://aws.amazon.com/premiumsupport/knowledge-center/savings-plans-consolidated-billing/)
- [Turning on shared reserved instances and Savings Plans discounts](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ri-turn-on-process.html)
### Related Videos
- [Save up to 90% and run production workloads on Spot](https://www.youtube.com/watch?v=BlNPZQh2wXs)
### Related Examples
- [What should I consider before purchasing a Savings Plan?](https://aws.amazon.com/premiumsupport/knowledge-center/savings-plans-considerations/)
- [How can I use rolling Savings Plans to reduce commitment risk?](https://aws.amazon.com/blogs/aws-cloud-financial-management/how-can-i-use-rolling-savings-plans-to-reduce-commitment-risk/)
- [When to Use Spot Instances](https://docs.aws.amazon.com/whitepapers/latest/cost-optimization-leveraging-ec2-spot-instances/when-to-use-spot-instances.html)
