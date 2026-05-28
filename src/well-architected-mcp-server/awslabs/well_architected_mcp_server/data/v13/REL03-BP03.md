---
id: "REL03-BP03"
title: "Provide service contracts per API"
framework: "WAF"
domain: "Reliability"
capability: "How do you design your workload service architecture?"
risk_level: "Medium"
---

# REL03-BP03 Provide service contracts per API

## Desired Outcome
Applications built with service-oriented or microservice architectures are able to operate independently while having integrated runtime dependency. Changes deployed to an API consumer or producer do not interrupt the stability of the overall system when both sides follow a common API contract. Components that communicate over service APIs can perform independent functional releases, upgrades to runtime dependencies, or fail over to a disaster recovery (DR) site with little or no impact to each other. In addition, discrete services are able to independently scale absorbing resource demand without requiring other services to scale in unison.

## Anti-Patterns
- Creating service APIs without strongly typed schemas. This results in APIs that cannot be used to generate API bindings and payloads that can’t be programmatically validated.
- Not adopting a versioning strategy, which forces API consumers to update and release or fail when service contracts evolve.
- Error messages that leak details of the underlying service implementation rather than describe integration failures in the domain context and language.
- Not using API contracts to develop test cases and mock API implementations to allow for independent testing of service components.

## Implementation Guidance
 Once you have identified business domains and determined your workload segmentation, you can develop your service APIs. First, define machine-readable service contracts for APIs, and then implement an API versioning strategy. When you are ready to integrate services over common protocols like REST, GraphQL, or asynchronous events, you can incorporate AWS services into your architecture to integrate your components with strongly-typed API contracts.

 **AWS services for service API contrats**

 Incorporate AWS services including [Amazon API Gateway](https://aws.amazon.com/api-gateway/), [AWS AppSync](https://aws.amazon.com/appsync/), and [Amazon EventBridge](https://aws.amazon.com/eventbridge/) into your architecture to use API service contracts in your application. Amazon API Gateway helps you integrate with directly native AWS services and other web services. API Gateway supports the [OpenAPI specification](https://github.com/OAI/OpenAPI-Specification) and versioning. AWS AppSync is a managed [GraphQL](https://graphql.org/) endpoint you configure by defining a GraphQL schema to define a service interface for queries, mutations and subscriptions. Amazon EventBridge uses event schemas to define events and generate code bindings for your events.

## Implementation Steps
- First, define a contract for your API. A contract will express the capabilities of an API as well as define strongly typed data objects and fields for the API input and output.
- When you configure APIs in API Gateway, you can import and export OpenAPI Specifications for your endpoints.
  - [Importing an OpenAPI definition](https://docs.aws.amazon.com/apigateway/latest/developerguide/import-edge-optimized-api.html) simplifies the creation of your API and can be integrated with AWS infrastructure as code tools like the [AWS Serverless Application Model](https://aws.amazon.com/serverless/sam/) and [AWS Cloud Development Kit (AWS CDK)](https://aws.amazon.com/cdk/).
  - [Exporting an API definition](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-export-api.html) simplifies integrating with API testing tools and provides services consumer an integration specification.
- You can define and manage GraphQL APIs with AWS AppSync by [defining a GraphQL schema](https://docs.aws.amazon.com/appsync/latest/devguide/designing-your-schema.html) file to generate your contract interface and simplify interaction with complex REST models, multiple database tables or legacy services.
- [AWS Amplify](https://aws.amazon.com/amplify/) projects that are integrated with AWS AppSync generate strongly typed JavaScript query files for use in your application as well as an AWS AppSync GraphQL client library for [Amazon DynamoDB](https://aws.amazon.com/dynamodb/) tables.
- When you consume service events from Amazon EventBridge, events adhere to schemas that already exist in the schema registry or that you define with the OpenAPI Spec. With a schema defined in the registry, you can also generate client bindings from the schema contract to integrate your code with events.
- Extending or version your API. Extending an API is a simpler option when adding fields that can be configured with optional fields or default values for required fields.
  - JSON based contracts for protocols like REST and GraphQL can be a good fit for contract extension.
  - XML based contracts for protocols like SOAP should be tested with service consumers to determine the feasibility of contract extension.
- When versioning an API, consider implementing proxy versioning where a facade is used to support versions so that logic can be maintained in a single codebase.
  - With API Gateway you can use [request and response mappings](https://docs.aws.amazon.com/apigateway/latest/developerguide/request-response-data-mappings.html#transforming-request-response-body) to simplify absorbing contract changes by establishing a facade to provide default values for new fields or to strip removed fields from a request or response. With this approach the underlying service can maintain a single codebase.

## Resources
### Related Best Practices
- [REL03-BP01 Choose how to segment your workload](rel_service_architecture_monolith_soa_microservice.md)
- [REL03-BP02 Build services focused on specific business domains and functionality](rel_service_architecture_business_domains.md)
- [REL04-BP02 Implement loosely coupled dependencies](rel_prevent_interaction_failure_loosely_coupled_system.md)
- [REL05-BP03 Control and limit retry calls](rel_mitigate_interaction_failure_limit_retries.md)
- [REL05-BP05 Set client timeouts](rel_mitigate_interaction_failure_client_timeouts.md)
### Related Documents
- [ What Is An API (Application Programming Interface)? ](https://aws.amazon.com/what-is/api/)
- [ Implementing Microservices on AWS](https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/microservices-on-aws.html)
- [ Microservice Trade-Offs ](https://martinfowler.com/articles/microservice-trade-offs.html)
- [ Microservices - a definition of this new architectural term ](https://www.martinfowler.com/articles/microservices.html)
- [ Microservices on AWS](https://aws.amazon.com/microservices/)
- [ Working with API Gateway extensions to OpenAPI ](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions.html)
- [ OpenAPI-Specification ](https://github.com/OAI/OpenAPI-Specification)
- [ GraphQL: Schemas and Types ](https://graphql.org/learn/schema/)
- [ Amazon EventBridge code bindings ](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema-code-bindings.html)
### Related Examples
- [ Amazon API Gateway: Configuring a REST API Using OpenAPI ](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-import-api.html)
- [ Amazon API Gateway to Amazon DynamoDB CRUD application using OpenAPI ](https://serverlessland.com/patterns/apigw-ddb-openapi-crud?ref=search)
- [ Modern application integration patterns in a serverless age: API Gateway Service Integration ](https://catalog.us-east-1.prod.workshops.aws/workshops/be7e1ee7-b91f-493d-93b0-8f7c5b002479/en-US/labs/asynchronous-request-response-poll/api-gateway-service-integration)
- [ Implementing header-based API Gateway versioning with Amazon CloudFront ](https://aws.amazon.com/blogs/compute/implementing-header-based-api-gateway-versioning-with-amazon-cloudfront/)
- [AWS AppSync: Building a client application ](https://docs.aws.amazon.com/appsync/latest/devguide/building-a-client-app.html#aws-appsync-building-a-client-app)
### Related Videos
- [ Using OpenAPI in AWS SAM to manage API Gateway ](https://www.youtube.com/watch?v=fet3bh0QA80)
### Related Tools
- [ Amazon API Gateway ](https://aws.amazon.com/api-gateway/)
- [AWS AppSync](https://aws.amazon.com/appsync/)
- [ Amazon EventBridge ](https://aws.amazon.com/eventbridge/)
