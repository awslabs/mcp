---
id: "COST11-BP01"
title: "Perform automation for operations"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you evaluate the cost of effort?"
risk_level: "Low"
---

# COST11-BP01 Perform automation for operations

## Implementation Guidance
 Automating operations reduces the frequency of manual tasks, improves efficiency, and benefits customers by delivering a consistent and reliable experience when deploying, administering, or operating workloads. You can free up infrastructure resources from manual operational tasks and use them for higher value tasks and innovations, which improves business value. Enterprises require a proven, tested way to manage their workloads in the cloud. That solution must be secure, fast, and cost effective, with minimum risk and maximum reliability.

 Start by prioritizing your operational activities based on required effort by looking at overall operations cost. For example, how long does it take to deploy new resources in the cloud, make optimization changes to existing ones, or implement necessary configurations? Look at the total cost of human actions by factoring in cost of operations and management. Prioritize automations for admin tasks to reduce the human effort.

 Review effort should reflect the potential benefit. For example, examine time spent performing tasks manually as opposed to automatically. Prioritize automating repetitive, high value, time consuming and complex activities. Activities that pose a high value or high risk of human error are typically the better place to start automating as the risk often poses an unwanted additional operational cost (like operations team working extra hours).

 Use automation tools like AWS Systems Manager or AWS Config to streamline operations, compliance, monitoring, lifecycle, and termination processes. With AWS services, tools, and third-party products, you can customize the automations you implement to meet your specific requirement. Following table shows some of the core operation functions and capabilities you can achieve with AWS services to automate administration and operation:
- [AWS Audit Manager](https://aws.amazon.com/audit-manager/): Continually audit your AWS usage to simplify risk and compliance assessment
- [AWS Backup](https://aws.amazon.com/backup/): Centrally manage and automate data protection.
- [AWS Config:](https://aws.amazon.com/config/) Configure compute resources, asses, audit, evaluate configurations and resource inventory.
- [AWS CloudFormation](https://aws.amazon.com/cloudformation/): Launch highly available resources with Infrastructure as Code.
- [AWS CloudTrail](https://aws.amazon.com/cloudtrail/): IT change management, compliance, and control.
- [Amazon EventBridge](https://aws.amazon.com/eventbridge/) Schedule events and trigger AWS Lambda to take action.
- [AWS Lambda](https://aws.amazon.com/lambda/): Automate repetitive processes by triggering them with events or by running them on a fixed schedule with AWS EventBridge.
- [AWS Systems Manager](https://aws.amazon.com/systems-manager/): Start and stop workloads, patch operating systems, automate configuration, and ongoing management.
- [AWS Step Functions](https://aws.amazon.com/step-functions/): Schedule jobs and automate workflows.
- [AWS Service Catalog](https://aws.amazon.com/servicecatalog/): Template consumption, infrastructure as code with compliance and control.

 If you would like to adopt automations immediately by using AWS products and service and if don't have skills in your organization, reach out to [AWS Managed Services (AMS)](https://aws.amazon.com/managed-services/), [AWS Professional Services](https://aws.amazon.com/professional-services/), or [AWS Partners](https://aws.amazon.com/partners/work-with-partners/?nc2=h_ql_pa_wwap_cp) to increase adoption of automation and improve your operational excellence in the cloud.

 AWS Managed Services (AMS) is a service that operates AWS infrastructure on behalf of enterprise customers and partners. It provides a secure and compliant environment that you can deploy your workloads onto. AMS uses enterprise cloud operating models with automation to allow you to meet your organization requirements, move into the cloud faster, and reduce your on-going management costs.

 AWS Professional Services can also help you achieve your desired business outcomes and automate operations with AWS. They help customers to deploy automated, robust, agile IT operations, and governance capabilities optimized for the cloud. For detailed monitoring examples and recommended best practices, see Operational Excellence Pillar whitepaper.

## Implementation Steps
- **Build once and deploy many**: Use infrastructure-as-code such as CloudFormation, AWS SDK, or AWS CLI to deploy once and use many times for similar environments or for disaster recovery scenarios. Tag while deploying to track your consumption as defined in other best practices. Use [AWS Launch Wizard](https://aws.amazon.com/launchwizard/) to reduce the time to deploy many popular enterprise workloads. AWS Launch Wizard guides you through the sizing, configuration, and deployment of enterprise workloads following AWS best practices. You can also use the [Service Catalog](https://aws.amazon.com/servicecatalog/), which helps you create and manage infrastructure-as-code approved templates for use on AWS so anyone can discover approved, self-service cloud resources.
- **Automate continuous compliance:** Consider automating assessment and remediation of recorded configurations against predefined standards. When you combine AWS Organizations with the capabilities of AWS Config and [AWS CloudFormation](https://aws.amazon.com/cloudformation/), you can efficiently manage and automate configuration compliance at scale for hundreds of member accounts. You can review changes in configurations and relationships between AWS resources and dive into the history of a resource configuration.
- **Automate monitoring tasks** AWS provides various tools that you can use to monitor services. You can configure these tools to automate monitoring tasks. Create and implement a monitoring plan that collects monitoring data from all the parts in your workload so that you can more easily debug a multi-point failure if one occurs. For example, you can use the automated monitoring tools to observe Amazon EC2 and report back to you when something is wrong for system status checks, instance status checks, and Amazon CloudWatch alarms.
- **Automate maintenance and operations**: Run routine operations automatically without human intervention. Using AWS services and tools, you can choose which AWS automations to implement and customize for your specific requirements. For example, use [EC2 Image Builder](https://aws.amazon.com/image-builder/) for building, testing, and deployment of virtual machine and container images for use on AWS or on-premises or patching your EC2 instances with AWS SSM. If your desired action cannot be done with AWS services or you need more complex actions with filtering resources, then automate your operations by using [AWS Command Line Interface](https://docs.aws.amazon.com/cli/index.html) (AWS CLI) or AWS SDK tools. AWS CLI provides the ability to automate the entire process of controlling and managing AWS services with scripts without using the AWS Management Console. Select your preferred AWS SDKs to interact with AWS services. For other code examples, see AWS SDK Code [examples repository](https://github.com/awsdocs/aws-doc-sdk-examples).
- **Create a continual lifecycle with automations:** It is important that you establish and preserve mature lifecycle policies not only for regulations or redundancy but also for cost optimization. You can use AWS Backup to centrally manage and automate data protection of data stores, such as your buckets, volumes, databases, and file systems. You can also use Amazon Data Lifecycle Manager to automate the creation, retention, and deletion of EBS snapshots and EBS-backed AMIs.
- **Delete unnecessary resources:** It's quite common to accumulate unused resources in sandbox or development AWS accounts. Developers create and experiment with various services and resources as part of the normal development cycle, and then they don't delete those resources when they're no longer needed. Unused resources can incur unnecessary and sometimes high costs for the organization. Deleting these resources can reduce the costs of operating these environments. Make sure your data is not needed or backed up if you are not sure. You can use AWS CloudFormation to clean up deployed stacks, which automatically deletes most resources defined in the template. Alternatively, you can create an automation for the deletion of AWS resources using tools like [aws-nuke](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/automate-deletion-of-aws-resources-by-using-aws-nuke.html).

## Resources
### Related Documents
- [Modernizing operations in the AWS Cloud](https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-operations-integration)
- [AWS Services for Automation](https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-operations-integration/aws-services-for-automation.html)
- [Infrastructure and automation](https://aws.amazon.com/blogs/infrastructure-and-automation/)
- [AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)
- [Automated and manual monitoring](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring_automated_manual.html)
- [AWS automations for SAP administration and operations](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-sap-automation/automations.html)
- [AWS Managed Services](https://docs.aws.amazon.com/managedservices/index.html)
- [AWS Professional Services](https://aws.amazon.com/professional-services/)
### Related Videos
- [Automate Continuous Compliance at Scale in AWS](https://www.youtube.com/watch?v=5WOL8Njvx48)
- [AWS Backup Demo: Cross-Account & Cross-Region Backup](https://www.youtube.com/watch?v=dCy7ixko3tE)
- [Patching for your Amazon EC2 Instances](https://www.youtube.com/watch?v=ABtwRb9BFY4)
### Related Examples
- [Reinventing automated operations (Part I)](https://aws.amazon.com/blogs/mt/reinventing-automated-operations-part-i/)
- [Reinventing automated operations (Part II)](https://aws.amazon.com/blogs/mt/reinventing-automated-operations-part-ii/)
- [Automate deletion of AWS resources by using aws-nuke](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/automate-deletion-of-aws-resources-by-using-aws-nuke.html)
- [Delete unused Amazon EBS volumes by using AWS Config and AWS SSM](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/delete-unused-amazon-elastic-block-store-amazon-ebs-volumes-by-using-aws-config-and-aws-systems-manager.html)
- [Automate continuous compliance at scale in AWS](https://aws.amazon.com/blogs/mt/automate-cloud-foundational-services-for-compliance-in-aws/)
- [IT Automations with AWS Lambda](https://aws.amazon.com/lambda/it-automation/)
