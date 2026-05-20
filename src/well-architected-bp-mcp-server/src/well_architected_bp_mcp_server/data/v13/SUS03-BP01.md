---
id: "SUS03-BP01"
title: "Optimize software and architecture for asynchronous and scheduled jobs"
framework: "WAF"
domain: "Sustainability"
capability: "How do you take advantage of software and architecture patterns to support your sustainability goals?"
risk_level: "Medium"
---

# SUS03-BP01 Optimize software and architecture for asynchronous and scheduled jobs

## Anti-Patterns
- You overprovision the resources in your cloud workload to meet unforeseen spikes in demand.
- Your architecture does not decouple senders and receivers of asynchronous messages by a messaging component.

## Implementation Guidance
 Use efficient architecture patterns such as [event-driven architecture](https://aws.amazon.com/event-driven-architecture/) that result in even utilization of components and minimize overprovisioning in your workload. Using efficient architecture patterns minimizes idle resources from lack of use due to changes in demand over time.

 Understand the requirements of your workload components and adopt architecture patterns that increase overall utilization of resources. Retire components that are no longer required.

## Implementation Steps
- Analyze the demand for your workload to determine how to respond to those.
- For requests or jobs that don’t require synchronous responses, use queue-driven architectures and auto scaling workers to maximize utilization. Here are some examples of when you might consider queue-driven architecture:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_software_a2.html)
- For requests or jobs that can be processed anytime, use scheduling mechanisms to process jobs in batch for more efficiency. Here are some examples of scheduling mechanisms on AWS:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_software_a2.html)
- If you use polling and webhooks mechanisms in your architecture, replace those with events. Use [event-driven architectures](https://docs.aws.amazon.com/lambda/latest/operatorguide/event-driven-architectures.html) to build highly efficient workloads.
- Leverage [serverless on AWS](https://aws.amazon.com/serverless/) to eliminate over-provisioned infrastructure.
- Right size individual components of your architecture to prevent idling resources waiting for input.
  - You can use the [Rightsizing Recommendations in AWS Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-rightsizing.html) or [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/) to identify rightsizing opportunities.
  - For more detail, see [Right Sizing: Provisioning Instances to Match Workloads](https://docs.aws.amazon.com/whitepapers/latest/cost-optimization-right-sizing/cost-optimization-right-sizing.html).

## Resources
### Related Documents
- [What is Amazon Simple Queue Service?](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html)
- [What is Amazon MQ?](https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/welcome.html)
- [Scaling based on Amazon SQS](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-using-sqs-queue.html)
- [What is AWS Step Functions?](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
- [What is AWS Lambda?](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [Using AWS Lambda with Amazon SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [What is Amazon EventBridge?](https://docs.aws.amazon.com/eventbridge/latest/userguide/what-is-amazon-eventbridge.html)
- [ Managing Asynchronous Workflows with a REST API ](https://aws.amazon.com/blogs/architecture/managing-asynchronous-workflows-with-a-rest-api/)
### Related Videos
- [AWS re:Invent 2023 - Navigating the journey to serverless event-driven architecture ](https://www.youtube.com/watch?v=hvGuqHp051c)
- [AWS re:Invent 2023 - Using serverless for event-driven architecture & domain-driven design ](https://www.youtube.com/watch?v=3foMZJSPMI4)
- [AWS re:Invent 2023 - Advanced event-driven patterns with Amazon EventBridge ](https://www.youtube.com/watch?v=6X4lSPkn4ps)
- [AWS re:Invent 2023 - Sustainable architecture: Past, present, and future ](https://www.youtube.com/watch?v=2xpUQ-Q4QcM)
- [ Asynchronous Message Patterns \$1 AWS Events ](https://www.youtube.com/watch?v=-yJqBuwouZ4)
### Related Examples
- [ Event-driven architecture with AWS Graviton Processors and Amazon EC2 Spot Instances ](https://catalog.workshops.aws/well-architected-sustainability/en-US/2-software-and-architecture/event-driven-architecture-with-graviton-spot)
