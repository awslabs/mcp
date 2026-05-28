---
id: "COST08-BP03"
title: "Implement services to reduce data transfer costs"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you plan for data transfer charges?"
risk_level: "Medium"
---

# COST08-BP03 Implement services to reduce data transfer costs

## Implementation Guidance
 There are various AWS services that can help you to optimize your network data transfer usage. Depending on your workload components, type, and cloud architecture, these services can assist you in compression, caching, and sharing and distribution of your traffic on the cloud.
- [Amazon CloudFront](https://aws.amazon.com/cloudfront/) is a global content delivery network that delivers data with low latency and high transfer speeds. It caches data at edge locations across the world, which reduces the load on your resources. By using CloudFront, you can reduce the administrative effort in delivering content to large numbers of users globally with minimum latency. The [security savings bundle](https://aws.amazon.com/about-aws/whats-new/2021/02/introducing-amazon-cloudfront-security-savings-bundle/?sc_channel=em&sc_campaign=Launch_mult_OT_awsroadmapemail_20200910&sc_medium=em_whats_new&sc_content=launch_ot_ot&sc_country=mult&sc_geo=mult&sc_category=mult&sc_outcome=launch) can help you to save up to 30% on your CloudFront usage if you plan to grow your usage over time.
- [AWS Direct Connect](https://aws.amazon.com/directconnect/) allows you to establish a dedicated network connection to AWS. This can reduce network costs, increase bandwidth, and provide a more consistent network experience than internet-based connections.
- [AWS VPN](https://aws.amazon.com/vpn/) allows you to establish a secure and private connection between your private network and the AWS global network. It is ideal for small offices or business partners because it provides simplified connectivity, and it is a fully managed and elastic service.
- [VPC Endpoints](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-endpoints.html) allow connectivity between AWS services over private networking and can be used to reduce public data transfer and [NAT gateway](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html) costs. [Gateway VPC endpoints](https://docs.aws.amazon.com/vpc/latest/userguide/vpce-gateway.html) have no hourly charges, and support Amazon S3 and Amazon DynamoDB. [Interface VPC endpoints](https://docs.aws.amazon.com/vpc/latest/userguide/vpce-interface.html) are provided by [AWS PrivateLink](https://docs.aws.amazon.com/vpc/latest/userguide/endpoint-service.html) and have an hourly fee and per-GB usage cost.
- [NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html) provide built-in scaling and management for reducing costs as opposed to a standalone NAT instance. Place NAT gateways in the same Availability Zones as high traffic instances and consider using VPC endpoints for the instances that need to access Amazon DynamoDB or Amazon S3 to reduce the data transfer and processing costs.
- Use [AWS Snow Family](https://aws.amazon.com/snow/) devices which have computing resources to collect and process data at the edge. AWS Snow Family devices ([Snowball Edge](https://aws.amazon.com/snowcone/), [Snowball Edge](https://aws.amazon.com/snowball/) and [Snowmobile](https://aws.amazon.com/snowmobile/)) allow you to move petabytes of data to the AWS Cloud cost effectively and offline.

## Implementation Steps
- **Implement services:** Select applicable AWS network services based on your service workload type using the data transfer modeling and reviewing VPC Flow Logs. Look at where the largest costs and highest volume flows are. Review the AWS services and assess whether there is a service that reduces or removes the transfer, specifically networking and content delivery. Also look for caching services where there is repeated access to data or large amounts of data.

## Resources
### Related Documents
- [AWS Direct Connect](https://aws.amazon.com/directconnect/)
- [AWS Explore Our Products](https://aws.amazon.com/)
- [AWS caching solutions](https://aws.amazon.com/caching/aws-caching/)
- [Amazon CloudFront](https://aws.amazon.com/cloudfront/)
- [AWS Snow Family](https://aws.amazon.com/snow/)
- [Amazon CloudFront Security Savings Bundle](https://aws.amazon.com/about-aws/whats-new/2021/02/introducing-amazon-cloudfront-security-savings-bundle/)
### Related Videos
- [Monitoring and Optimizing Your Data Transfer Costs](https://www.youtube.com/watch?v=UjliYz25_qo)
- [AWS Cost Optimization Series: CloudFront](https://www.youtube.com/watch?v=k8De2AfAN3k)
- [How can I reduce data transfer charges for my NAT gateway?](https://www.youtube.com/watch?v=hq4KtPRezus)
### Related Examples
- [How-to chargeback shared services: An AWS Transit Gateway example](https://aws.amazon.com/blogs/aws-cloud-financial-management/gs-chargeback-shared-services-an-aws-transit-gateway-example/)
- [Understand AWS data transfer details in depth from cost and usage report using Athena query and QuickSight](https://aws.amazon.com/blogs/networking-and-content-delivery/understand-aws-data-transfer-details-in-depth-from-cost-and-usage-report-using-athena-query-and-quicksight/)
- [Overview of Data Transfer Costs for Common Architectures](https://aws.amazon.com/blogs/architecture/overview-of-data-transfer-costs-for-common-architectures/)
- [Using AWS Cost Explorer to analyze data transfer costs](https://aws.amazon.com/blogs/mt/using-aws-cost-explorer-to-analyze-data-transfer-costs/)
- [Cost-Optimizing your AWS architectures by utilizing Amazon CloudFront features](https://aws.amazon.com/blogs/networking-and-content-delivery/cost-optimizing-your-aws-architectures-by-utilizing-amazon-cloudfront-features/)
- [How can I reduce data transfer charges for my NAT gateway?](https://aws.amazon.com/premiumsupport/knowledge-center/vpc-reduce-nat-gateway-transfer-costs/)
