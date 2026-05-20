---
id: "COST05-BP04"
title: "Select software with cost-effective licensing"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you evaluate cost when you select services?"
risk_level: "Low"
---

# COST05-BP04 Select software with cost-effective licensing

## Implementation Guidance
 Open source originated in the context of software development to indicate that the software complies with certain free distribution criteria. Open source software is composed of source code that anyone can inspect, modify, and enhance. Based on business requirements, skill of engineers, forecasted usage, or other technology dependencies, organizations can consider using open source software on AWS to minimize their license costs. In other words, the cost of software licenses can be reduced through the use of [open source software](https://aws.amazon.com/what-is/open-source/). This can have significant impact on workload costs as the size of the workload scales.

 Measure the benefits of licensed software against the total cost to optimize your workload. Model any changes in licensing and how they would impact your workload costs. If a vendor changes the cost of your database license, investigate how that impacts the overall efficiency of your workload. Consider historical pricing announcements from your vendors for trends of licensing changes across their products. Licensing costs may also scale independently of throughput or usage, such as licenses that scale by hardware (CPU bound licenses). These licenses should be avoided because costs can rapidly increase without corresponding outcomes.

 For instance, operating an Amazon EC2 instance in us-east-1 with a Linux operating system allows you to cut costs by approximately 45%, compared to running another Amazon EC2 instance that runs on Windows.

 The [AWS Pricing Calculator](https://calculator.aws/) offers a comprehensive way to compare the costs of various resources with different license options, such as Amazon RDS instances and different database engines. Additionally, the AWS Cost Explorer provides an invaluable perspective for the costs of existing workloads, especially those that come with different licenses. For license management, [AWS License Manager](https://aws.amazon.com/license-manager) offers a streamlined method to oversee and handle software licenses. Customers can deploy and operationalize their preferred open source software in the AWS Cloud.

## Implementation Steps
- ** Analyze license options:** Review the licensing terms of available software. Look for open source versions that have the required functionality, and whether the benefits of licensed software outweigh the cost. Favorable terms align the cost of the software to the benefits it provides.
- ** Analyze the software provider:** Review any historical pricing or licensing changes from the vendor. Look for any changes that do not align to outcomes, such as punitive terms for running on specific vendors hardware or platforms. Additionally, look for how they perform audits, and penalties that could be imposed.

## Resources
### Related Documents
- [ Open Source at AWS](https://aws.amazon.com/opensource/)
- [AWS Total Cost of Ownership (TCO) Calculator](https://aws.amazon.com/tco-calculator/)
- [Amazon S3 storage classes](https://aws.amazon.com/s3/storage-classes/)
- [Cloud products](https://aws.amazon.com/products/)
### Related Examples
- [ Open Source Blogs ](https://aws.amazon.com/blogs/opensource/)
- [AWS Open Source Blogs ](https://aws.github.io/)
- [ Optimization and Licensing Assessment ](https://aws.amazon.com/optimization-and-licensing-assessment/)
