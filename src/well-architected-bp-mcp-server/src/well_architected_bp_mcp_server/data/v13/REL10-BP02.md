---
id: "REL10-BP02"
title: "Automate recovery for components constrained to a single location"
framework: "WAF"
domain: "Reliability"
capability: "How do you use fault isolation to protect your workload?"
risk_level: "Medium"
---

# REL10-BP02 Automate recovery for components constrained to a single location

## Implementation Guidance
 If the best practice to deploy the workload to multiple locations is not possible due to technological constraints, you must implement an alternate path to resiliency. You must automate the ability to recreate necessary infrastructure, redeploy applications, and recreate necessary data for these cases.

 For example, Amazon EMR launches all nodes for a given cluster in the same Availability Zone because running a cluster in the same zone improves performance of the jobs flows as it provides a higher data access rate. If this component is required for workload resilience, then you must have a way to redeploy the cluster and its data. Also for Amazon EMR, you should provision redundancy in ways other than using Multi-AZ. You can provision [multiple nodes](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-ha-launch.html). Using [EMR File System (EMRFS)](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-fs.html), data in EMR can be stored in Amazon S3, which in turn can be replicated across multiple Availability Zones or AWS Regions.

 Similarly, for Amazon Redshift, by default it provisions your cluster in a randomly selected Availability Zone within the AWS Region that you select. All the cluster nodes are provisioned in the same zone.

 For stateful server-based workloads deployed to an on-premise data center, you can use AWS Elastic Disaster Recovery to protect your workloads in AWS. If you are already hosted in AWS, you can use Elastic Disaster Recovery to protect your workload to an alternative Availability Zone or Region. Elastic Disaster Recovery uses continual block-level replication to a lightweight staging area to provide fast, reliable recovery of on-premises and cloud-based applications.

## Implementation Steps
1.  Implement self-healing. Deploy your instances or containers using automatic scaling when possible. If you cannot use automatic scaling, use automatic recovery for EC2 instances or implement self-healing automation based on Amazon EC2 or ECS container lifecycle events.
   - Use [Amazon EC2 Auto Scaling groups](https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html) for instances and container workloads that have no requirements for a single instance IP address, private IP address, Elastic IP address, and instance metadata.
     - The launch template user data can be used to implement automation that can self-heal most workloads.
   - Use automatic [recovery of Amazon EC2 instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-recover.html) for workloads that require a single instance ID address, private IP address, elastic IP address, and instance metadata.
     - Automatic Recovery will send recovery status alerts to a SNS topic as the instance failure is detected.
   - Use [Amazon EC2 instance lifecycle events](https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html) or [Amazon ECS events](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_cwe_events.html) to automate self-healing where automatic scaling or EC2 recovery cannot be used.
     - Use the events to invoke automation that will heal your component according to the process logic you require.
   - Protect stateful workloads that are limited to a single location using [AWS Elastic Disaster Recovery](https://docs.aws.amazon.com/drs/latest/userguide/what-is-drs.html).

## Resources
### Related Documents
- [Amazon ECS events](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_cwe_events.html)
- [Amazon EC2 Auto Scaling lifecycle hooks](https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html)
- [Recover your instance.](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-recover.html)
- [Service automatic scaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html)
- [What Is Amazon EC2 Auto Scaling?](https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html)
- [AWS Elastic Disaster Recovery](https://docs.aws.amazon.com/drs/latest/userguide/what-is-drs.html)
