---
id: "COST06-BP04"
title: "Consider using shared resources"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you meet cost targets when you select resource type, size and number?"
risk_level: "Medium"
---

# COST06-BP04 Consider using shared resources

## Implementation Guidance
 Where multiple workloads cause the same function, use existing solutions and shared components to improve management and optimize costs. Consider using existing resources (especially shared ones), such as non-production database servers or directory services, to mitigate cloud costs by following security best practices and organizational regulations. For optimal value realization and efficiency, it is crucial to allocate costs back (using showback and chargeback) to the pertinent areas of the business driving consumption.

 *Showback* refers to reports that break down cloud costs into attributable categories, such as consumers, business units, general ledger accounts, or other responsible entities. The goal of showback is to show teams, business units, or individuals the cost of their consumed cloud resources.

 *Chargeback* means to allocate central service spend to cost units based on a strategy suitable for a specific financial management process. For customers, chargeback charges the cost incurred from one shared services account to different financial cost categories suitable for a customer reporting process. By establishing chargeback mechanisms, you can report costs incurred by different business units, products, and teams.

 Workloads can be categorized as critical and non-critical. Based on this classification, use shared resources with general configurations for less critical workloads. To further optimize costs, reserve dedicated servers solely for critical workloads. Share resources or provision them across several accounts to manage them efficiently. Even with distinct development, testing, and production environments, secure sharing is feasible and does not compromise organizational structure.

 To improve your understanding and optimize cost and usage for containerized applications, use split cost allocation data which helps you allocate costs to individual business entities based on how the application consumes shared compute and memory resources. Split cost allocation data helps you achieve task-level showback and chargeback in container workloads running on Amazon Elastic Container Service (Amazon ECS) or Amazon Elastic Kubernetes Service (Amazon EKS).

 For distributed architectures, build a shared services VPC, which provides centralized access to shared services required by workloads in each of the VPCs. These shared services can include resources such as directory services or VPC endpoints. To reduce administrative overhead and cost, share resources from a central location instead of building them in each VPC.

 When you use shared resources, you can save on operational costs, maximize resource utilization, and improve consistency. In a multi-account design, you can host some AWS services centrally and access them using several applications and accounts in a hub to save cost. You can use [AWS Resource Access Manager (AWS RAM)](https://aws.amazon.com/ram/) to share other common resources, such as [VPC subnets and AWS Transit Gateway attachments](https://docs.aws.amazon.com/ram/latest/userguide/shareable.html#shareable-vpc), [AWS Network Firewall](https://docs.aws.amazon.com/ram/latest/userguide/shareable.html#shareable-network-firewall), or [Amazon SageMaker AI pipelines](https://docs.aws.amazon.com/ram/latest/userguide/shareable.html#shareable-sagemaker). In a multi-account environment, use AWS RAM to create a resource once and share it with other accounts.

 Organizations should tag shared costs effectively and verify that they do not have a significant portion of their costs untagged or unallocated. If you do not allocate shared costs effectively and no one takes accountability for shared costs management, shared cloud costs can spiral. You should know where you have incurred costs at the resource, workload, team, or organization level, as this knowledge enhances your understanding of the value delivered at the applicable level when compared to the business outcomes achieved. Ultimately, organizations benefit from cost savings as a result of sharing cloud infrastructure. Encourage cost allocation on shared cloud resources to optimize cloud spend.

## Implementation Steps
- **Evaluate existing resources:** Review existing workloads that use similar services for your workload. Depending on the workload’s components, consider existing platforms if business logic or technical requirement allow.
- **Use resource sharing in AWS RAM and restrict accordingly:** Use AWS RAM to share resources with other AWS accounts within your organization. When you share resources, you don’t need to duplicate resources in multiple accounts, which minimizes the operational burden of resource maintenance. This process also helps you securely share the resources that you have created with roles and users in your account, as well as with other AWS accounts.
- **Tag resources:** Tag resources that are candidates for cost reporting and categorize them within cost categories. Activate these cost related resource tags for cost allocation to provide visibility of AWS resources usage. Focus on creating an appropriate level of granularity with respect to cost and usage visibility, and inﬂuence cloud consumption behaviors through cost allocation reporting and KPI tracking.

## Resources
### Related Best Practices
- [ SEC03-BP08 Share resources securely within your organization ](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_permissions_share_securely.html)
### Related Documents
- [ What is AWS Resource Access Manager? ](https://docs.aws.amazon.com/ram/latest/userguide/what-is.html)
- [AWS services that you can use with AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_integrate_services_list.html)
- [ Shareable AWS resources ](https://docs.aws.amazon.com/ram/latest/userguide/shareable.html)
- [AWS Cost and Usage (CUR) Queries ](https://catalog.workshops.aws/cur-query-library/en-US)
### Related Videos
- [AWS Resource Access Manager - granular access control with managed permissions ](https://www.youtube.com/watch?v=X3HskbPqR2s)
- [ How to design your AWS cost allocation strategy ](https://pages.awscloud.com/aws-cfm-talks-how-to-design-your-AWS-cost-allocation-strategy-01122022.html)
- [AWS Cost Categories ](https://www.youtube.com/watch?v=84GYnBBM0Cg)
### Related Examples
- [ How-to chargeback shared services: An AWS Transit Gateway example ](https://aws.amazon.com/blogs/aws-cloud-financial-management/gs-chargeback-shared-services-an-aws-transit-gateway-example/)
- [ How to build a chargeback/showback model for Savings Plans using the CUR ](https://aws.amazon.com/blogs/aws-cloud-financial-management/how-to-build-a-chargeback-showback-model-for-savings-plans-using-the-cur/)
- [ Using VPC Sharing for a Cost-Effective Multi-Account Microservice Architecture ](https://aws.amazon.com/blogs/architecture/using-vpc-sharing-for-a-cost-effective-multi-account-microservice-architecture/)
- [ Improve cost visibility of Amazon EKS with AWS Split Cost Allocation Data ](https://aws.amazon.com/blogs/aws-cloud-financial-management/improve-cost-visibility-of-amazon-eks-with-aws-split-cost-allocation-data/)
- [ Improve cost visibility of Amazon ECS and AWS Batch with AWS Split Cost Allocation Data ](https://aws.amazon.com/blogs/aws-cloud-financial-management/la-improve-cost-visibility-of-containerized-applications-with-aws-split-cost-allocation-data-for-ecs-and-batch-jobs/)
