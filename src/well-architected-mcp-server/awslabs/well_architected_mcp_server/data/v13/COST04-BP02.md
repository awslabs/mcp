---
id: "COST04-BP02"
title: "Implement a decommissioning process"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you decommission resources?"
risk_level: "High"
---

# COST04-BP02 Implement a decommissioning process

## Implementation Guidance
Implement a standardized process across your organization to identify and remove unused resources. The process should define the frequency searches are performed and the processes to remove the resource to verify that all organization requirements are met.

## Implementation Steps
- **Create and implement a decommissioning process:** Work with the workload developers and owners to build a decommissioning process for the workload and its resources. The process should cover the method to verify if the workload is in use, and also if each of the workload resources are in use. Detail the steps necessary to decommission the resource, removing them from service while ensuring compliance with any regulatory requirements. Any associated resources should be included, such as licenses or attached storage. Notify the workload owners that the decommissioning process has been started.

   Use the following decommission steps to guide you on what should be checked as part of your process:
  - **Identify resources to be decommissioned:** Identify resources that are eligible for decommissioning in your AWS Cloud. Record all necessary information and schedule the decommission. In your timeline, be sure to account for if (and when) unexpected issues arise during the process.
  - **Coordinate and communicate:** Work with workload owners to confirm the resource to be decommissioned
  - **Record metadata and create backups:** Record metadata (such as public IPs, Region, AZ, VPC, Subnet, and Security Groups) and create backups (such as Amazon Elastic Block Store snapshots or taking AMI, keys export, and Certificate export) if it is required for the resources in the production environment or if they are critical resources.
  - **Validate infrastructure-as-code:** Determine whether resources were deployed with AWS CloudFormation, Terraform, AWS Cloud Development Kit (AWS CDK), or any other infrastructure-as-code deployment tool so they can be re-deployed if necessary.
  - **Prevent access:** Apply restrictive controls for a period of time, to prevent the use of resources while you determine if the resource is required. Verify that the resource environment can be reverted to its original state if required.
  - **Follow your internal decommissioning process:** Follow the administrative tasks and decommissioning process of your organization, like removing the resource from your organization domain, removing the DNS record, and removing the resource from your configuration management tool, monitoring tool, automation tool and security tools.

   If the resource is an Amazon EC2 instance, consult the following list. [For more detail, see How do I delete or terminate my Amazon EC2 resources?](https://aws.amazon.com/premiumsupport/knowledge-center/delete-terminate-ec2/)
  - Stop or terminate all your Amazon EC2 instances and load balancers. Amazon EC2 instances are visible in the console for a short time after they're terminated. You aren't billed for any instances that aren't in the running state
  - Delete your Auto Scaling infrastructure.
  - Release all Dedicated Hosts.
  - Delete all Amazon EBS volumes and Amazon EBS snapshots.
  - Release all Elastic IP addresses.
  - Deregister all Amazon Machine Images (AMIs).
  - Terminate all AWS Elastic Beanstalk environments.

   If the resource is an object in Amazon Glacier storage and if you delete an archive before meeting the minimum storage duration, you will be charged a prorated early deletion fee. Amazon Glacier minimum storage duration depends on the storage class used. For a summary of minimum storage duration for each storage class, see [Performance across the Amazon S3 storage classes](https://aws.amazon.com/s3/storage-classes/?nc=sn&loc=3#Performance_across_the_S3_Storage_Classes). For detail on how early deletion fees are calculated, see [Amazon S3 pricing](https://aws.amazon.com/s3/pricing/).

 The following simple decommissioning process flowchart outlines the decommissioning steps. Before decommissioning resources, verify that resources you have identified for decommissioning are not being used by the organization.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/decommissioning-process-flowchart.png)

## Resources
### Related Documents
- [AWS Auto Scaling](https://aws.amazon.com/autoscaling/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/trustedadvisor/)
- [AWS CloudTrail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html)
### Related Videos
- [Delete CloudFormation stack but retain some resources](https://www.youtube.com/watch?v=bVmsS8rjuwk)
- [Find out which user launched Amazon EC2 instance](https://www.youtube.com/watch?v=SlyAHc5Mv2A)
### Related Examples
- [Delete or terminate Amazon EC2 resources](https://aws.amazon.com/premiumsupport/knowledge-center/delete-terminate-ec2/)
- [Find out which user launched an Amazon EC2 instance](https://aws.amazon.com/premiumsupport/knowledge-center/ec2-user-launched-instance/)
