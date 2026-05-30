---
id: "COST02-BP06"
title: "Track project lifecycle"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you govern usage?"
risk_level: "Low"
---

# COST02-BP06 Track project lifecycle

## Implementation Guidance
 By effectively tracking the project lifecycle, organizations can achieve better cost control through enhanced planning, management, and resource optimization. The insights gained through tracking are invaluable for making informed decisions that contribute to the cost-effectiveness and overall success of the project.

 Tracking the entire lifecycle of the workload helps you understand when workloads or workload components are no longer required. The existing workloads and components may appear to be in use, but when AWS releases new services or features, they can be decommissioned or adopted. Check the previous stages of workloads. After a workload is in production, previous environments can be decommissioned or greatly reduced in capacity until they are required again.

 You can tag resources with a timeframe or reminder to pin the time that the workload was reviewed. For example, if the development environment was last reviewed months ago, it could be a good time to review it again to explore if new services can be adopted or if the environment is in use. You can group and tag your applications with [myApplications](https://docs.aws.amazon.com/awsconsolehelpdocs/latest/gsg/aws-myApplications.html) on AWS to manage and track metadata such as criticality, environment, last reviewed, and cost center. You can both track your workload's lifecycle and monitor and manage the cost, health, security posture, and performance of your applications.

 AWS provides various management and governance services you can use for entity lifecycle tracking. You can use [https://aws.amazon.com/config/](https://aws.amazon.com/config/) or [https://aws.amazon.com/systems-manager/](https://aws.amazon.com/systems-manager/) to provide a detailed inventory of your AWS resources and configuration. It is recommended that you integrate with your existing project or asset management systems to keep track of active projects and products within your organization. Combining your current system with the rich set of events and metrics provided by AWS allows you to build a view of significant lifecycle events and proactively manage resources to reduce unnecessary costs.

 Similar to [Application Lifecycle Management (ALM)](https://aws.amazon.com/what-is/application-lifecycle-management/), tracking project lifecycle should involve multiple processes, tools, and teams working together, such as design and development, testing, production, support, and workload redundancy.

 By carefully monitoring each phase of a project's lifecycle, organizations gain crucial insights and enhanced control, facilitating successful project planning, implementation, and completion. This careful oversight verifies that projects not only meet quality standards, but are delivered on time and within budget, promoting overall cost efficiency.

 For more details on implementing entity lifecycle tracking, see [https://aws.amazon.com/architecture/well-architected/](https://aws.amazon.com/architecture/well-architected/).

## Implementation Steps
- **Establish project lifecycle monitoring process:** [The Cloud Center of Excellence team](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_cloud_financial_management_function.html) must establish project lifecycle monitoring process. Establish a structured and systematic approach to monitoring workloads in order to improve control, visibility, and performance of the projects. Make the monitoring process transparent, collaborative, and focused on continuous improvement to maximize its effectiveness and value.
- **Perform workload reviews:** As defined by your organizational policies, set up a regular cadence to audit your existing projects and perform workload reviews. The amount of effort spent in the audit should be proportional to the approximate risk, value, or cost to the organization. Key areas to include in the audit would be risk to the organization of an incident or outage, value, or contribution to the organization (measured in revenue or brand reputation), cost of the workload (measured as total cost of resources and operational costs), and usage of the workload (measured in number of organization outcomes per unit of time). If these areas change over the lifecycle, adjustments to the workload are required, such as full or partial decommissioning.

## Resources
### Related Documents
- [Guidance for Tagging on AWS](https://aws.amazon.com/solutions/guidance/tagging-on-aws/)
- [What Is ALM (Application Lifecycle Management)?](https://aws.amazon.com/what-is/application-lifecycle-management/)
- [AWS managed policies for job functions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_job-functions.html)
### Related Examples
- [Control access to AWS Regions using IAM policies](https://aws.amazon.com/blogs/security/easier-way-to-control-access-to-aws-regions-using-iam-policies/)
### Related Tools
- [AWS Config](https://aws.amazon.com/config/)
- [AWS Systems Manager](https://aws.amazon.com/systems-manager/)
- [AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/)
- [AWS Organizations](https://aws.amazon.com/organizations/)
- [AWS CloudFormation](https://aws.amazon.com/cloudformation/?c=mg&sec=srv)
