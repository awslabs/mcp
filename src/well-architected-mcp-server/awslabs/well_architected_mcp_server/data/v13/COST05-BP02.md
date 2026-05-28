---
id: "COST05-BP02"
title: "Analyze all components of the workload"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you evaluate cost when you select services?"
risk_level: "High"
---

# COST05-BP02 Analyze all components of the workload

## Implementation Guidance
 Workload components, which are designed to deliver business value to the organization, may encompass various services. For each component, one might choose specific AWS Cloud services to address business needs. This selection could be influenced by factors such as familiarity with or prior experience using these services.

 After identifying your organization's requirements as mentioned in [COST05-BP01 Identify organization requirements for cost](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_select_service_requirements.html), perform a thorough analysis on all components in your workload. Analyze each component considering current and projected costs and sizes. Consider the cost of analysis against any potential workload savings over its lifecycle. The effort expended on the analysis of all components of this workload should correspond to the potential savings or improvements anticipated from optimization of that specific component. For example, if the cost of the proposed resource is \$110 per month, and under forecasted loads would not exceed \$115 per month, spending a day of effort to reduce costs by 50% (five dollars per month) could exceed the potential benefit over the life of the system. Use a faster and more efficient data-based estimation to create the best overall outcome for this component.

 Workloads can change over time, and the right set of services may not be optimal if the workload architecture or usage changes. Analysis for selection of services must incorporate current and future workload states and usage levels. Implementing a service for future workload state or usage may reduce overall costs by reducing or removing the effort required to make future changes. For example, using EMR Serverless might be the appropriate choice initially. However, as consumption for that service increases, transitioning to EMR on EC2 could reduce costs for that component of the workload.

 [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) and the AWS Cost and Usage Reports ([CUR](https://aws.amazon.com/aws-cost-management/aws-cost-and-usage-reporting/)) can analyze the cost of a proof of concept (PoC) or running environment. You can also use [AWS Pricing Calculator](https://calculator.aws/#/) to estimate workload costs.

 Write a workflow to be followed by technical teams to review their workloads. Keep this workflow simple, but also cover all the necessary steps to make sure the teams understand each component of the workload and its pricing. Your organization can then follow and customize this workflow based on the specific needs of each team.

1.  **List each service in use for your workload:** This is a good starting point. Identify all of the services currently in use and where costs are originate from.

1.  **Understand how pricing works for those services:** Understand the [pricing model](https://aws.amazon.com/pricing/) of each service. Different AWS services have different pricing models based on factors like usage volume, data transfer, and feature-specific pricing.

1.  **Focus on the services that have unexpected workload costs and that do not align with your expected usage and business outcome:** Identify outliers or services where the cost is not proportional to the value or usage by using AWS Cost Explorer or AWS Cost and Usage Reports. It's important to correlate costs with business outcomes to prioritize optimization efforts.

1.  **AWS Cost Explorer, CloudWatch Logs, VPC Flow Logs, and Amazon S3 Storage Lens to understand the root cause of those high costs:** These tools are instrumental in the diagnosis of high costs. Each service offers a different lens to view and analyze usage and costs. For instance, Cost Explorer helps determine overall cost trends, CloudWatch Logs provides operational insights, VPC Flow Logs displays IP traffic, and Amazon S3 Storage Lens is useful for storage analytics.

1.  **Use AWS Budgets to set budgets for certain amounts for services or accounts:** Setting budgets is a proactive way to manage costs. Use AWS Budgets to set custom budget thresholds and receive alerts when costs exceed those thresholds.

1.  **Configure Amazon CloudWatch alarms to send billing and usage alerts:** Set up monitoring and alerts for cost and usage metrics. CloudWatch alarms can notify you when certain thresholds are breached, which improves intervention response time.

 Facilitate notable enhancement and financial savings over time through strategic review of all workload components and irrespective of their present attributes. The effort invested in this review process should be deliberate, with careful consideration of the potential advantages that might be realized.

## Implementation Steps
- **List the workload components:** Build a list of your workload's components. Use this list to verify that each component was analyzed. The effort spent should reflect the criticality to the workload as defined by your organization's priorities. Group together resources functionally to improve efficiency (for example, production database storage, if there are multiple databases).
- **Prioritize the component list:** Take the component list and prioritize it in order of effort. This is typically in order of the cost of the component, from most expensive to least expensive or the criticality as defined by your organization's priorities.
- **Perform the analysis:** For each component on the list, review the options and services available, and choose the option that aligns best with your organizational priorities.

## Resources
### Related Documents
- [AWS Pricing Calculator](https://calculator.aws/#/)
- [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
- [Amazon S3 storage classes](https://aws.amazon.com/s3/storage-classes/)
- [AWS Cloud products](https://aws.amazon.com/products/)
### Related Videos
- [AWS Cost Optimization Series: CloudWatch](https://www.youtube.com/watch?v=6imTJUGEzjU)
