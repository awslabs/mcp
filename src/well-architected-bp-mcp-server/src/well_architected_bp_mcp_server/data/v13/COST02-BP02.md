---
id: "COST02-BP02"
title: "Implement goals and targets"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you govern usage?"
risk_level: "High"
---

# COST02-BP02 Implement goals and targets

## Implementation Guidance
 Develop cost and usage goals and targets for your organization. As a growing organization on AWS, it is important to set and track goals for cost optimization. These goals or [key performance indicators (KPIs)](https://aws.amazon.com/blogs/aws-cloud-financial-management/unit-metric-the-touchstone-of-your-it-planning-and-evaluation/) can include things like percent of spend on-demand or adoption of certain optimized services such as AWS Graviton instances or gp3 EBS volume types. Set measurable and achievable goals to help you measure efficiency improvements, which is important for your business operations. Goals provide guidance and direction to your organization on expected outcomes.

 Targets provide specific, measurable outcomes to be achieved. In short, a goal is the direction you want to go, and a target is how far in that direction and when that goal should be achieved (use guidance of specific, measurable, assignable, realistic and timely, or SMART). An example of a goal is that platform usage should increase significantly, with only a minor (non-linear) increase in cost. An example target is a 20% increase in platform usage, with less than a five percent increase in costs. Another common goal is that workloads need to be more efficient every six months. The accompanying target would be that the cost per business metrics needs to decrease by five percent every six months. Use the right metrics, and set calculated KPIs for your organization. You can start with basic KPIs and evolve later based on business needs.

 A goal for cost optimization is to increase workload efficiency, which corresponds to a decrease in the cost per business outcome of the workload over time. Implement this goal for all workloads, and set a target like a five percent increase in efficiency every six months to a year. In the cloud, you can achieve this through the establishment of capability in cost optimization, as well as new service and feature releases.

 Targets are the quantifiable benchmarks you want to reach to meet your goals and benchmarks compare your actual results against a target. Establish benchmarks with KPIs for the cost per unit of compute services (such as Spot adoption, Graviton adoption, latest instance types, and On-Demands coverage), storage services (such as EBS GP3 adoption, obsolete EBS snapshots, and Amazon S3 standard storage), or database service usage (such as RDS open-source engines, Graviton adoption, and On-demand coverage). These benchmarks and KPIs can help you verify that you use AWS services in the most cost-effective manner.

 The following table provides a list of standard AWS metrics for reference. Each organization can have different target values for these KPIs.

|  Category  |  KPI (%)  |  Description  |
| --- | --- | --- |
|  Compute  |  EC2 usage Coverage  |  EC2 instances (in cost or hours) using SP\$1RI\$1Spot compared to total (in cost or hours) of EC2 instances  |
|  Compute  |  Compute SP/RI utilization  |  Utilized SP or RI hours compared to total available SP or RI hours  |
|  Compute  |  EC2/Hour cost  |  EC2 cost divided by the number of EC2 instances running in that hour  |
|  Compute  |  vCPU cost  |  Cost per vCPU for all instances  |
|  Compute  |  Latest Instance Generation  |  Percentage of instances on Graviton (or other modern generation instance types)  |
|  Database  |  RDS coverage  |  RDS instances (in cost or hours) using RI compared to total (in cost or hours) of RDS instances  |
|  Database  |  RDS utilization  |  Utilized RI hours compared to total available RI hours  |
|  Database  |  RDS uptime  |  RDS cost divided by the number of RDS instances running in that hour  |
|  Database  |  Latest Instance Generation  |  Percentage of instances on Graviton (or other modern instance types)  |
|  Storage  |  Storage utilization  |  Optimized storage cost (for example Glacier, deep archive, or Infrequent Access) divided by total storage cost  |
|  Tagging  |  Untagged resources  |   Cost Explorer:   1. Filter out credits, discounts, taxes, refunds, marketplace, and copy the latest monthly cost   2. Select **Show only untagged resources** in Cost Explorer   3. Divide the amount in **untagged resources** with your monthly cost.   |

 Using this table, include target or benchmark values, which should be calculated based on your organizational goals. You need to measure certain metrics for your business and understand business outcome for that workload to define accurate and realistic KPIs. When you evaluate performance metrics within an organization, distinguish between different types of metrics that serve distinct purposes. These metrics primarily measure the performance and efficiency of the technical infrastructure rather than directly the overall business impact. For instance, they might track server response times, network latency, or system uptime. These metrics are crucial to assess how well the infrastructure supports the organization's technical operations. However, they don't provide direct insight into broader business objectives like customer satisfaction, revenue growth, or market share. To gain a comprehensive understanding of business performance, complement these efficiency metrics with strategic business metrics that directly correlate with business outcomes.

 Establish near real-time visibility over your KPIs and related savings opportunities and track your progress over time. To get started with the definition and tracking of KPI goals, we recommend the KPI dashboard from [Cloud Intelligence Dashboards](https://wellarchitectedlabs.com/cloud-intelligence-dashboards/) (CID). Based on the data from Cost and Usage Report (CUR), the KPI dashboard provides a series of recommended cost optimization KPIs, with the ability to set custom goals and track progress over time.

 If you have other solutions to set and track KPI goals, make sure these methods are adopted by all cloud financial management stakeholders in your organization.

## Implementation Steps
- **Define expected usage levels:** To begin, focus on usage levels. Engage with the application owners, marketing, and greater business teams to understand what the expected usage levels are for the workload. How might customer demand change over time, and what can change due to seasonal increases or marketing campaigns?
- **Define workload resourcing and costs:** With usage levels defined, quantify the changes in workload resources required to meet those usage levels. You may need to increase the size or number of resources for a workload component, increase data transfer, or change workload components to a different service at a specific level. Specify the costs at each of these major points, and predict the change in cost when there is a change in usage.
- **Define business goals:** Take the output from the expected changes in usage and cost, combine this with expected changes in technology, or any programs that you are running, and develop goals for the workload. Goals must address usage and cost, as well as the relationship between the two. Goals must be simple, high-level, and help people understand what the business expects in terms of outcomes (such as making sure unused resources are kept below certain cost level). You don't need to define goals for each unused resource type or define costs that can cause losses in goals and targets. Verify that there are organizational programs (for example, capability building like training and education) if there are expected changes in cost without changes in usage.
- **Define targets:** For each of the defined goals, specify a measurable target. If the goal is to increase efficiency in the workload, the target should quantify the amount of improvement (typically in business outputs for each dollar spent) and when it should be delivered. For example, you could set a goal to minimize waste due to over-provisioning. With this goal, your target can be that waste due to compute over-provisioning in the first tier of production workloads should not exceed ten percent of tier compute cost. Additionally, a second target could be that waste due to compute over-provisioning in the second tier of production workloads should not exceed five percent of tier compute cost.

## Resources
### Related Documents
- [AWS managed policies for job functions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_job-functions.html)
- [AWS multiple account billing strategy](https://aws.amazon.com/answers/account-management/aws-multi-account-billing-strategy/)
- [Control access to AWS Regions using IAM policies](https://aws.amazon.com/blogs/security/easier-way-to-control-access-to-aws-regions-using-iam-policies/)
- [S.M.A.R.T. Goals](https://en.wikipedia.org/wiki/SMART_criteria)
- [How to track your cost optimization KPIs with the CID KPI Dashboard](https://aws.amazon.com/blogs/aws-cloud-financial-management/how-to-track-your-cost-optimization-kpis-with-the-kpi-dashboard/)
### Related Videos
- [Well-Architected Labs: Goals and Targets (Level 100)](https://catalog.workshops.aws/well-architected-cost-optimization/en-US/2-expenditure-and-usage-awareness/150-goals-and-targets)
### Related Examples
- [What is a unit metric](https://aws.amazon.com/blogs/aws-cloud-financial-management/what-is-a-unit-metric/)?
- [Selecting a unit metric to support your business](https://aws.amazon.com/blogs/aws-cost-management/selecting-a-unit-metric-to-support-your-business/)
- [Unit metrics in practice – lessons learned](https://aws.amazon.com/blogs/aws-cost-management/unit-metrics-in-practice-lessons-learned/)
- [How unit metrics help create alignment between business functions](https://aws.amazon.com/blogs/aws-cost-management/unit-metrics-help-create-alignment-between-business-functions/)
