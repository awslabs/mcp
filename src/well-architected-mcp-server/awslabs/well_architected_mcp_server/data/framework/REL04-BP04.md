---
id: "REL04-BP04"
title: "Make mutating operations idempotent"
pillar: "Reliability"
risk_level: "MEDIUM"
capability: "How do you design interactions in a distributed system to prevent failures?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_idempotent.html"
description: "An idempotent service promises that each request is processed exactly once, such that making multiple identical requests has the same effect as making a single request. This makes it easier for a client to implement retries without fear that a request is erroneously processed multiple times. To do this, clients can issue API requests with an idempotency token, which is used whenever the request is repeated. An idempotent service API uses the token to return a response identical to the response that was returned the first time that the request was completed, even if the underlying state of the system has changed."
area: ["Workload architecture", "Design interactions in a distributed system to prevent failures"]
relatedIds: ["REL05-BP03", "REL06-BP01", "REL06-BP03", "REL08-BP02"]
---

# REL04-BP04 Make mutating operations idempotent

An idempotent service promises that each request is processed
exactly once, such that making multiple identical requests has the
same effect as making a single request. This makes it easier for a
client to implement retries without fear that a request is
erroneously processed multiple times. To do this, clients can issue
API requests with an idempotency token, which is used whenever the
request is repeated. An idempotent service API uses the token to
return a response identical to the response that was returned the
first time that the request was completed, even if the underlying
state of the system has changed.

In a distributed system, it is relatively simple to perform an
action at most once (client makes only one request) or at least once
(keep requesting until client gets confirmation of success). It is
more difficult to guarantee an action is performed *exactly
once*, such that making multiple identical requests has
the same effect as making a single request. Using idempotency tokens
in APIs, services can receive a mutating request one or more times
without the need to create duplicate records or side effects.

**Desired outcome:** You have a
consistent, well-documented, and widely adopted approach for
ensuring idempotency across all components and services.

**Common anti-patterns:**

- You apply idempotency indiscriminately, even when not needed.
- You introduce overly complex logic for implementing idempotency.
- You use timestamps as keys for idempotency. This can cause
inaccuracies due to clock skew or due to multiple clients that
use the same timestamps to apply changes.
- You store entire payloads for idempotency. In this approach, you
save complete data payloads for every request and overwrite it
at each new request. This can degrade performance and affect
scalability.
- You generate keys inconsistently across services. Without
consistent keys, services may fail to recognize duplicate
requests, which results in unintended results.

**Benefits of establishing this best
practice:**

- Greater scalability: The system can handle retries and duplicate
requests without having to perform additional logic or complex
state management.
- Enhanced reliability: Idempotency helps services handle multiple
identical requests in a consistent manner, which reduces the
risk of unintended side effects or duplicate records. This is
especially crucial in distributed systems, where network
failures and retries are common.
- Improved data consistency: Because the same request produces the
same response, idempotency helps maintain data consistency
across distributed systems. This is essential to maintain the
integrity of transactions and operations.
- Error handling: Idempotency tokens make error handling more
straightforward. If a client does not receive a response due to
an issue, it can safely resend the request with the same
idempotency token.
- Operational transparency: Idempotency allows for better
monitoring and logging. Services can log requests with their
idempotency tokens, which makes it easier to trace and debug
issues.
- Simplified API contract: It can simplify the contract between
the client and server side systems and reduce the fear of
erroneous data processing.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

In a distributed system, performing an action at most once (the
client makes only one request) or at least once (the client keeps
requesting until success is confirmed) is relatively
straightforward. However, it's challenging to implement
*exactly once* behavior. To achieve this, your
clients should generate and provide an idempotency token for each
request.

By using idempotency tokens, a service can distinguish between new
requests and repeated ones. When a service receives a request with
an idempotency token, it checks if the token has already been
used. If the token has been used, the service retrieves and
returns the stored response. If the token is new, the service
processes the request, stores the response along with the token,
and then returns the response. This mechanism makes all responses
idempotent, which enhances the reliability and consistency of the
distributed system.

Idempotency is also an important behavior of event-driven
architectures. These architectures are typically backed by a
message queue such as Amazon SQS, Amazon MQ, Amazon Kinesis
Streams, or Amazon Managed Streaming for Apache Kafka (MSK). In some
circumstances, a message that was published only once may be
accidentally delivered more than once. When a publisher generates
and includes idempotency tokens in messages, it requests that the
processing of any duplicate message received doesn't result in a
repeated action for the same message. Consumers should keep track
of each token received and ignore messages that contain duplicate
tokens.

Services and consumers should also pass the received idempotency
token to any downstream services that it calls. Every downstream
service in the processing chain is similarly responsible for
making sure that idempotency is implemented to avoid the side
effect of processing a message more than once.

### Implementation steps

- **Identify idempotent
operations**

Determine which operations require idempotency. These
typically include POST,
PUT, and DELETE HTTP
methods and database insert, update, or delete operations.
Operations that do not mutate state, such as read-only
queries, usually do not require idempotency unless they have
side effects.
- **Use unique identifiers**

Include a unique token in each idempotent operation request
sent by the sender, either directly in the request or as
part of its metadata (for example, an HTTP header). This
allows the receiver to recognize and handle duplicate
requests or operations. Identifiers commonly used for tokens
include
[Universally
Unique Identifiers (UUIDs)](https://datatracker.ietf.org/doc/html/rfc9562) and

[K-Sortable
Unique Identifiers (KSUIDs)](https://github.com/segmentio/ksuid).
- **Track and manage state**

Maintain the state of each operation or request in your
workload. This can be achieved by storing the idempotency
token and the corresponding state (such as
pending, completed, or
failed) in a database, cache, or other
persistent store. This state information allows the workload
to identify and handle duplicate requests or operations.

Maintain consistency and atomicity by using appropriate
concurrency control mechanisms if needed, such as locks,
transactions, or optimistic concurrency controls. This
includes the process of recording the idempotent token and
running all mutating operations associated with servicing
the request. This helps prevent race conditions and verifies
that idempotent operations run correctly.

Regularly remove old idempotency tokens from the datastore
to manage storage and performance. If your storage system
supports it, consider using expiration timestamps for data
(often known as time to live, or TTL values). The likelihood
of idempotency token reuse diminishes over time.

Common AWS storage options typically used for storing
idempotency tokens and related state include:

**Amazon DynamoDB**:
DynamoDB is a NoSQL database service that provides
low-latency performance and high availability, which
makes it well-suited for the storage of
idempotency-related data. The key-value and document
data model of DynamoDB allows for efficient storage and
retrieval of idempotency tokens and associated state
information. DynamoDB can also expire idempotency tokens
automatically if your application sets a TTL value when
it inserts them.
- **Amazon ElastiCache**:
ElastiCache can store idempotency tokens with high
throughput, low latency, and at low cost. Both
ElastiCache (Redis) and ElastiCache (Memcached) can also
expire idempotency tokens automatically if your
application sets a TTL value when it inserts them.
- **Amazon Relational Database Service
(RDS):** You can use Amazon RDS to store idempotency
tokens and related state information, especially if your
application already uses a relational database for other
purposes.
- **Amazon Simple Storage Service (S3):** Amazon S3 is a highly scalable and durable object storage service that can be used to store idempotency tokens and related metadata. The versioning capabilities of S3 can be particularly useful for maintenance of the state of idempotent operations.

The choice of storage service typically depends on factors such as the volume of idempotency-related data, the required performance characteristics, the need for durability and availability, and how the idempotency mechanism integrates with the overall workload architecture.

- **Implement idempotent
operations**

Design your API and workload components to be idempotent.
Incorporate idempotency checks into your workload
components. Before you process a request or perform an
operation, check if the unique identifier has already been
processed. If it has, return the previous result instead of
executing the operation again. For example, if a client
sends a request to create a user, check if a user with the
same unique identifier already exists. If the user exists,
it should return the existing user information instead of
creating a new one. Similarly, if a queue consumer receives
a message with a duplicate idempotency token, the consumer
should ignore the message.

Create comprehensive test suites that validate the
idempotency of requests. They should cover a wide range of
scenarios, such as successful requests, failed requests, and
duplicate requests.

If your workload leverages AWS Lambda functions, consider
Powertools for AWS Lambda. Powertools for AWS Lambda is a
developer toolkit that helps implement serverless best
practices and increase developer velocity when you work with
AWS Lambda functions. In particular, it provides a utility
to convert your Lambda functions into idempotent operations
which are safe to retry.
- **Communicate idempotency
clearly**

Document your API and workload components to clearly
communicate the idempotent nature of the operations. This
helps clients understand the expected behavior and how to
interact with your workload reliably.
- **Monitor and audit**

Implement monitoring and auditing mechanisms to detect any
issues related to the idempotency of responses, such as
unexpected response variations or excessive duplicate
request handling. This can help you detect and investigate
any issues or unexpected behaviors in your workload.

## Resources

**Related best practices:**

- [REL05-BP03
Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)
- [REL06-BP01
Monitor all components for the workload (Generation)](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_monitor_aws_resources_monitor_resources.html)
- [REL06-BP03
Send notifications (Real-time processing and alarming)](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_monitor_aws_resources_notification_monitor.html))
- [REL08-BP02
Integrate functional testing as part of your deployment](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_tracking_change_management_functional_testing.html)

**Related documents:**

- [The
Amazon Builders' Library: Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
- [The
Amazon Builders' Library: Challenges with distributed systems](https://aws.amazon.com/builders-library/challenges-with-distributed-systems/)
- [The
Amazon Builders' Library: Reliability, constant work, and a good cup of coffee](https://aws.amazon.com/builders-library/reliability-and-constant-work/)
- [Amazon Elastic Container Service: Ensuring idempotency](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/ECS_Idempotency.html)
- [How
do I make my Lambda function idempotent?](https://repost.aws/knowledge-center/lambda-function-idempotent)
- [Ensuring
idempotency in Amazon EC2 API requests](https://docs.aws.amazon.com/ec2/latest/devguide/ec2-api-idempotency.html)

**Related videos:**

- [Building
Distributed Applications with Event-driven Architecture - AWS Online Tech Talks](https://www.youtube.com/watch?v=gA2-eqDVSng&t=1668s)
- [AWS re:Invent 2023 - Building next-generation applications with event-driven architecture](https://www.youtube.com/watch?v=KXR17uwLEC8)
- [AWS re:Invent 2023 - Advanced integration patterns & trade-offs for loosely coupled systems](https://www.youtube.com/watch?v=FGKGdUiZKto)
- [AWS re:Invent 2023 - Advanced event-driven patterns with Amazon EventBridge](https://www.youtube.com/watch?v=6X4lSPkn4ps)
- [AWS re:Invent
2018 - Close Loops and Opening Minds: How to Take Control of Systems, Big and Small ARC337 (includes loose coupling, constant work, static stability)](https://youtu.be/O8xLxNje30M)
- [AWS re:Invent
2019 - Moving to event-driven architectures (SVS308)](https://youtu.be/h46IquqjF3E)

**Related tools:**

- [Idempotency
with AWS Lambda Powertools (Java)](https://docs.powertools.aws.dev/lambda/java/utilities/idempotency/)
- [Idempotency
with AWS Lambda Powertools (Python)](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)
- [AWS Lambda Powertools GitHub page](https://github.com/aws-powertools/)
