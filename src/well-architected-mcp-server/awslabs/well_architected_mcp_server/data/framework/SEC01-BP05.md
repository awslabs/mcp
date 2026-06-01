---
id: "SEC01-BP05"
title: "Reduce security management scope"
pillar: "Security"
risk_level: "MEDIUM"
capability: "How do you securely operate your workload?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate_reduce_management_scope.html"
description: "Determine if you can reduce your security scope by using AWS services that shift management of certain controls to AWS (managed services). These services can help reduce your security maintenance tasks, such as infrastructure provisioning, software setup, patching, or backups."
area: ["Security Foundations", "Operating your workloads securely"]
relatedIds: ["PERF02-BP01", "PERF03-BP01", "SUS05-BP03"]
---

# SEC01-BP05 Reduce security management scope

Determine if you can reduce your security scope by using AWS services that shift management of certain controls to AWS (*managed services*). These services can help reduce your security maintenance tasks, such as infrastructure provisioning, software setup, patching, or backups.

**Desired outcome:** You consider the scope of your security management when selecting AWS services for your workload. The cost of management overhead and maintenance tasks (the total cost of ownership, or TCO) is weighed against the cost of the services you select, in addition to other Well-Architected considerations. You incorporate AWS control and compliance documentation into your control evaluation and verification procedures.

**Common anti-patterns:**

- Deploying workloads without thoroughly understanding the shared responsibility model for the services you select.
- Hosting databases and other technologies on virtual machines without having evaluated a managed service equivalent.
- Not including security management tasks into the total cost of ownership of hosting technologies on virtual machines when compared to managed service options.

**Benefits of establishing this best practice:** Using managed services can reduce your overall burden of managing operational security controls, which can reduce your security risks and total cost of ownership. Time that would otherwise be spent on certain security tasks can be reinvested into tasks that provide more value to your business. Managed services can also reduce the scope of your compliance requirements by shifting some control requirements to AWS.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

There are multiple ways you can integrate the components of your workload on AWS. Installing and running technologies on Amazon EC2 instances often requires you to take on the largest share of the overall security responsibility. To help reduce the burden of operating certain controls, identify AWS managed services that reduce the scope of your side of the shared responsibility model and understand how you can use them in your existing architecture. Examples include using the [Amazon Relational Database Service (Amazon RDS)](https://aws.amazon.com/rds/) for deploying databases, [Amazon Elastic Kubernetes Service (Amazon EKS)](https://aws.amazon.com/eks/) or [Amazon Elastic Container Service (Amazon ECS)](https://aws.amazon.com/ecs/) for orchestrating containers, or using [serverless options](https://aws.amazon.com/serverless/). When building new applications, think through which services can help reduce time and cost when it comes to implementing and managing security controls.

Compliance requirements can also be a factor when selecting services. Managed services can shift the compliance of some requirements to AWS. Discuss with your compliance team about their degree of comfort with auditing the aspects of services you operate and manage and accepting control statements in relevant AWS audit reports. You can provide the audit artifacts found in [AWS Artifact](https://aws.amazon.com/artifact/) to your auditors or regulators as evidence of AWS security controls. You can also use the responsibility guidance provided by some of the AWS audit artifacts to design your architecture, along with the [AWS Customer Compliance Guides](https://d1.awsstatic.com/whitepapers/compliance/AWS_Customer_Compliance_Guides.pdf). This guidance helps determine the additional security controls you should put in place in order to support the specific use cases of your system.

When using managed services, be familiar with the process of updating their resources to newer versions (for example, updating the version of a database managed by Amazon RDS, or a programming language runtime for an AWS Lambda function). While the managed service may perform this operation for you, configuring the timing of the update and understanding the impact on your operations remains your responsibility. Tools like [AWS Health](https://aws.amazon.com/premiumsupport/technology/aws-health/) can help you track and manage these updates throughout your environments.

### Implementation steps

- Evaluate the components of your workload that can be replaced with a managed service.

If you are migrating a workload to AWS, consider the reduced management (time and expense) and reduction of risk when you assess if you should rehost, refactor, replatform, rebuild, or replace your workload. Sometimes additional investment at the start of a migration can have significant savings in the long run.

- Consider implementing managed services, like Amazon RDS, instead of installing and managing your own technology deployments.
- Use the responsibility guidance in AWS Artifact to help determine the security controls you should put in place for your workload.
- Keep an inventory of resources in use, and stay up-to-date with new services and approaches to identify new opportunities to reduce scope.

## Resources

**Related best practices:**

- [PERF02-BP01
Select the best compute options for your workload](https://docs.aws.amazon.com/wellarchitected/latest/framework/perf_compute_hardware_select_best_compute_options.html)
- [PERF03-BP01
Use a purpose-built data store that best supports your data
access and storage requirements](https://docs.aws.amazon.com/wellarchitected/latest/framework/perf_data_use_purpose_built_data_store.html)
- [SUS05-BP03
Use managed services](https://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_hardware_a4.html)

**Related documents:**

- [Planned
lifecycle events for AWS Health](https://docs.aws.amazon.com/health/latest/ug/aws-health-planned-lifecycle-events.html)

**Related tools:**

- [AWS Health](https://docs.aws.amazon.com/health/latest/ug/what-is-aws-health.html)
- [AWS Artifact](https://aws.amazon.com/artifact/)
- [AWS Customer Compliance Guides](https://d1.awsstatic.com/whitepapers/compliance/AWS_Customer_Compliance_Guides.pdf)

**Related videos:**

- [How
do I migrate to an Amazon RDS or Aurora MySQL DB instance
using AWS DMS?](https://www.youtube.com/watch?v=vqgSdD5vkS0)
- [AWS re:Invent 2023 - Manage resource lifecycle events at scale
with AWS Health](https://www.youtube.com/watch?v=VoLLNL5j9NA)
