---
id: "REL03-BP01"
title: "Choose how to segment your workload"
framework: "WAF"
domain: "Reliability"
capability: "How do you design your workload service architecture?"
risk_level: "High"
effort: "High"
---

# REL03-BP01 Choose how to segment your workload

## Desired Outcome
Workloads should be supportable, scalable, and as loosely coupled as possible.

 When making choices about how to segment your workload, balance the benefits against the complexities. What is right for a new product racing to first launch is different than what a workload built to scale from the start needs. When refactoring an existing monolith, you will need to consider how well the application will support a decomposition towards statelessness. Breaking services into smaller pieces allows small, well-defined teams to develop and manage them. However, smaller services can introduce complexities which include possible increased latency, more complex debugging, and increased operational burden.

## Anti-Patterns
- The [microservice *Death Star*](https://mrtortoise.github.io/architecture/lean/design/patterns/ddd/2018/03/18/deathstar-architecture.html) is a situation in which the atomic components become so highly interdependent that a failure of one results in a much larger failure, making the components as rigid and fragile as a monolith.

## Implementation Guidance
 Choose your architecture type based on how you will segment your workload. Choose an SOA or microservices architecture (or in some rare cases, a monolithic architecture). Even if you choose to start with a monolith architecture, you must ensure that it’s modular and can ultimately evolve to SOA or microservices as your product scales with user adoption. SOA and microservices offer respectively smaller segmentation, which is preferred as a modern scalable and reliable architecture, but there are trade-offs to consider, especially when deploying a microservice architecture.

 One primary trade-off is that you now have a distributed compute architecture that can make it harder to achieve user latency requirements and there is additional complexity in the debugging and tracing of user interactions. You can use AWS X-Ray to assist you in solving this problem. Another effect to consider is increased operational complexity as you increase the number of applications that you are managing, which requires the deployment of multiple independency components.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/monolith-soa-microservices-comparison.png)

## Implementation Steps
- Determine the appropriate architecture to refactor or build your application. SOA and microservices offer respectively smaller segmentation, which is preferred as a modern scalable and reliable architecture. SOA can be a good compromise for achieving smaller segmentation while avoiding some of the complexities of microservices. For more details, see [Microservice Trade-Offs](https://martinfowler.com/articles/microservice-trade-offs.html).
- If your workload is amenable to it, and your organization can support it, you should use a microservices architecture to achieve the best agility and reliability. For more details, see [Implementing Microservices on AWS.](https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/introduction.html)
- Consider following the [*Strangler Fig* pattern](https://martinfowler.com/bliki/StranglerFigApplication.html) to refactor a monolith into smaller components. This involves gradually replacing specific application components with new applications and services. [AWS Migration Hub Refactor Spaces](https://docs.aws.amazon.com/migrationhub-refactor-spaces/latest/userguide/what-is-mhub-refactor-spaces.html) acts as the starting point for incremental refactoring. For more details, see [Seamlessly migrate on-premises legacy workloads using a strangler pattern](https://aws.amazon.com/blogs/architecture/seamlessly-migrate-on-premises-legacy-workloads-using-a-strangler-pattern/).
- Implementing microservices may require a service discovery mechanism to allow these distributed services to communicate with each other. [AWS App Mesh](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html) can be used with service-oriented architectures to provide reliable discovery and access of services. [AWS Cloud Map](https://aws.amazon.com/cloud-map/) can also be used for dynamic, DNS-based service discovery.
- If you’re migrating from a monolith to SOA, [Amazon MQ](https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/welcome.html) can help bridge the gap as a service bus when redesigning legacy applications in the cloud.
- For existing monoliths with a single, shared database, choose how to reorganize the data into smaller segments. This could be by business unit, access pattern, or data structure. At this point in the refactoring process, you should choose to move forward with a relational or non-relational (NoSQL) type of database. For more details, see [From SQL to NoSQL](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/SQLtoNoSQL.html).

## Resources
### Related Best Practices
- [REL03-BP02 Build services focused on specific business domains and functionality](rel_service_architecture_business_domains.md)
### Related Documents
- [Amazon API Gateway: Configuring a REST API Using OpenAPI](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-import-api.html)
- [What is Service-Oriented Architecture?](https://aws.amazon.com/what-is/service-oriented-architecture/)
- [Bounded Context (a central pattern in Domain-Driven Design)](https://martinfowler.com/bliki/BoundedContext.html)
- [Implementing Microservices on AWS](https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/introduction.html)
- [Microservice Trade-Offs](https://martinfowler.com/articles/microservice-trade-offs.html)
- [Microservices - a definition of this new architectural term](https://www.martinfowler.com/articles/microservices.html)
- [Microservices on AWS](https://aws.amazon.com/microservices/)
- [What is AWS App Mesh?](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)
### Related Examples
- [Iterative App Modernization Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/f2c0706c-7192-495f-853c-fd3341db265a/en-US/intro)
### Related Videos
- [Delivering Excellence with Microservices on AWS](https://www.youtube.com/watch?v=otADkIyugzY)
