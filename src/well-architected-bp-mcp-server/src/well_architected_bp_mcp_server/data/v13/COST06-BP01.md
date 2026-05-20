---
id: "COST06-BP01"
title: "Perform cost modeling"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you meet cost targets when you select resource type, size and number?"
risk_level: "High"
---

# COST06-BP01 Perform cost modeling

## Implementation Guidance
 Perform cost modeling for your workload and each of its components to understand the balance between resources, and find the correct size for each resource in the workload, given a specific level of performance. Understanding cost considerations can inform your organizational business case and decision-making process when evaluating the value realization outcomes for planned workload deployment.

 Perform benchmark activities for the workload under different predicted loads and compare the costs. The modeling effort should reflect potential benefit; for example, time spent is proportional to component cost or predicted saving. For best practices, refer to the [Review section of the Performance Efficiency Pillar of the AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/review.html).

 As an example, to create cost modeling for a workload consisting of compute resources, [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/) can assist with cost modeling for running workloads. It provides right-sizing recommendations for compute resources based on historical usage. Make sure CloudWatch Agents are deployed to the Amazon EC2 instances to collect memory metrics which help you with more accurate recommendations within AWS Compute Optimizer. This is the ideal data source for compute resources because it is a free service that uses machine learning to make multiple recommendations depending on levels of risk.

 There are [multiple services](https://docs.aws.amazon.com/whitepapers/latest/cost-optimization-right-sizing/identifying-opportunities-to-right-size.html) you can use with custom logs as data sources for rightsizing operations for other services and workload components, such as [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/), [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) and [Amazon CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html). AWS Trusted Advisor checks resources and flags resources with low utilization which can help you rightsize your resources and create cost modeling.

 The following are recommendations for cost modeling data and metrics:
- The monitoring must accurately reflect the user experience. Select the correct granularity for the time period and thoughtfully choose the maximum or 99th percentile instead of the average.
- Select the correct granularity for the time period of analysis that is required to cover any workload cycles. For example, if a two-week analysis is performed, you might be overlooking a monthly cycle of high utilization, which could lead to under-provisioning.
- Choose the right AWS services for your planned workload by considering your existing commitments, selected pricing models for other workloads, and ability to innovate faster and focus on your core business value.

**Implementation steps **
- ** Perform cost modeling for resources:** Deploy the workload or a proof of concept into a separate account with the specific resource types and sizes to test. Run the workload with the test data and record the output results, along with the cost data for the time the test was run. Afterwards, redeploy the workload or change the resource types and sizes and run the test again. Include license fees of any products you may use with these resources and estimated operations (labor or engineer) costs for deploying and managing these resources while creating cost modeling. Consider cost modeling for a period (hourly, daily, monthly, yearly or three years).

## Resources
### Related Documents
- [AWS Auto Scaling](https://aws.amazon.com/autoscaling/)
- [ Identifying Opportunities to Right Size ](https://docs.aws.amazon.com/whitepapers/latest/cost-optimization-right-sizing/identifying-opportunities-to-right-size.html)
- [Amazon CloudWatch features](https://aws.amazon.com/cloudwatch/features/)
- [Cost Optimization: Amazon EC2 Right Sizing](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ce-rightsizing.html)
- [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/)
- [AWS Pricing Calculator ](https://calculator.aws/#/)
### Related Examples
- [ Perform a Data-Driven Cost modeling ](https://aws.amazon.com/blogs/mt/how-to-use-aws-well-architected-with-aws-trusted-advisor-to-achieve-data-driven-cost-optimization/)
- [ Estimate the cost of planned AWS resource configurations ](https://aws.amazon.com/premiumsupport/knowledge-center/estimating-aws-resource-costs/)
- [ Choose the right AWS tools ](https://www.learnaws.org/2019/09/27/choose-right-aws-tools/)
