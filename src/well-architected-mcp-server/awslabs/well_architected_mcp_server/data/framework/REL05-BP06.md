---
id: "REL05-BP06"
title: "Make systems stateless where possible"
pillar: "Reliability"
risk_level: "MEDIUM"
capability: "How do you design interactions in a distributed system to mitigate or withstand failures?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_stateless.html"
---

# REL05-BP06 Make systems stateless where possible

Systems should either not require state, or should offload state
such that between different client requests, there is no dependence
on locally stored data on disk and in memory. This allows servers to
be replaced at will without causing an availability impact.

When users or services interact with an application, they often
perform a series of interactions that form a session. A session is
unique data for users that persists between requests while they use
the application. A stateless application is an application that does
not need knowledge of previous interactions and does not store
session information.

Once designed to be stateless, you can then use serverless compute
services, such as AWS Lambda or AWS Fargate.

In addition to server replacement, another benefit of stateless
applications is that they can scale horizontally because any of the
available compute resources (such as EC2 instances and AWS Lambda
functions) can service any request.

**Benefits of establishing this best
practice:** Systems that are designed to be stateless are
more adaptable to horizontal scaling, making it possible to add or
remove capacity based on fluctuating traffic and demand. They are
also inherently resilient to failures and provide flexibility and
agility in application development.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Make your applications stateless. Stateless applications allow
horizontal scaling and are tolerant to the failure of an
individual node. Analyze and understand the components of your
application that maintain state within the architecture. This
helps you assess the potential impact of transitioning to a
stateless design. A stateless architecture decouples user data and
offloads the session data. This provides the flexibility to scale
each component independently to meet varying workload demands and
optimize resource utilization.

### Implementation steps

- Identify and understand the stateful components in your
application.
- Decouple data by separating and managing user data from the
core application logic.

[Amazon Cognito](https://aws.amazon.com/cognito/) can decouple user data from application
code by using features, such as
[identity
pools](https://docs.aws.amazon.com/cognito/latest/developerguide/getting-started-with-identity-pools.html),
[user
pools](https://docs.aws.amazon.com/cognito/latest/developerguide/getting-started-with-cognito-user-pools.html), and
[Amazon Cognito Sync](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-sync.html).
- You can use
[AWS Secrets Manager](https://aws.amazon.com/secrets-manager/) decouple user data by storing
secrets in a secure, centralized location. This means
that the application code doesn't need to store secrets,
which makes it more secure.
- Consider using
[Amazon S3](https://aws.amazon.com/s3/) to store large, unstructured data, such as
images and documents. Your application can retrieve this
data when required, eliminating the need to store it in
memory.
- Use
[Amazon DynamoDB](https://aws.amazon.com/dynamodb/) to store information such as user
profiles. Your application can query this data in
near-real time.

- Offload session data to a database, cache, or external
files.

[Amazon ElastiCache](https://aws.amazon.com/elasticache/), Amazon DynamoDB,
[Amazon Elastic File System](https://aws.amazon.com/efs/) (Amazon EFS), and
[Amazon MemoryDB](https://aws.amazon.com/memorydb/) are examples of AWS services
that you can use to offload session data.

- Design a stateless architecture after you identify which
state and user data need to be persisted with your storage
solution of choice.

## Resources

**Related best practices:**

- [REL11-BP03
Automate healing on all layers](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_auto_healing_system.html)

**Related documents:**

- [The
Amazon Builders' Library: Avoiding fallback in distributed
systems](https://aws.amazon.com/builders-library/avoiding-fallback-in-distributed-systems)
- [The
Amazon Builders' Library: Avoiding insurmountable queue
backlogs](https://aws.amazon.com/builders-library/avoiding-insurmountable-queue-backlogs)
- [The
Amazon Builders' Library: Caching challenges and
strategies](https://aws.amazon.com/builders-library/caching-challenges-and-strategies/)
- [Best
Practices for Stateless Web Tier on AWS](https://docs.aws.amazon.com/whitepapers/latest/best-practices-wordpress/stateless-web-tier.html)
