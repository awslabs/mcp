---
id: "REL11-BP03"
title: "Automate healing on all layers"
framework: "WAF"
domain: "Reliability"
capability: "How do you design your workload to withstand component failures?"
risk_level: "High"
---

# REL11-BP03 Automate healing on all layers

## Desired Outcome
Automated actions are performed to remediate detection of a failure.

## Anti-Patterns
- Provisioning resources without autoscaling.
- Deploying applications in instances or containers individually.
- Deploying applications that cannot be deployed into multiple locations without using automatic recovery.
- Manually healing applications that automatic scaling and automatic recovery fail to heal.
- No automation to failover databases.
- Lack automated methods to reroute traffic to new endpoints.
- No storage replication.

## Implementation Guidance
 Designs for Amazon EKS or other Kubernetes services should include both minimum and maximum replica or stateful sets and the minimum cluster and node group sizing. These mechanisms provide a minimum amount of continually-available processing resources while automatically remediating any failures using the Kubernetes control plane.

 Design patterns that are accessed through a load balancer using compute clusters should leverage Auto Scaling groups. Elastic Load Balancing (ELB) automatically distributes incoming application traffic across multiple targets and virtual appliances in one or more Availability Zones (AZs).

 Clustered compute-based designs that do not use load balancing should have their size designed for loss of at least one node. This will allow for the service to maintain itself running in potentially reduced capacity while it's recovering a new node. Example services are Mongo, DynamoDB Accelerator, Amazon Redshift, Amazon EMR, Cassandra, Kafka, MSK-EC2, Couchbase, ELK, and Amazon OpenSearch Service. Many of these services can be designed with additional auto healing features. Some cluster technologies must generate an alert upon the loss a node triggering an automated or manual workflow to recreate a new node. This workflow can be automated using AWS Systems Manager to remediate issues quickly.

 Amazon EventBridge can be used to monitor and filter for events such as CloudWatch alarms or changes in state in other AWS services. Based on event information, it can then invoke AWS Lambda, Systems Manager Automation, or other targets to run custom remediation logic on your workload. Amazon EC2 Auto Scaling can be configured to check for EC2 instance health. If the instance is in any state other than running, or if the system status is impaired, Amazon EC2 Auto Scaling considers the instance to be unhealthy and launches a replacement instance. For large-scale replacements (such as the loss of an entire Availability Zone), static stability is preferred for high availability.

## Implementation Steps
- Use Auto Scaling groups to deploy tiers in a workload. [Auto Scaling](https://docs.aws.amazon.com/autoscaling/plans/userguide/how-it-works.html) can perform self-healing on stateless applications and add or remove capacity.
- For compute instances noted previously, use [load balancing](https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-load-balancer.html) and choose the appropriate type of load balancer.
- Consider healing for Amazon RDS. With standby instances, configure for [auto failover](https://repost.aws/questions/QU4DYhqh2yQGGmjE_x0ylBYg/what-happens-after-failover-in-rds) to the standby instance. For Amazon RDS Read Replica, automated workflow is required to make a read replica primary.
- Implement [automatic recovery on EC2 instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-recover.html) that have applications deployed that cannot be deployed in multiple locations, and can tolerate rebooting upon failures. Automatic recovery can be used to replace failed hardware and restart the instance when the application is not capable of being deployed in multiple locations. The instance metadata and associated IP addresses are kept, as well as the [EBS volumes](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AmazonEBS.html) and mount points to [Amazon Elastic File System](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AmazonEFS.html) or [File Systems for Lustre](https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html) and [Windows](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/what-is.html). Using [AWS OpsWorks](https://docs.aws.amazon.com/opsworks/latest/userguide/workinginstances-autohealing.html), you can configure automatic healing of EC2 instances at the layer level.
- Implement automated recovery using [AWS Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html) and [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html) when you cannot use automatic scaling or automatic recovery, or when automatic recovery fails. When you cannot use automatic scaling, and either cannot use automatic recovery or automatic recovery fails, you can automate the healing using AWS Step Functions and AWS Lambda.
- [Amazon EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/what-is-amazon-eventbridge.html) can be used to monitor and filter for events such as [CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html) or changes in state in other AWS services. Based on event information, it can then invoke AWS Lambda (or other targets) to run custom remediation logic on your workload.

## Resources
### Related Best Practices
- [Availability Definition](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/availability.html)
- [REL11-BP01 Monitor all components of the workload to detect failures](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_notifications_sent_system.html)
### Related Documents
- [How AWS Auto Scaling Works](https://docs.aws.amazon.com/autoscaling/plans/userguide/how-it-works.html)
- [Amazon EC2 Automatic Recovery](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-recover.html)
- [Amazon Elastic Block Store (Amazon EBS)](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AmazonEBS.html)
- [Amazon Elastic File System (Amazon EFS)](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AmazonEFS.html)
- [What is Amazon FSx for Lustre?](https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html)
- [What is Amazon FSx for Windows File Server?](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/what-is.html)
- [AWS OpsWorks: Using Auto Healing to Replace Failed Instances](https://docs.aws.amazon.com/opsworks/latest/userguide/workinginstances-autohealing.html)
- [What is AWS Step Functions?](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
- [What is AWS Lambda?](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [What Is Amazon EventBridge?](https://docs.aws.amazon.com/eventbridge/latest/userguide/what-is-amazon-eventbridge.html)
- [Using Amazon CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [Amazon RDS Failover](https://d1.awsstatic.com/rdsImages/IG1_RDS1_AvailabilityDurability_Final.pdf)
- [SSM - Systems Manager Automation](https://docs.aws.amazon.com/resilience-hub/latest/userguide/integrate-ssm.html)
- [Resilient Architecture Best Practices](https://aws.amazon.com/blogs/architecture/understand-resiliency-patterns-and-trade-offs-to-architect-efficiently-in-the-cloud/)
### Related Videos
- [Automatically Provision and Scale OpenSearch Service](https://www.youtube.com/watch?v=GPQKetORzmE)
- [Amazon RDS Failover Automatically](https://www.youtube.com/watch?v=Mu7fgHOzOn0)
### Related Examples
- [Amazon RDS Failover Workshop](https://catalog.workshops.aws/resilient-apps/en-US/rds-multi-availability-zone/failover-db-instance)
### Related Tools
- [CloudWatch](https://aws.amazon.com/cloudwatch/)
- [CloudWatch X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/security-logging-monitoring.html)
