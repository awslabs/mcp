---
id: "REL04-BP02"
title: "Implement loosely coupled dependencies"
framework: "WAF"
domain: "Reliability"
capability: "How do you design interactions in a distributed system to prevent failures?"
risk_level: "High"
---

# REL04-BP02 Implement loosely coupled dependencies

## Desired Outcome
Implementing loosely coupled dependencies allows you to minimize the surface area for failure to a component level, which helps diagnose and resolve issues. It also simplifies development cycles, allowing teams to implement changes at a modular level without affecting the performance of other components that depend on it. This approach provides the capability to scale out at a component level based on resource needs, as well as utilization of a component contributing to cost-effectiveness.

## Anti-Patterns
- Deploying a monolithic workload.
- Directly invoking APIs between workload tiers with no capability of failover or asynchronous processing of the request.
- Tight coupling using shared data. Loosely coupled systems should avoid sharing data through shared databases or other forms of tightly coupled data storage, which can reintroduce tight coupling and hinder scalability.
- Ignoring back pressure. Your workload should have the ability to slow down or stop incoming data when a component can't process it at the same rate.

## Implementation Guidance
 Implement loosely coupled dependencies. There are various solutions that allow you to build loosely coupled applications. These include services for implementing fully managed queues, automated workflows, react to events, and APIs among others which can help isolate behavior of components from other components, and as such increasing resilience and agility.
- **Build event-driven architectures:** [Amazon EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html) helps you build loosely coupled and distributed event-driven architectures.
- **Implement queues in distributed systems:** You can use [Amazon Simple Queue Service (Amazon SQS)](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html) to integrate and decouple distributed systems.
- **Containerize components as microservices:** [Microservices](https://aws.amazon.com/microservices/) allow teams to build applications composed of small independent components which communicate over well-defined APIs. [Amazon Elastic Container Service (Amazon ECS)](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html), and [Amazon Elastic Kubernetes Service (Amazon EKS)](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html) can help you get started faster with containers.
- **Manage workflows with Step Functions:** [Step Functions](https://aws.amazon.com/step-functions/getting-started/) help you coordinate multiple AWS services into flexible workflows.
- **Leverage publish-subscribe (pub/sub) messaging architectures:** [Amazon Simple Notification Service (Amazon SNS)](https://docs.aws.amazon.com/sns/latest/dg/welcome.html) provides message delivery from publishers to subscribers (also known as producers and consumers).

## Implementation Steps
- Components in an event-driven architecture are initiated by events. Events are actions that happen in a system, such as a user adding an item to a cart. When an action is successful, an event is generated that actuates the next component of the system.
  - [ Building Event-driven Applications with Amazon EventBridge ](https://aws.amazon.com/blogs/compute/building-an-event-driven-application-with-amazon-eventbridge/)
  - [AWS re:Invent 2022 - Designing Event-Driven Integrations using Amazon EventBridge ](https://www.youtube.com/watch?v=W3Rh70jG-LM)
- Distributed messaging systems have three main parts that need to be implemented for a queue based architecture. They include components of the distributed system, the queue that is used for decoupling (distributed on Amazon SQS servers), and the messages in the queue. A typical system has producers which initiate the message into the queue, and the consumer which receives the message from the queue. The queue stores messages across multiple Amazon SQS servers for redundancy.
  - [ Basic Amazon SQS architecture ](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-basic-architecture.html)
  - [ Send Messages Between Distributed Applications with Amazon Simple Queue Service ](https://aws.amazon.com/getting-started/hands-on/send-messages-distributed-applications/)
- Microservices, when well-utilized, enhance maintainability and boost scalability, as loosely coupled components are managed by independent teams. It also allows for the isolation of behaviors to a single component in case of changes.
  - [ Implementing Microservices on AWS](https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/microservices-on-aws.html)
  - [ Let's Architect\$1 Architecting microservices with containers ](https://aws.amazon.com/blogs/architecture/lets-architect-architecting-microservices-with-containers/)
- With AWS Step Functions you can build distributed applications, automate processes, orchestrate microservices, among other things. The orchestration of multiple components into an automated workflow allows you to decouple dependencies in your application.
  - [ Create a Serverless Workflow with AWS Step Functions and AWS Lambda](https://aws.amazon.com/tutorials/create-a-serverless-workflow-step-functions-lambda/)
  - [ Getting Started with AWS Step Functions](https://aws.amazon.com/step-functions/getting-started/)

## Resources
### Related Documents
- [Amazon EC2: Ensuring Idempotency](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/Run_Instance_Idempotency.html)
- [The Amazon Builders' Library: Challenges with distributed systems](https://aws.amazon.com/builders-library/challenges-with-distributed-systems/)
- [The Amazon Builders' Library: Reliability, constant work, and a good cup of coffee](https://aws.amazon.com/builders-library/reliability-and-constant-work/)
- [What Is Amazon EventBridge?](https://docs.aws.amazon.com/eventbridge/latest/userguide/what-is-amazon-eventbridge.html)
- [What Is Amazon Simple Queue Service?](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html)
- [ Break up with your monolith ](https://pages.awscloud.com/break-up-your-monolith.html)
- [ Orchestrate Queue-based Microservices with AWS Step Functions and Amazon SQS ](https://aws.amazon.com/tutorials/orchestrate-microservices-with-message-queues-on-step-functions/)
- [ Basic Amazon SQS architecture ](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-basic-architecture.html)
- [ Queue-Based Architecture ](https://docs.aws.amazon.com/wellarchitected/latest/high-performance-computing-lens/queue-based-architecture.html)
### Related Videos
- [AWS New York Summit 2019: Intro to Event-driven Architectures and Amazon EventBridge (MAD205)](https://youtu.be/tvELVa9D9qU)
- [AWS re:Invent 2018: Close Loops and Opening Minds: How to Take Control of Systems, Big and Small ARC337 (includes loose coupling, constant work, static stability)](https://youtu.be/O8xLxNje30M)
- [AWS re:Invent 2019: Moving to event-driven architectures (SVS308)](https://youtu.be/h46IquqjF3E)
- [AWS re:Invent 2019: Scalable serverless event-driven applications using Amazon SQS and Lambda ](https://www.youtube.com/watch?v=2rikdPIFc_Q)
- [AWS re:Invent 2022 - Designing event-driven integrations using Amazon EventBridge ](https://www.youtube.com/watch?v=W3Rh70jG-LM)
- [AWS re:Invent 2017: Elastic Load Balancing Deep Dive and Best Practices ](https://www.youtube.com/watch?v=9TwkMMogojY)
