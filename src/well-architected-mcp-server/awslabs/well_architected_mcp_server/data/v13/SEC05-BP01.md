---
id: "SEC05-BP01"
title: "Create network layers"
framework: "WAF"
domain: "Security"
capability: "How do you protect your network resources?"
risk_level: "High"
---

# SEC05-BP01 Create network layers

## Desired Outcome
The layers of your network are part of an integral defense-in-depth approach to security that complements the identity authentication and authorization strategy of your workloads. Layers are in place according to data sensitivity and access requirements, with appropriate traffic flow and control mechanisms.

## Anti-Patterns
- You create all resources in a single VPC or subnet.
- You construct your network layers without consideration of data sensitivity requirements, component behaviors, or functionality.
- You use VPCs and subnets as defaults for all network layer considerations, and you don't consider how AWS managed services influence your topology.

## Implementation Guidance
 When designing a workload architecture, it is common to separate components into different layers based on their responsibility. For example, a web application can have a presentation layer, application layer, and data layer. You can take a similar approach when designing your network topology. Underlying network controls can help enforce your workload's data access requirements. For example, in a three-tier web application architecture, you can store your static presentation layer files on [Amazon S3](https://aws.amazon.com/s3/) and serve them from a content delivery network (CDN), such as [Amazon CloudFront](https://aws.amazon.com/cloudfront/). The application layer can have public endpoints that an [Application Load Balancer (ALB)](https://aws.amazon.com/elasticloadbalancing/application-load-balancer/) serves in an [Amazon VPC](https://aws.amazon.com/vpc/) public subnet (similar to a demilitarized zone, or DMZ), with back-end services deployed into private subnets. The data layer, that is hosting resources such as databases and shared file systems, can reside in different private subnets from the resources of your application layer. At each of these layer boundaries (CDN, public subnet, private subnet), you can deploy controls that allow only authorized traffic to traverse across those boundaries.

 Similar to modeling network layers based on the functional purpose of your workload's components, also consider the sensitivity of the data being processed. Using the web application example, while all of your workload services may reside within the application layer, different services may process data with different sensitivity levels. In this case, dividing the application layer using multiple private subnets, different VPCs in the same AWS account, or even different VPCs in different AWS accounts for each level of data sensitivity may be appropriate according to your control requirements.

 A further consideration for network layers is the behavior consistency of your workload's components. Continuing the example, in the application layer you may have services that accept inputs from end-users or external system integrations that are inherently riskier than the inputs to other services. Examples include file uploads, code scripts to run, email scanning and so on. Placing these services in their own network layer helps create a stronger isolation boundary around them, and can prevent their unique behavior from creating false positive alerts in inspection systems.

 As part of your design, consider how using AWS managed services influences your network topology. Explore how services such as [Amazon VPC Lattice](https://aws.amazon.com/vpc/lattice/) can help make the interoperability of your workload components across network layers easier. When using [AWS Lambda](https://aws.amazon.com/lambda/), deploy in your VPC subnets unless there are specific reasons not to. Determine where VPC endpoints and [AWS PrivateLink](https://aws.amazon.com/privatelink/) can simplify adhering to security policies that limit access to internet gateways.

## Implementation Steps
1.  Review your workload architecture. Logically group components and services based on the functions they serve, the sensitivity of data being processed, and their behavior.

1.  For components responding to requests from the internet, consider using load balancers or other proxies to provide public endpoints. Explore shifting security controls by using managed services, such as CloudFront, [Amazon API Gateway](https://aws.amazon.com/api-gateway/), Elastic Load Balancing, and [AWS Amplify](https://aws.amazon.com/amplify/) to host public endpoints.

1.  For components running in compute environments, such as Amazon EC2 instances, [AWS Fargate](https://aws.amazon.com/fargate/) containers, or Lambda functions, deploy these into private subnets based on your groups from the first step.

1.  For fully managed AWS services, such as [Amazon DynamoDB](https://aws.amazon.com/dynamodb/), [Amazon Kinesis](https://aws.amazon.com/kinesis/), or [Amazon SQS](https://aws.amazon.com/sqs/), consider using VPC endpoints as the default for access over private IP addresses.

## Resources
### Related Best Practices
- [REL02 Plan your network topology](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/plan-your-network-topology.html)
- [PERF04-BP01 Understand how networking impacts performance](https://docs.aws.amazon.com/wellarchitected/latest/framework/perf_networking_understand_how_networking_impacts_performance.html)
### Related Videos
- [AWS re:Invent 2023 - AWS networking foundations](https://www.youtube.com/watch?v=8nNurTFy-h4)
### Related Examples
- [VPC examples](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-examples-intro.html)
- [Access container applications privately on Amazon ECS by using AWS Fargate, AWS PrivateLink, and a Network Load Balancer](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/access-container-applications-privately-on-amazon-ecs-by-using-aws-fargate-aws-privatelink-and-a-network-load-balancer.html)
- [Serve static content in an Amazon S3 bucket through a VPC by using Amazon CloudFront](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/serve-static-content-in-an-amazon-s3-bucket-through-a-vpc-by-using-amazon-cloudfront.html)
