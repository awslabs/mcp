---
id: "REL11-BP04"
title: "Rely on the data plane and not the control plane during recovery"
framework: "WAF"
domain: "Reliability"
capability: "How do you design your workload to withstand component failures?"
risk_level: "Medium"
---

# REL11-BP04 Rely on the data plane and not the control plane during recovery

## Desired Outcome
When a resource enters an impaired state, the system is capable of automatically or manually recovering by shifting traffic from impaired to healthy resources.

## Anti-Patterns
- Dependence on changing DNS records to re-route traffic.
- Dependence on control-plane scaling operations to replace impaired components due to insufficiently provisioned resources.
- Relying on extensive, multi service, multi-API control plane actions to remediate any category of impairment.

## Implementation Guidance
 To limit data plane actions, assess each service for what actions are required to restore service.

 Leverage Amazon Application Recovery Controller to shift the DNS traffic. These features continually monitor your application’s ability to recover from failures and allow you to control your application recovery across multiple AWS Regions, Availability Zones, and on premises.

 Route 53 routing policies use the control plane, so do not rely on it for recovery. The Route 53 data planes answer DNS queries and perform and evaluate health checks. They are globally distributed and designed for a [100% availability service level agreement (SLA)](https://aws.amazon.com/route53/sla/).

 The Route 53 management APIs and consoles where you create, update, and delete Route 53 resources run on control planes that are designed to prioritize the strong consistency and durability that you need when managing DNS. To achieve this, the control planes are located in a single Region: US East (N. Virginia). While both systems are built to be very reliable, the control planes are not included in the SLA. There could be rare events in which the data plane’s resilient design allows it to maintain availability while the control planes do not. For disaster recovery and failover mechanisms, use data plane functions to provide the best possible reliability.

 Design your compute infrastructure to be statically stable to avoid using the control plane during an incident. For example, if you are using Amazon EC2 instances, avoid provisioning new instances manually or instructing Auto Scaling Groups to add instances in response. For the highest levels of resilience, provision sufficient capacity in the cluster used for failover. If this capacity threshold must be limited, set throttles on the overall end-to-end system to safely limit the total traffic reaching the limited set of resources.

 For services like Amazon DynamoDB, Amazon API Gateway, load balancers, and AWS Lambda serverless, using those services leverages the data plane. However, creating new functions, load balancers, API gateways, or DynamoDB tables is a control plane action and should be completed before the degradation as preparation for an event and rehearsal of failover actions. For Amazon RDS, data plane actions allow for access to data.

 For more information about data planes, control planes, and how AWS builds services to meet high availability targets, see [Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/).

 Understand which operations are on the data plane and which are on the control plane.

## Implementation Steps
 For each workload that needs to be restored after a degradation event, evaluate the failover runbook, high availability design, auto healing design, or HA resource restoration plan. Identity each action that might be considered a control plane action.

 Consider changing the control action to a data plane action:
- Auto Scaling (control plane) to pre-scaled Amazon EC2 resources (data plane)
- Amazon EC2 instance scaling (control plane) to AWS Lambda scaling (data plane)
- Assess any designs using Kubernetes and the nature of the control plane actions. Adding pods is a data plane action in Kubernetes. Actions should be limited to adding pods and not adding nodes. Using [over-provisioned nodes](https://www.eksworkshop.com/docs/autoscaling/compute/cluster-autoscaler/overprovisioning/) is the preferred method to limit control plane actions

 Consider alternate approaches that allow for data plane actions to affect the same remediation.
- Route 53 Record change (control plane) or Amazon Application Recovery Controller (data plane)
- [ Route 53 Health checks for more automated updates ](https://aws.amazon.com/blogs/networking-and-content-delivery/creating-disaster-recovery-mechanisms-using-amazon-route-53/)

 Consider some services in a secondary Region, if the service is mission critical, to allow for more control plane and data plane actions in an unaffected Region.
- Amazon EC2 Auto Scaling or Amazon EKS in a primary Region compared to Amazon EC2 Auto Scaling or Amazon EKS in a secondary Region and routing traffic to secondary Region (control plane action)
- Make read replica in secondary primary or attempting same action in primary Region (control plane action)

## Resources
### Related Best Practices
- [Availability Definition](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/availability.html)
- [REL11-BP01 Monitor all components of the workload to detect failures](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_notifications_sent_system.html)
### Related Documents
- [APN Partner: partners that can help with automation of your fault tolerance](https://aws.amazon.com/partners/find/results/?keyword=automation)
- [AWS Marketplace: products that can be used for fault tolerance](https://aws.amazon.com/marketplace/search/results?searchTerms=fault+tolerance)
- [Amazon Builders' Library: Avoiding overload in distributed systems by putting the smaller service in control](https://aws.amazon.com/builders-library/avoiding-overload-in-distributed-systems-by-putting-the-smaller-service-in-control/)
- [Amazon DynamoDB API (control plane and data plane)](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.API.html)
- [AWS Lambda Executions](https://docs.aws.amazon.com/whitepapers/latest/security-overview-aws-lambda/lambda-executions.html) (split into the control plane and the data plane)
- [AWS Elemental MediaStore Data Plane](https://docs.aws.amazon.com/mediastore/latest/apireference/API_Operations_AWS_Elemental_MediaStore_Data_Plane.html)
- [Building highly resilient applications using Amazon Application Recovery Controller, Part 1: Single-Region stack](https://aws.amazon.com/blogs/networking-and-content-delivery/building-highly-resilient-applications-using-amazon-route-53-application-recovery-controller-part-1-single-region-stack/)
- [Building highly resilient applications using Amazon Application Recovery Controller, Part 2: Multi-Region stack](https://aws.amazon.com/blogs/networking-and-content-delivery/building-highly-resilient-applications-using-amazon-route-53-application-recovery-controller-part-2-multi-region-stack/)
- [Creating Disaster Recovery Mechanisms Using Amazon Route 53](https://aws.amazon.com/blogs/networking-and-content-delivery/creating-disaster-recovery-mechanisms-using-amazon-route-53/)
- [What is Amazon Application Recovery Controller](https://docs.aws.amazon.com/r53recovery/latest/dg/what-is-route53-recovery.html)
- [ Kubernetes Control Plane and data plane ](https://aws.amazon.com/blogs/containers/managing-kubernetes-control-plane-events-in-amazon-eks/)
### Related Videos
- [ Back to Basics - Using Static Stability ](https://www.youtube.com/watch?v=gy1RITZ7N7s)
- [ Building resilient multi-site workloads using AWS global services ](https://www.youtube.com/watch?v=62ZQHTruBnk)
### Related Examples
- [Introducing Amazon Application Recovery Controller](https://aws.amazon.com/blogs/aws/amazon-route-53-application-recovery-controller/)
- [ Amazon Builders' Library: Avoiding overload in distributed systems by putting the smaller service in control ](https://aws.amazon.com/builders-library/avoiding-overload-in-distributed-systems-by-putting-the-smaller-service-in-control/)
- [ Building highly resilient applications using Amazon Application Recovery Controller, Part 1: Single-Region stack ](https://aws.amazon.com/blogs/networking-and-content-delivery/building-highly-resilient-applications-using-amazon-route-53-application-recovery-controller-part-1-single-region-stack/)
- [ Building highly resilient applications using Amazon Application Recovery Controller, Part 2: Multi-Region stack ](https://aws.amazon.com/blogs/networking-and-content-delivery/building-highly-resilient-applications-using-amazon-route-53-application-recovery-controller-part-2-multi-region-stack/)
- [ Static stability using Availability Zones ](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)
### Related Tools
- [ Amazon CloudWatch ](https://aws.amazon.com/cloudwatch/)
- [AWS X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/security-logging-monitoring.html)
