---
id: "REL03-BP02"
title: "Build services focused on specific business domains and functionality"
framework: "WAF"
domain: "Reliability"
capability: "How do you design your workload service architecture?"
risk_level: "High"
---

# REL03-BP02 Build services focused on specific business domains and functionality

## Desired Outcome
Engineers and business stakeholders jointly define bounded contexts and use them to design systems as services that fulfill specific business functions. These teams use established practices like event storming to define requirements. New applications are designed as services well-defined boundaries and loosely coupling. Existing monoliths are decomposed into [bounded contexts](https://martinfowler.com/bliki/BoundedContext.html) and system designs move towards SOA or microservice architectures. When monoliths are refactored, established approaches like bubble contexts and monolith decomposition patterns are applied.

 Domain-oriented services are executed as one or more processes that don’t share state. They independently respond to fluctuations in demand and handle fault scenarios in light of domain specific requirements.

## Anti-Patterns
- Teams are formed around specific technical domains like UI and UX, middleware, or database instead of specific business domains.
- Applications span domain responsibilities. Services that span bounded contexts can be more difficult to maintain, require larger testing efforts, and require multiple domain teams to participate in software updates.
- Domain dependencies, like domain entity libraries, are shared across services such that changes for one service domain require changes to other service domains
- Service contracts and business logic don’t express entities in a common and consistent domain language, resulting in translation layers that complicate systems and increase debugging efforts.

## Implementation Guidance
 Domain-driven design (DDD) is the foundational approach of designing and building software around business domains. It’s helpful to work with an existing framework when building services focused on business domains. When working with existing monolithic applications, you can take advantage of decomposition patterns that provide established techniques to modernize applications into services.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/domain-driven-decision.png)

## Implementation Steps
- Teams can hold [event storming](https://serverlessland.com/event-driven-architecture/visuals/event-storming) workshops to quickly identify events, commands, aggregates and domains in a lightweight sticky note format.
- Once domain entities and functions have been formed in a domain context, you can divide your domain into services using [bounded context](https://martinfowler.com/bliki/BoundedContext.html), where entities that share similar features and attributes are grouped together. With the model divided into contexts, a template for how to boundary microservices emerges.
  - For example, the Amazon.com website entities might include package, delivery, schedule, price, discount, and currency.
  - Package, delivery, and schedule are grouped into the shipping context, while price, discount, and currency are grouped into the pricing context.
- [Decomposing monoliths into microservices](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/welcome.html) outlines patterns for refactoring microservices. Using patterns for decomposition by business capability, subdomain, or transaction aligns well with domain-driven approaches.
- Tactical techniques such as the [bubble context](https://www.domainlanguage.com/wp-content/uploads/2016/04/GettingStartedWithDDDWhenSurroundedByLegacySystemsV1.pdf) allow you to introduce DDD in existing or legacy applications without up-front rewrites and full commitments to DDD. In a bubble context approach, a small bounded context is established using a service mapping and coordination, or [anti-corruption layer](https://serverlessland.com/event-driven-architecture/visuals/messages-between-bounded-context), which protects the newly defined domain model from external influences.

 After teams have performed domain analysis and defined entities and service contracts, they can take advantage of AWS services to implement their domain-driven design as cloud-based services.
- Start your development by defining tests that exercise business rules of your domain. Test-driven development (TDD) and behavior-driven development (BDD) help teams keep services focused on solving business problems.
- Select the [AWS services](https://aws.amazon.com/microservices/) that best meet your business domain requirements and [microservice architecture](https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/microservices-on-aws.html):
  - [AWS Serverless](https://aws.amazon.com/serverless/) allows your team focus on specific domain logic instead of managing servers and infrastructure.
  - [Containers at AWS](https://aws.amazon.com/containers/) simplify the management of your infrastructure, so you can focus on your domain requirements.
  - [Purpose built databases](https://aws.amazon.com/products/databases/) help you match your domain requirements to the best fit database type.
- [Building hexagonal architectures on AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/hexagonal-architectures/welcome.html) outlines a framework to build business logic into services working backwards from a business domain to fulfill functional requirements and then attach integration adapters. Patterns that separate interface details from business logic with AWS services help teams focus on domain functionality and improve software quality.

## Resources
### Related Best Practices
- [REL03-BP01 Choose how to segment your workload](rel_service_architecture_monolith_soa_microservice.md)
- [REL03-BP03 Provide service contracts per API](rel_service_architecture_api_contracts.md)
### Related Documents
- [AWS Microservices](https://aws.amazon.com/microservices/)
- [Implementing Microservices on AWS](https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/introduction.html)
- [How to break a Monolith into Microservices](https://martinfowler.com/articles/break-monolith-into-microservices.html)
- [Getting Started with DDD when Surrounded by Legacy Systems](https://domainlanguage.com/wp-content/uploads/2016/04/GettingStartedWithDDDWhenSurroundedByLegacySystemsV1.pdf)
- [ Domain-Driven Design: Tackling Complexity in the Heart of Software ](https://www.amazon.com/gp/product/0321125215)
- [ Building hexagonal architectures on AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/hexagonal-architectures/welcome.html)
- [ Decomposing monoliths into microservices ](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/welcome.html)
- [ Event Storming ](https://serverlessland.com/event-driven-architecture/visuals/event-storming)
- [ Messages Between Bounded Contexts ](https://serverlessland.com/event-driven-architecture/visuals/messages-between-bounded-context)
- [ Microservices ](https://www.martinfowler.com/articles/microservices.html)
- [ Test-driven development ](https://en.wikipedia.org/wiki/Test-driven_development)
- [ Behavior-driven development ](https://en.wikipedia.org/wiki/Behavior-driven_development)
### Related Examples
- [ Designing Cloud Native Microservices on AWS (from DDD/EventStormingWorkshop) ](https://github.com/aws-samples/designing-cloud-native-microservices-on-aws/tree/main)
### Related Tools
- [AWS Cloud Databases ](https://aws.amazon.com/products/databases/)
- [ Serverless on AWS](https://aws.amazon.com/serverless/)
- [ Containers at AWS](https://aws.amazon.com/containers/)
