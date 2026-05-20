---
id: "REL11-BP02"
title: "Fail over to healthy resources"
framework: "WAF"
domain: "Reliability"
capability: "How do you design your workload to withstand component failures?"
risk_level: "High"
---

# REL11-BP02 Fail over to healthy resources

## Desired Outcome
Systems are capable of automatically or manually using new resources to recover from degradation.

## Anti-Patterns
- Planning for failure is not part of the planning and design phase.
- RTO and RPO are not established.
- Insufficient monitoring to detect failing resources.
- Proper isolation of failure domains.
- Multi-Region fail over is not considered.
- Detection for failure is too sensitive or aggressive when deciding to failover.
- Not testing or validating failover design.
- Performing auto healing automation, but not notifying that healing was needed.
- Lack of dampening period to avoid failing back too soon.

## Implementation Guidance
 AWS services, such as [Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-subnets.html) and [Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/auto-scaling-groups.html), help distribute load across resources and Availability Zones. Therefore, failure of an individual resource (such as an EC2 instance) or impairment of an Availability Zone can be mitigated by shifting traffic to remaining healthy resources.

 For multi-Region workloads, designs are more complicated. For example, cross-Region read replicas allow you to deploy your data to multiple AWS Regions. However, failover is still required to promote the read replica to primary and then point your traffic to the new endpoint. Amazon Route 53, [Amazon Application Recovery Controller (ARC)](https://aws.amazon.com/application-recovery-controller/), Amazon CloudFront, and AWS Global Accelerator can help route traffic across AWS Regions.

 AWS services, such as Amazon S3, Lambda, API Gateway, Amazon SQS, Amazon SNS, Amazon SES, Amazon Pinpoint, Amazon ECR, AWS Certificate Manager, EventBridge, or Amazon DynamoDB, are automatically deployed to multiple Availability Zones by AWS. In case of failure, these AWS services automatically route traffic to healthy locations. Data is redundantly stored in multiple Availability Zones and remains available.

 For Amazon RDS, Amazon Aurora, Amazon Redshift, Amazon EKS, or Amazon ECS, Multi-AZ is a configuration option. AWS can direct traffic to the healthy instance if failover is initiated. This failover action may be taken by AWS or as required by the customer

 For Amazon EC2 instances, Amazon Redshift, Amazon ECS tasks, or Amazon EKS pods, you choose which Availability Zones to deploy to. For some designs, Elastic Load Balancing provides the solution to detect instances in unhealthy zones and route traffic to the healthy ones. Elastic Load Balancing can also route traffic to components in your on-premises data center.

 For Multi-Region traffic failover, rerouting can leverage Amazon Route 53, Amazon Application Recovery Controller, AWS Global Accelerator, Route 53 Private DNS for VPCs, or CloudFront to provide a way to define internet domains and assign routing policies, including health checks, to route traffic to healthy Regions. AWS Global Accelerator provides static IP addresses that act as a fixed entry point to your application, then route to endpoints in AWS Regions of your choosing, using the AWS global network instead of the internet for better performance and reliability.

## Implementation Steps
- Create failover designs for all appropriate applications and services. Isolate each architecture component and create failover designs meeting RTO and RPO for each component.
- Configure lower environments (like development or test) with all services that are required to have a failover plan. Deploy the solutions using infrastructure as code (IaC) to ensure repeatability.
- Configure a recovery site such as a second Region to implement and test the failover designs. If necessary, resources for testing can be configured temporarily to limit additional costs.
- Determine which failover plans are automated by AWS, which can be automated by a DevOps process, and which might be manual. Document and measure each service's RTO and RPO.
- Create a failover playbook and include all steps to failover each resource, application, and service.
- Create a failback playbook and include all steps to failback (with timing) each resource, application, and service
- Create a plan to initiate and rehearse the playbook. Use simulations and chaos testing to test the playbook steps and automation.
- For location impairment (such as Availability Zone or AWS Region), ensure you have systems in place to fail over to healthy resources in unimpaired locations. Check quota, autoscaling levels, and resources running before failover testing.

## Resources
### Related Best Practices
- [REL13- Plan for DR](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/plan-for-disaster-recovery-dr.html)
- [REL10 - Use fault isolation to protect your workload](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/use-fault-isolation-to-protect-your-workload.html)
### Related Documents
- [Setting RTO and RPO Targets](https://aws.amazon.com/blogs/mt/establishing-rpo-and-rto-targets-for-cloud-applications/)
- [Failover using Route 53 Weighted routing](https://aws.amazon.com/blogs/networking-and-content-delivery/building-highly-resilient-applications-using-amazon-route-53-application-recovery-controller-part-2-multi-region-stack)
- [Disaster Recovery with Amazon Application Recovery Controller](https://catalog.us-east-1.prod.workshops.aws/workshops/4d9ab448-5083-4db7-bee8-85b58cd53158/en-US/)
- [EC2 with autoscaling](https://github.com/adriaanbd/aws-asg-ecs-starter)
- [EC2 Deployments - Multi-AZ](https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html)
- [ECS Deployments - Multi-AZ](https://github.com/aws-samples/ecs-refarch-cloudformation)
- [Switch traffic using Amazon Application Recovery Controller](https://docs.aws.amazon.com/r53recovery/latest/dg/routing-control.failover-different-accounts.html)
- [Lambda with an Application Load Balancer and Failover](https://docs.aws.amazon.com/lambda/latest/dg/services-alb.html)
- [ACM Replication and Failover](https://github.com/aws-samples/amazon-ecr-cross-region-replication)
- [Parameter Store Replication and Failover](https://medium.com/devops-techable/how-to-design-an-ssm-parameter-store-for-multi-region-replication-support-aws-infrastructure-db7388be454d)
- [ECR cross region replication and Failover](https://docs.aws.amazon.com/AmazonECR/latest/userguide/registry-settings-configure.html)
- [Secrets manager cross region replication configuration](https://disaster-recovery.workshop.aws/en/labs/basics/secrets-manager.html)
- [Enable cross region replication for EFS and Failover](https://aws.amazon.com/blogs/aws/new-replication-for-amazon-elastic-file-system-efs/)
- [EFS Cross Region Replication and Failover](https://aws.amazon.com/blogs/storage/transferring-file-data-across-aws-regions-and-accounts-using-aws-datasync/)
- [Networking Failover](https://docs.aws.amazon.com/whitepapers/latest/hybrid-connectivity/aws-dx-dxgw-with-vgw-multi-regions-and-aws-public-peering.html)
- [S3 Endpoint failover using MRAP](https://catalog.workshops.aws/s3multiregionaccesspoints/en-US/0-setup/1-review-mrap)
- [Create cross region replication for S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html)
- [Guidance for Cross Region Failover and Graceful Failback on AWS](https://d1.awsstatic.com/solutions/guidance/architecture-diagrams/cross-region-failover-and-graceful-failback-on-aws.pdf)
- [Failover using multi-region global accelerator](https://aws.amazon.com/blogs/networking-and-content-delivery/deploying-multi-region-applications-in-aws-using-aws-global-accelerator/)
- [Failover with DRS](https://docs.aws.amazon.com/drs/latest/userguide/failback-overview.html)
### Related Examples
- [Disaster Recovery on AWS](https://disaster-recovery.workshop.aws/en/)
- [Elastic Disaster Recovery on AWS](https://catalog.us-east-1.prod.workshops.aws/workshops/080af3a5-623d-4147-934d-c8d17daba346/en-US)
