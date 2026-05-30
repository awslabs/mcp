---
id: "COST08-BP02"
title: "Select components to optimize data transfer cost"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you plan for data transfer charges?"
risk_level: "Medium"
---

# COST08-BP02 Select components to optimize data transfer cost

## Implementation Guidance
 Architecting for data transfer minimizes data transfer costs. This may involve using content delivery networks to locate data closer to users, or using dedicated network links from your premises to AWS. You can also use WAN optimization and application optimization to reduce the amount of data that is transferred between components.

 When transferring data to or within the AWS Cloud, it is essential to know the destination based on varied use cases, the nature of the data, and the available network resources in order to select the right AWS services to optimize data transfer. AWS offers a range of data transfer services tailored for diverse data migration requirements. Select the right [data storage](https://aws.amazon.com/products/storage/) and [data transfer](https://aws.amazon.com/cloud-data-migration/) options based on the business needs within your organization.

 When planning or reviewing your workload architecture, consider the following:
- **Use VPC endpoints within AWS:** VPC endpoints allow for private connections between your VPC and supported AWS services. This allows you to avoid using the public internet, which can lead to data transfer costs.
- **Use a NAT gateway:** Use a [NAT gateway](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html) so that instances in a private subnet can connect to the internet or to the services outside your VPC. Check whether the resources behind the NAT gateway that send the most traffic are in the same Availability Zone as the NAT gateway. If they are not, create new NAT gateways in the same Availability Zone as the resource to reduce cross-AZ data transfer charges.
- **Use AWS Direct Connect** AWS Direct Connect bypasses the public internet and establishes a direct, private connection between your on-premises network and AWS. This can be more cost-effective and consistent than transferring large volumes of data over the internet.
- **Avoid transferring data across Regional boundaries:** Data transfers between AWS Regions (from one Region to another) typically incur charges. It should be a very thoughtful decision to pursue a multi-Region path. For more detail, see [Multi-Region scenarios](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/multi-region-scenarios.html).
- **Monitor data transfer:** Use Amazon CloudWatch and [VPC flow logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html) to capture details about your data transfer and network usage. Analyze captured network traffic information in your VPCs, such as IP address or range going to and from network interfaces.
- **Analyze your network usage:** Use metering and reporting tools such as AWS Cost Explorer, CUDOS Dashboards, or CloudWatch to understand data transfer cost of your workload.

## Implementation Steps
- **Select components for data transfer:** Using the data transfer modeling explained in [COST08-BP01 Perform data transfer modeling](cost_data_transfer_modeling.md), focus on where the largest data transfer costs are or where they would be if the workload usage changes. Look for alternative architectures or additional components that remove or reduce the need for data transfer (or lower its cost).

## Resources
### Related Best Practices
- [COST08-BP01 Perform data transfer modeling](cost_data_transfer_modeling.md)
- [COST08-BP03 Implement services to reduce data transfer costs](cost_data_transfer_implement_services.md)
### Related Documents
- [ Cloud Data Migration ](https://aws.amazon.com/cloud-data-migration/)
- [AWS caching solutions](https://aws.amazon.com/caching/aws-caching/)
- [Deliver content faster with Amazon CloudFront](https://aws.amazon.com/getting-started/tutorials/deliver-content-faster/)
### Related Examples
- [ Overview of Data Transfer Costs for Common Architectures ](https://aws.amazon.com/blogs/architecture/overview-of-data-transfer-costs-for-common-architectures/)
- [AWS Network Optimization Tips ](https://aws.amazon.com/blogs/networking-and-content-delivery/aws-network-optimization-tips/)
- [ Optimize performance and reduce costs for network analytics with VPC Flow Logs in Apache Parquet format ](https://aws.amazon.com/blogs/big-data/optimize-performance-and-reduce-costs-for-network-analytics-with-vpc-flow-logs-in-apache-parquet-format/)
