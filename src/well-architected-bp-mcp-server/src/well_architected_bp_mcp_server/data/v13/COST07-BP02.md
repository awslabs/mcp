---
id: "COST07-BP02"
title: "Choose Regions based on cost"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you use pricing models to reduce cost?"
risk_level: "Medium"
---

# COST07-BP02 Choose Regions based on cost

## Implementation Guidance
The [AWS Cloud Infrastructure](https://aws.amazon.com/about-aws/global-infrastructure/) is global, hosted in [multiple locations world-wide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html), and built around AWS Regions, Availability Zones, Local Zones, AWS Outposts, and Wavelength Zones. A Region is a physical location in the world and each Region is a separate geographic area where AWS has multiple Availability Zones. Availability Zones which are multiple isolated locations within each Region consist of one or more discrete data centers, each with redundant power, networking, and connectivity.

Each AWS Region operates within local market conditions, and resource pricing is different in each Region due to differences in the cost of land, fiber, electricity, and taxes, for example. Choose a specific Region to operate a component of or your entire solution so that you can run at the lowest possible price globally. Use [AWS Calculator](https://calculator.aws/#/) to estimate the costs of your workload in various Regions by searching services by location type (Region, wave length zone and local zone) and Region.

When you architect your solutions, a best practice is to seek to place computing resources closer to users to provide lower latency and strong data sovereignty. Select the geographic location based on your business, data privacy, performance, and security requirements. For applications with global end users, use multiple locations.

 Use Regions that provide lower prices for AWS services to deploy your workloads if you have no obligations in data privacy, security and business requirements. For example, if your default Region is Asia Pacific (Sydney) (`ap-southwest-2`), and if there are no restrictions (data privacy, security, for example) to use other Regions, deploying non-critical (development and test) Amazon EC2 instances in US East (N. Virginia) (`us-east-1`) will cost you less.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/region-feature-matrix.png)

 The preceding matrix table shows us that Region 6 is the best option for this given scenario because latency is low compared to other Regions, service is available, and it is the least expensive Region.

## Implementation Steps
- ** Review AWS Region pricing: **Analyze the workload costs in the current Region. Starting with the highest costs by service and usage type, calculate the costs in other Regions that are available. If the forecasted saving outweighs the cost of moving the component or workload, migrate to the new Region.
- **Review requirements for multi-Region deployments:** Analyze your business requirements and obligations (data privacy, security, or performance) to find out if there are any restrictions for you to not to use multiple Regions. If there are no obligations to restrict you to use single Region, then use multiple Regions.
- **Analyze required data transfer:** Consider data transfer costs when selecting Regions. Keep your data close to your customer and close to the resources. Select less costly AWS Regions where data flows and where there is minimal data transfer. Depending on your business requirements for data transfer, you can use [Amazon CloudFront](https://aws.amazon.com/cloudfront/), [AWS PrivateLink](https://aws.amazon.com/privatelink/), [AWS Direct Connect](https://aws.amazon.com/directconnect/), and [AWS Virtual Private Network](https://aws.amazon.com/vpn/) to reduce your networking costs, improve performance, and enhance security.

## Resources
### Related Documents
- [Accessing Reserved Instance recommendations](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ri-recommendations.html)
- [Amazon EC2 pricing](https://aws.amazon.com/ec2/pricing/)
- [Instance purchasing options](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-purchasing-options.html)
- [Region Table](https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/)
### Related Videos
- [Save up to 90% and run production workloads on Spot](https://www.youtube.com/watch?v=BlNPZQh2wXs)
### Related Examples
- [ Overview of Data Transfer Costs for Common Architectures ](https://aws.amazon.com/blogs/architecture/overview-of-data-transfer-costs-for-common-architectures/)
- [ Cost Considerations for Global Deployments ](https://aws.amazon.com/blogs/aws-cloud-financial-management/cost-considerations-for-global-deployments/)
- [ What to Consider when Selecting a Region for your Workloads ](https://aws.amazon.com/blogs/architecture/what-to-consider-when-selecting-a-region-for-your-workloads/)
