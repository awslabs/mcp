---
id: "COST08-BP01"
title: "Perform data transfer modeling"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you plan for data transfer charges?"
risk_level: "High"
---

# COST08-BP01 Perform data transfer modeling

## Implementation Guidance
 When designing a solution in the cloud, data transfer fees are usually neglected due to habits of designing architecture using on-premises data centers or lack of knowledge. Data transfer charges in AWS are determined by the source, destination, and volume of traffic. Factoring in these fees during the design phase can lead to cost savings. Understanding where the data transfer occurs in your workload, the cost of the transfer, and its associated benefit is very important to accurately estimate total cost of ownership (TCO). This allows you to make an informed decision to modify or accept the architectural decision. For example, you may have a Multi-Availability Zone configuration where you replicate data between the Availability Zones.

 You model the components of services which transfer the data in your workload, and decide that this is an acceptable cost (similar to paying for compute and storage in both Availability Zones) to achieve the required reliability and resilience. Model the costs over different usage levels. Workload usage can change over time, and different services may be more cost effective at different levels.

 While modeling your data transfer, think about how much data is ingested and where that data comes from. Additionally, consider how much data is processed and how much storage or compute capacity is needed. During modeling, follow networking best practices for your workload architecture to optimize your potential data transfer costs.

 The AWS Pricing Calculator can help you see estimated costs for specific AWS services and expected data transfer. If you have a workload already running (for test purposes or in a pre-production environment), use [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) or [AWS Cost and Usage Report](https://aws.amazon.com/aws-cost-management/aws-cost-and-usage-reporting/) (CUR) to understand and model your data transfer costs. Configure a proof of concept (PoC) or test your workload, and run a test with a realistic simulated load. You can model your costs at different workload demands.

## Implementation Steps
- **Identify requirements:** What is the primary goal and business requirements for the planned data transfer between source and destination? What is the expected business outcome at the end? Gather business requirements and define expected outcome.
- **Identify source and destination:** What is the data source and destination for the data transfer, such as within AWS Regions, to AWS services, or out to the internet?
  - [ Data transfer within an AWS Region](https://docs.aws.amazon.com/cur/latest/userguide/cur-data-transfers-charges.html#data-transfer-within-region)
  - [ Data transfer between AWS Regions](https://docs.aws.amazon.com/cur/latest/userguide/cur-data-transfers-charges.html#data-transfer-between-regions)
  - [ Data transfer out to the internet ](https://docs.aws.amazon.com/cur/latest/userguide/cur-data-transfers-charges.html#data-transfer-out-internet)
- **Identify data classifications:** What is the data classification for this data transfer? What kind of data is it? How big is the data? How frequently must data be transferred? Is data sensitive?
- **Identify AWS services or tools to use:** Which AWS services are used for this data transfer? Is it possible to use an already-provisioned service for another workload?
- ** Calculate data transfer costs: **Use [AWS Pricing](https://aws.amazon.com/pricing/) the data transfer modeling you created previously to calculate the data transfer costs for the workload. Calculate the data transfer costs at different usage levels, for both increases and reductions in workload usage. Where there are multiple options for the workload architecture, calculate the cost for each option for comparison.
- ** Link costs to outcomes:** For each data transfer cost incurred, specify the outcome that it achieves for the workload. If it is transfer between components, it may be for decoupling, if it is between Availability Zones it may be for redundancy.
- **Create data transfer modeling:** After gathering all information, create a conceptual base data transfer modeling for multiple use cases and different workloads.

## Resources
### Related Documents
- [AWS caching solutions](https://aws.amazon.com/caching/aws-caching/)
- [AWS Pricing](https://aws.amazon.com/pricing/)
- [Amazon EC2 Pricing](https://aws.amazon.com/ec2/pricing/on-demand/)
- [Amazon VPC pricing](https://aws.amazon.com/vpc/pricing/)
- [ Understanding data transfer charges ](https://docs.aws.amazon.com/cur/latest/userguide/cur-data-transfers-charges.html)
### Related Videos
- [ Monitoring and Optimizing Your Data Transfer Costs ](https://www.youtube.com/watch?v=UjliYz25_qo)
- [ S3 Transfer Acceleration ](https://youtu.be/J2CVnmUWSi4)
### Related Examples
- [ Overview of Data Transfer Costs for Common Architectures ](https://aws.amazon.com/blogs/architecture/overview-of-data-transfer-costs-for-common-architectures/)
- [AWS Prescriptive Guidance for Networking ](https://aws.amazon.com/prescriptive-guidance/?apg-all-cards.sort-by=item.additionalFields.sortDate&apg-all-cards.sort-order=desc&awsf.apg-new-filter=*all&awsf.apg-content-type-filter=*all&awsf.apg-code-filter=*all&awsf.apg-category-filter=categories%23network&awsf.apg-rtype-filter=*all&awsf.apg-isv-filter=*all&awsf.apg-product-filter=*all&awsf.apg-env-filter=*all)
