---
id: "COST04-BP01"
title: "Track resources over their lifetime"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you decommission resources?"
risk_level: "High"
---

# COST04-BP01 Track resources over their lifetime

## Implementation Guidance
Decommission workload resources that are no longer required. A common example is resources used for testing: after testing has been completed, the resources can be removed. Tracking resources with tags (and running reports on those tags) can help you identify assets for decommission, as they will not be in use or the license on them will expire. Using tags is an effective way to track resources, by labeling the resource with its function, or a known date when it can be decommissioned. Reporting can then be run on these tags. Example values for feature tagging are `feature-X testing` to identify the purpose of the resource in terms of the workload lifecycle. Another example is using `LifeSpan` or `TTL` for the resources, such as to-be-deleted tag key name and value to define the time period or specific time for decommissioning.

## Implementation Steps
- ** Implement a tagging scheme: **Implement a tagging scheme that identifies the workload the resource belongs to, verifying that all resources within the workload are tagged accordingly. Tagging helps you categorize resources by purpose, team, environment, or other criteria relevant to your business. For more detail on tagging uses cases, strategies, and techniques, see [AWS Tagging Best Practices](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html).
- ** Implement workload throughput or output monitoring: **Implement workload throughput monitoring or alarming, initiating on either input requests or output completions. Configure it to provide notifications when workload requests or outputs drop to zero, indicating the workload resources are no longer used. Incorporate a time factor if the workload periodically drops to zero under normal conditions. For more detail on unused or underutilized resources, see [AWS Trusted Advisor Cost Optimization checks](https://docs.aws.amazon.com/awssupport/latest/user/cost-optimization-checks.html).
- **Group AWS resources:** Create groups for AWS resources. You can use [AWS Resource Groups](https://docs.aws.amazon.com/ARG/latest/userguide/resource-groups.html) to organize and manage your AWS resources that are in the same AWS Region. You can add tags to most of your resources to help identify and sort your resources within your organization. Use [Tag Editor](https://docs.aws.amazon.com/ARG/latest/userguide/tag-editor.html) add tags to supported resources in bulk. Consider using [AWS Service Catalog](https://docs.aws.amazon.com/servicecatalog/index.html) to create, manage, and distribute portfolios of approved products to end users and manage the product lifecycle.

## Resources
### Related Documents
- [AWS Auto Scaling](https://aws.amazon.com/autoscaling/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/trustedadvisor/)
- [AWS Trusted Advisor Cost Optimization Checks](https://docs.aws.amazon.com/awssupport/latest/user/cost-optimization-checks.html)
- [Tagging AWS resources](https://docs.aws.amazon.com/general/latest/gr/aws_tagging.html)
- [Publishing Custom Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html)
### Related Videos
- [How to optimize costs using AWS Trusted Advisor](https://youtu.be/zcQPufNFhgg)
### Related Examples
- [Organize AWS resources](https://aws.amazon.com/premiumsupport/knowledge-center/resource-groups/)
- [Optimize cost using AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/knowledge-center/trusted-advisor-cost-optimization/)
