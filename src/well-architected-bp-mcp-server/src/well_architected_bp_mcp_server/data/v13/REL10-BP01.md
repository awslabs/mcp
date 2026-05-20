---
id: "REL10-BP01"
title: "Deploy the workload to multiple locations"
framework: "WAF"
domain: "Reliability"
capability: "How do you use fault isolation to protect your workload?"
risk_level: "High"
---

# REL10-BP01 Deploy the workload to multiple locations

## Desired Outcome
Production workloads are distributed among multiple Availability Zones (AZs) or Regions to achieve fault tolerance and high availability.

## Anti-Patterns
- Your production workload exists only in a single Availability Zone.
- You implement a multi-Region architecture when a multi-AZ architecture would satisfy business requirements.
- Your deployments or data become desynchronized, which results in configuration drift or under-replicated data.
- You don't account for dependencies between application components if resilience and multi-location requirements differ between those components.

## Implementation Guidance
 Deploy and operate all production workloads in at least two Availability Zones (AZs) in a Region.

 **Using multiple Availability Zones**

 Availability Zones are resource hosting locations that are physically separated from each other to avoid correlated failures due to risks such as fires, floods, and tornadoes. Each Availability Zone has independent physical infrastructure, including utility power connections, backup power sources, mechanical services, and network connectivity. This arrangement limits faults in any of these components to just the impacted Availability Zone. For example, if an AZ-wide incident makes EC2 instances unavailable in the affected Availability Zone, your instances in other Availability Zone remains available.

 Despite being physically separated, Availability Zones in the same AWS Region are close enough to provide high-throughput, low-latency (single-digit millisecond) networking. You can replicate data synchronously between Availability Zones for most workloads without significantly impacting user experience. This means you can use Availability Zones in a Region in an active/active or active/standby configuration.

 All compute associated with your workload should be distributed among multiple Availability Zones. This includes [Amazon EC2](https://aws.amazon.com/ec2/) instances, [AWS Fargate](https://aws.amazon.com/fargate/) tasks, and VPC-attached [AWS Lambda](https://aws.amazon.com/lambda/) functions. AWS compute services, including [EC2 Auto Scaling](https://aws.amazon.com/ec2/autoscaling/), [Amazon Elastic Container Service (ECS)](https://aws.amazon.com/ecs/), and [Amazon Elastic Kubernetes Service (EKS)](https://aws.amazon.com/eks/), provide ways for you to launch and manage compute across Availability Zones. Configure them to automatically replace compute as needed in a different Availability Zone to maintain availability. To direct traffic to available Availability Zones, place a load balancer in front of your compute, such as an Application Load Balancer or Network Load Balancer. AWS load balancers can reroute traffic to available instances in the event of an Availability Zone impairment.

 You should also replicate data for your workload and make it available in multiple Availability Zones. Some AWS managed data services, such as [Amazon S3](https://aws.amazon.com/s3/), [Amazon Elastic File Service (EFS)](https://aws.amazon.com/efs/), [Amazon Aurora](https://aws.amazon.com/aurora/), [Amazon DynamoDB](https://aws.amazon.com/dynamodb/), [Amazon Simple Queue Service (SQS)](https://aws.amazon.com/sqs/), and [Amazon Kinesis Data Streams](https://aws.amazon.com/kinesis/data-streams/) replicate data in multiple Availability Zones by default and are robust against Availability Zone impairment. With other AWS managed data services, such as [Amazon Relational Database Service (RDS)](https://aws.amazon.com/rds/), [Amazon Redshift](https://aws.amazon.com/redshift/), and [Amazon ElastiCache](https://aws.amazon.com/elasticache/), you must enable multi-AZ replication. Once enabled, these services automatically detect an Availability Zone impairment, redirect requests to an available Availability Zone, and re-replicate data as needed after recovery without customer intervention. Familiarize yourself with the user guide for each AWS managed data service you use to understand its multi-AZ capabilities, behaviors, and operations.

 If you are using self-managed storage, such as [Amazon Elastic Block Store (EBS)](https://aws.amazon.com/ebs/) volumes or Amazon EC2 instance storage, you must manage multi-AZ replication yourself.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/multi-tier-architecture.png)

 **Using multiple AWS Regions**

 If you have workloads that require extreme resilience (such as critical infrastructure, health-related applications, or services with stringent customer or mandated availability requirements), you may require additional availability beyond what a single AWS Region can provide. In this case, you should deploy and operate your workload across at least two AWS Regions (assuming that your data residency requirements allow it).

 AWS Regions are located in different geographical regions around the world and in multiple continents. AWS Regions have even greater physical separation and isolation than Availability Zones alone. AWS services, with few exceptions, take advantage of this design to operate fully independently between different Regions (also known as *Regional services*). A failure of an AWS Regional service is designed not to impact the service in a different Region.

 When you operate your workload in multiple Regions, you should consider additional requirements. Because resources in different Regions are separate from and independent of one another, you must duplicate your workload's components in each Region. This includes foundational infrastructure, such as VPCs, in addition to compute and data services.

 **NOTE:** When you consider a multi-Regional design, verify that your workload is capable of running in a single Region. If you create dependencies between Regions where a component in one Region relies on services or components in a different Region, you can increase the risk of failure and significantly weaken your reliability posture.

 To ease multi-Regional deployments and maintain consistency, [AWS CloudFormation StackSets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html) can replicate your entire AWS infrastructure across multiple Regions. [AWS CloudFormation](https://aws.amazon.com/cloudformation/) can also detect configuration drift and inform you when your AWS resources in a Region are out of sync. Many AWS services offer multi-region replication for important workload assets. For example, [EC2 Image Builder](https://aws.amazon.com/image-builder/) can publish your EC2 machine images (AMIs) after every build to each Region you use. [Amazon Elastic Container Registry (ECR)](https://aws.amazon.com/ecr/) can replicate your container images to your selected Regions.

 You must also replicate your data across each of your chosen Regions. Many AWS managed data services provide cross-Regional replication capability, including Amazon S3, Amazon DynamoDB, Amazon RDS, Amazon Aurora, Amazon Redshift, Amazon Elasticache, and Amazon EFS. [Amazon DynamoDB global tables](https://aws.amazon.com/dynamodb/global-tables/) accept writes in any supported Region and will replicate data among all your other configured Regions. With other services, you must designate a primary Region for writes, as other Regions contain read-only replicas. For each AWS-managed data service your workload uses, refer to its user guide and developer guide to understand its multi-Region capabilities and limitations. Pay special attention to where writes must be directed, transactional capabilities and limitations, how replication is performed, and how to monitor synchronization between Regions.

 AWS also provides the ability to route request traffic to your Regional deployments with great flexibility. For example, you can configure your DNS records using [Amazon Route 53](https://aws.amazon.com/route53/) to direct traffic to the closest available Region to the user. Alternatively, you can configure your DNS records in an active/standby configuration, where you designate one Region as primary and fall back to a Regional replica only if the primary Region becomes unhealthy. You can configure [Route 53 health checks](https://docs.aws.amazon.com/Route 53/latest/DeveloperGuide/dns-failover.html) to detect unhealthy endpoints and perform automatic failover and additionally use [Amazon Application Recovery Controller (ARC)](https://aws.amazon.com/application-recovery-controller/) to provide a highly-available routing control for manually re-routing traffic as needed.

 Even if you choose not to operate in multiple Regions for high availability, consider multiple Regions as part of your disaster recovery (DR) strategy. If possible, replicate your workload's infrastructure components and data in a *warm standby* or *pilot light* configuration in a secondary Region. In this design, you replicate baseline infrastructure from the primary Region such as VPCs, Auto Scaling groups, container orchestrators, and other components, but you configure the variable-sized components in the standby Region (such as the number of EC2 instances and database replicas) to be a minimally-operable size. You also arrange for continuous data replication from the primary Region to the standby Region. If an incident occurs, you can then scale out, or grow, the resources in the standby Region, and then promote it to become the primary Region.

## Implementation Steps
1.  Work with business stakeholders and data residency experts to determine which AWS Regions can be used to host your resources and data.

1.  Work with business and technical stakeholders to evaluate your workload, and determine whether its resilience needs can be met by a multi-AZ approach (single AWS Region) or if they require a multi-Region approach (if multiple Regions are permitted). The use of multiple Regions can achieve greater availability but can involve additional complexity and cost. Consider the following factors in your evaluation:

   1.  **Business objectives and customer requirements**: How much downtime is permitted should a workload-impacting incident occur in an Availability Zone or a Region? Evaluate your recovery point objectives as discussed in [REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html).

   1.  **Disaster recovery (DR) requirements**: What kind of potential disaster do you want to insure yourself against? Consider the possibility of data loss or long-term unavailability at different scopes of impact from a single Availability Zone to an entire Region. If you replicate data and resources across Availability Zones, and a single Availability Zone experiences a sustained failure, you can recover service in another Availability Zone. If you replicate data and resources across Regions, you can recover service in another Region.

1.  Deploy your compute resources into multiple Availability Zones.

   1.  In your VPC, create multiple subnets in different Availability Zones. Configure each to be large enough to accommodate the resources needed to serve the workload, even during an incident. For more detail, see [REL02-BP03 Ensure IP subnet allocation accounts for expansion and availability](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology_ip_subnet_allocation.html).

   1.  If you are using Amazon EC2 instances, use [EC2 Auto Scaling](https://aws.amazon.com/ec2/autoscaling/) to manage your instances. Specify the subnets you chose in the previous step when you create your Auto Scaling groups.

   1.  If you are using AWS Fargate compute for [Amazon ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) or [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html), select the subnets you chose in the first step when you create an ECS Service, launch an ECS task, or create a [Fargate profile](https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html) for EKS.

   1.  If you are using AWS Lambda functions that need to run in your VPC, select the subnets you chose in the first step when you create the Lambda function. For any functions that do not have a VPC configuration, AWS Lambda manages availability for you automatically.

   1.  Place traffic directors such as load balancers in front of your compute resources. If cross-zone load balancing is enabled, [AWS Application Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html) and [Network Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/introduction.html) detect when targets such as EC2 instances and containers are unreachable due to Availability Zone impairment and reroute traffic towards targets in healthy Availability Zones. If you disable cross-zone load balancing, use Amazon Application Recovery Controller (ARC) to provide zonal shift capability. If you are using a third-party load balancer or have implemented your own load balancers, configure them with multiple front ends across different Availability Zones.

1.  Replicate your workload's data across multiple Availability Zones.

   1.  If you use an AWS-managed data service such as Amazon RDS, Amazon ElastiCache, or Amazon FSx, study its user guide to understand its data replication and resilience capabilities. Enable cross-AZ replication and failover if necessary.

   1.  If you use AWS-managed storage services such as Amazon S3, Amazon EFS, and Amazon FSx, avoid using single-AZ or One Zone configurations for data that requires high durability. Use a multi-AZ configuration for these services. Check the respective service's user guide to determine whether multi-AZ replication is enabled by default or whether you must enable it.

   1.  If you run a self-managed database, queue, or other storage service, arrange for multi-AZ replication according to the application's instructions or best practices. Familiarize yourself with the failover procedures for your application.

1.  Configure your DNS service to detect AZ impairment and reroute traffic to a healthy Availability Zone. Amazon Route 53, when used in combination with Elastic Load Balancers, can do this automatically. Route 53 can also be configured with failover records that use health checks to respond to queries with only healthy IP addresses. For any DNS records used for failover, specify a short time to live (TTL) value (for example, 60 seconds or less) to help prevent record caching from impeding recovery (Route 53 alias records supply appropriate TTLs for you).

 **Additional steps when using multiple AWS Regions**

1.  Replicate all operating system (OS) and application code used by your workload across your selected Regions. Replicate Amazon Machine Images (AMIs) used by your EC2 instances if necessary using solutions such as Amazon EC2 Image Builder. Replicate container images stored in registries using solutions such as Amazon ECR cross-Region replication. Enable Regional replication for any Amazon S3 buckets used for storing application resources.

1.  Deploy your compute resources and configuration metadata (such as parameters stored in AWS Systems Manager Parameter Store) into multiple Regions. Use the same procedures described in previous steps, but replicate the configuration for each Region you are using for your workload. Use infrastructure as code solutions such as AWS CloudFormation to uniformly reproduce the configurations among Regions. If you are using a secondary Region in a pilot light configuration for disaster recovery, you may reduce the number of your compute resources to a minimum value to save cost, with a corresponding increase in time to recovery.

1.  Replicate your data from your primary Region into your secondary Regions.

   1.  Amazon DynamoDB global tables provide global replicas of your data that can be written to from any supported Region. With other AWS-managed data services, such as Amazon RDS, Amazon Aurora, and Amazon Elasticache, you designate a primary (read/write) Region and replica (read-only) Regions. Consult the respective services' user and developer guides for details on Regional replication.

   1.  If you are running a self-managed database, arrange for multi-Region replication according to the application's instructions or best practices. Familiarize yourself with the failover procedures for your application.

   1.  If your workload uses AWS EventBridge, you may need to forward selected events from your primary Region to your secondary Regions. To do so, specify event buses in your secondary Regions as targets for matched events in your primary Region.

1.  Consider whether and to what extent you want to use identical encryption keys across Regions. A typical approach that balances security and ease of use is to use Region-scoped keys for Region-local data and authentication, and use globally-scoped keys for encryption of data that is replicated among different Regions. [AWS Key Management Service (KMS)](https://aws.amazon.com/kms/) supports [multi-region keys](https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.html) to securely distribute and protect keys shared across Regions.

1.  Consider AWS Global Accelerator to improve the availability of your application by directing traffic to Regions that contain healthy endpoints.

## Resources
### Related Best Practices
- [REL02-BP03 Ensure IP subnet allocation accounts for expansion and availability](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology_ip_subnet_allocation.html)
- [REL11-BP05 Use static stability to prevent bimodal behavior](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_static_stability.html)
- [REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)
### Related Documents
- [AWS Global Infrastructure](https://aws.amazon.com/about-aws/global-infrastructure)
- [White paper: AWS Fault Isolation Boundaries](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/availability-zones.html)
- [Resilience in Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/disaster-recovery-resiliency.html)
- [Amazon EC2 Auto Scaling: Example: Distribute instances across Availability Zones](https://docs.aws.amazon.com/autoscaling/ec2/userguide/auto-scaling-benefits.html#arch-AutoScalingMultiAZ)
- [How EC2 Image Builder works](https://docs.aws.amazon.com/imagebuilder/latest/userguide/how-image-builder-works.html#image-builder-distribution)
- [How Amazon ECS places tasks on container instances (includes Fargate)](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-placement.html)
- [Resilience in AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/security-resilience.html)
- [Amazon S3: Replicating objects overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html)
- [Private image replication in Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/replication.html)
- [Global Tables: Multi-Region Replication with DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)
- [Amazon Elasticache for Redis OSS: Replication across AWS Regions using global datastores](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Redis-Global-Datastore.html)
- [Resilience in Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/disaster-recovery-resiliency.html)
- [Using Amazon Aurora global databases](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)
- [AWS Global Accelerator Developer Guide](https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html)
- [Multi-Region keys in AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.html)
- [Amazon Route 53: Configuring DNS failover](https://docs.aws.amazon.com/Route 53/latest/DeveloperGuide/dns-failover-configuring.html)
- [Amazon Application Recovery Controller (ARC) Developer Guide](https://docs.aws.amazon.com/r53recovery/latest/dg/what-is-route53-recovery.html)
- [Sending and receiving Amazon EventBridge events between AWS Regions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cross-region.html)
- [Creating a Multi-Region Application with AWS Services blog series](https://aws.amazon.com/blogs/architecture/tag/creating-a-multi-region-application-with-aws-services-series/)
- [Disaster Recovery (DR) Architecture on AWS, Part I: Strategies for Recovery in the Cloud](https://aws.amazon.com/blogs/architecture/disaster-recovery-dr-architecture-on-aws-part-i-strategies-for-recovery-in-the-cloud/)
- [Disaster Recovery (DR) Architecture on AWS, Part III: Pilot Light and Warm Standby](https://aws.amazon.com/blogs/architecture/disaster-recovery-dr-architecture-on-aws-part-iii-pilot-light-and-warm-standby/)
### Related Videos
- [AWS re:Invent 2018: Architecture Patterns for Multi-Region Active-Active Applications](https://youtu.be/2e29I3dA8o4)
- [AWS re:Invent 2019: Innovation and operation of the AWS global network infrastructure](https://youtu.be/UObQZ3R9_4c)
