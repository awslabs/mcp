---
id: "SUS03-BP01"
title: "Optimize software and architecture for asynchronous and scheduled jobs"
pillar: "Sustainability"
risk_level: "MEDIUM"
capability: "How do you take advantage of software and architecture patterns to support your sustainability goals?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_software_a2.html"
---

# SUS03-BP01 Optimize software and architecture for asynchronous and scheduled jobs

Use efficient software and architecture patterns such as queue-driven to
maintain consistent high utilization of deployed resources.

**Common anti-patterns:**

- You overprovision the resources in your cloud workload to meet unforeseen spikes in demand.
- Your architecture does not decouple senders and receivers of asynchronous messages by a messaging component.

**Benefits of establishing this best practice:**

- Efficient software and architecture patterns minimize the unused resources in your workload and improve the overall efficiency.
- You can scale the processing independently of the receiving of asynchronous messages.
- Through a messaging component, you have relaxed availability requirements that you can meet with fewer resources.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Use efficient architecture patterns such as [event-driven architecture](https://aws.amazon.com/event-driven-architecture/) that result in
even utilization of components and minimize overprovisioning in your workload. Using
efficient architecture patterns minimizes idle resources from lack of use due to changes
in demand over time.

Understand the requirements of your workload components and adopt architecture patterns
that increase overall utilization of resources. Retire components that are no longer required.

### Implementation steps

- Analyze the demand for your workload to determine how to respond to those.
- For requests or jobs that don’t require synchronous responses, use queue-driven
architectures and auto scaling workers to maximize utilization. Here are some
examples of when you might consider queue-driven architecture:

Queuing mechanism
Description

[AWS Batch job queues](https://docs.aws.amazon.com/batch/latest/userguide/job_queues.html)

AWS Batch jobs are submitted to a job queue where
they reside until they can be scheduled to run in a
compute environment.

[Amazon Simple Queue Service and Amazon EC2 Spot Instances](https://aws.amazon.com/blogs/compute/running-cost-effective-queue-workers-with-amazon-sqs-and-amazon-ec2-spot-instances/)

Pairing Amazon SQS and Spot Instances to build fault tolerant and efficient architecture.
- For requests or jobs that can be processed anytime, use scheduling mechanisms
to process jobs in batch for more efficiency. Here are some examples of scheduling
mechanisms on AWS:

Scheduling mechanism
Description

[Amazon EventBridge Scheduler](https://aws.amazon.com/blogs/compute/introducing-amazon-eventbridge-scheduler/)

A capability from [Amazon EventBridge](https://aws.amazon.com/eventbridge/) that allows you to create, run, and manage scheduled tasks at scale.

[AWS Glue time-based schedule](https://docs.aws.amazon.com/glue/latest/dg/monitor-data-warehouse-schedule.html)

Define a time-based schedule for your crawlers and jobs in AWS Glue.

[Amazon Elastic Container Service (Amazon ECS) scheduled tasks](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/scheduled_tasks.html)

Amazon ECS supports creating scheduled tasks. Scheduled tasks use Amazon EventBridge rules to run tasks either on a schedule or in a response to an EventBridge event.

[Instance Scheduler](https://aws.amazon.com/solutions/implementations/instance-scheduler-on-aws/)

Configure start and stop schedules for your Amazon EC2 and Amazon Relational Database Service instances.
- If you use polling and webhooks mechanisms in your architecture, replace those with events.
Use [event-driven architectures](https://docs.aws.amazon.com/lambda/latest/operatorguide/event-driven-architectures.html) to build highly efficient workloads.
- Leverage [serverless on AWS](https://aws.amazon.com/serverless/) to eliminate over-provisioned infrastructure.
- Right size individual components of your architecture to prevent idling resources waiting for input.

You can use the [Rightsizing Recommendations in AWS Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-rightsizing.html) or [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/) to identify rightsizing opportunities.
- For more detail, see [Right Sizing: Provisioning Instances to Match Workloads](https://docs.aws.amazon.com/whitepapers/latest/cost-optimization-right-sizing/cost-optimization-right-sizing.html).

## Resources

**Related documents:**

- [What
is Amazon Simple Queue Service?](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html)
- [What
is Amazon MQ?](https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/welcome.html)
- [Scaling
based on Amazon SQS](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-using-sqs-queue.html)
- [What
is AWS Step Functions?](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
- [What
is AWS Lambda?](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [Using
AWS Lambda with Amazon SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [What
is Amazon EventBridge?](https://docs.aws.amazon.com/eventbridge/latest/userguide/what-is-amazon-eventbridge.html)
- [Managing Asynchronous Workflows with a REST API](https://aws.amazon.com/blogs/architecture/managing-asynchronous-workflows-with-a-rest-api/)

**Related videos:**

- [AWS re:Invent 2023 - Navigating the journey to serverless event-driven architecture](https://www.youtube.com/watch?v=hvGuqHp051c)
- [AWS re:Invent 2023 - Using serverless for event-driven architecture & domain-driven design](https://www.youtube.com/watch?v=3foMZJSPMI4)
- [AWS re:Invent 2023 - Advanced event-driven patterns with Amazon EventBridge](https://www.youtube.com/watch?v=6X4lSPkn4ps)
- [AWS re:Invent 2023 - Sustainable architecture: Past, present, and future](https://www.youtube.com/watch?v=2xpUQ-Q4QcM)
- [Asynchronous Message Patterns | AWS Events](https://www.youtube.com/watch?v=-yJqBuwouZ4)

**Related examples:**

- [Event-driven architecture with AWS Graviton Processors and Amazon EC2 Spot Instances](https://catalog.workshops.aws/well-architected-sustainability/en-US/2-software-and-architecture/event-driven-architecture-with-graviton-spot)
