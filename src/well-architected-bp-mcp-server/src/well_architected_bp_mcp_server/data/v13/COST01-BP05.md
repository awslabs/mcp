---
id: "COST01-BP05"
title: "Report and notify on cost optimization"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you implement cloud financial management?"
risk_level: "Low"
---

# COST01-BP05 Report and notify on cost optimization

## Implementation Guidance
 You must regularly report on cost and usage optimization within your organization. You can implement dedicated sessions to discuss cost performance, or include cost optimization in your regular operational reporting cycles for your workloads. Use services and tools to monitor your cost performances regularly and implement cost savings opportunities.

 View your cost and usage with multiple filters and granularity by using [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/), which provides dashboards and reports such as costs by service or by account, daily costs, or marketplace costs. Track your progress of cost and usage against configured budgets with [AWS Budgets Reports](https://aws.amazon.com/about-aws/whats-new/2019/07/introducing-aws-budgets-reports/).

 Use [AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/) to set custom budgets to track your costs and usage and respond quickly to alerts received from email or Amazon Simple Notification Service (Amazon SNS) notifications if you exceed your threshold. [Set your preferred budget](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-create.html) period to daily, monthly, quarterly, or annually, and create specific budget limits to stay informed on how actual or forecasted costs and usage progress toward your budget threshold. You can also set up [alerts](https://docs.aws.amazon.com/cost-management/latest/userguide/sns-alert-chime.html) and [actions](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html) against those alerts to run automatically or through an approval process when a budget target is exceeded.

 Implement notifications on cost and usage to ensure that changes in cost and usage can be acted upon quickly if they are unexpected. [AWS Cost Anomaly Detection](https://aws.amazon.com/aws-cost-management/aws-cost-anomaly-detection/) allows you to reduce cost surprises and enhance control without slowing innovation. AWS Cost Anomaly Detection identifies anomalous spend and root causes, which helps to reduce the risk of billing surprises. With three simple steps, you can create your own contextualized monitor and receive alerts when any anomalous spend is detected.

 You can also use [Quick Suite](https://aws.amazon.com/quicksight/) with AWS Cost and Usage Report (CUR) data, to provide highly customized reporting with more granular data. Quick Suite allows you to schedule reports and receive periodic Cost Report emails for historical cost and usage or cost-saving opportunities. Check our [Cost Intelligence Dashboard](https://aws.amazon.com/blogs/aws-cloud-financial-management/a-detailed-overview-of-the-cost-intelligence-dashboard/) (CID) solution built on Quick Suite, which gives you advanced visibility.

 Use [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/), which provides guidance to verify whether provisioned resources are aligned with AWS best practices for cost optimization.

 Check your Savings Plans recommendations through visual graphs against your granular cost and usage. Hourly graphs show On-Demand spend alongside the recommended Savings Plans commitment, providing insight into estimated savings, Savings Plans coverage, and Savings Plans utilization. This helps organizations to understand how their Savings Plans apply to each hour of spend without having to invest time and resources into building models to analyze their spend.

 Periodically create reports containing a highlight of Savings Plans, Reserved Instances, and Amazon EC2 rightsizing recommendations from AWS Cost Explorer to start reducing the cost associated with steady-state workloads, idle, and underutilized resources. Identify and recoup spend associated with cloud waste for resources that are deployed. Cloud waste occurs when incorrectly-sized resources are created or different usage patterns are observed instead what is expected. Follow AWS best practices to reduce your waste or ask your account team and partner to help you to [optimize and save](https://aws.amazon.com/aws-cost-management/aws-cost-optimization/) your cloud costs.

 Generate reports regularly for better purchasing options for your resources to drive down unit costs for your workloads. Purchasing options such as Savings Plans, Reserved Instances, or Amazon EC2 Spot Instances offer the deepest cost savings for fault-tolerant workloads and allow stakeholders (business owners, finance, and tech teams) to be part of these commitment discussions.

 Share the reports that contain opportunities or new release announcements that may help you to reduce total cost of ownership (TCO) of the cloud. Adopt new services, Regions, features, solutions, or new ways to achieve further cost reductions.

## Implementation Steps
- **Configure AWS Budgets:** Configure AWS Budgets on all accounts for your workload. Set a budget for the overall account spend, and a budget for the workload by using tags.
  - [Well-Architected Labs: Cost and Governance Usage](https://wellarchitectedlabs.com/Cost/Cost_Fundamentals/100_2_Cost_and_Usage_Governance/README.html)
- **Report on cost optimization:** Set up a regular cycle to discuss and analyze the efficiency of the workload. Using the metrics established, report on the metrics achieved and the cost of achieving them. Identify and fix any negative trends, as well as positive trends that you can promote across your organization. Reporting should involve representatives from the application teams and owners, finance, and key decision makers with respect to cloud expenditure.

## Resources
### Related Documents
- [AWS Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
- [AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/)
- [AWS Cost and Usage Report](https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html)
- [AWS Budgets Best Practices](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-best-practices.html#budgets-best-practices-setting-budgets%3Fsc_channel=ba%26sc_campaign=aws-budgets%26sc_medium=manage-and-control%26sc_content=web_pdp%26sc_detail=how-do-I%26sc_outcome=aw%26trk=how-do-I_web_pdp_aws-budgets)
- [Amazon S3 Analytics](https://docs.aws.amazon.com/AmazonS3/latest/userguide/analytics-storage-class.html)
### Related Examples
- [Key ways to start optimizing your AWS cloud costs](https://aws.amazon.com/blogs/aws-cloud-financial-management/key-ways-to-start-optimizing-your-aws-cloud-costs/)
