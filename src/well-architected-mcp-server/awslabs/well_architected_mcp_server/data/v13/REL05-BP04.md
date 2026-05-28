---
id: "REL05-BP04"
title: "Fail fast and limit queues"
framework: "WAF"
domain: "Reliability"
capability: "How do you design interactions in a distributed system to mitigate or withstand failures?"
risk_level: "High"
---

# REL05-BP04 Fail fast and limit queues

## Desired Outcome
When systems experience resource contention, timeouts, exceptions, or grey failures that make service level objectives unachievable, fail fast strategies allow for faster system recovery. Systems that must absorb traffic spikes and can accommodate asynchronous processing can improve reliability by allowing clients to quickly release requests by using queues to buffer requests to backend services. When buffering requests to queues, queue management strategies are implemented to avoid insurmountable backlogs.

## Anti-Patterns
- Implementing message queues but not configuring dead letter queues (DLQ) or alarms on DLQ volumes to detect when a system is in failure.
- Not measuring the age of messages in a queue, a measurement of latency to understand when queue consumers are falling behind or erroring out causing retrying.
- Not clearing backlogged messages from a queue, when there is no value in processing these messages if the business need no longer exists.
- Configuring first in first out (FIFO) queues when last in first out (LIFO) queues would better serve client needs, for example when strict ordering is not required and backlog processing is delaying all new and time sensitive requests resulting in all clients experiencing breached service levels.
- Exposing internal queues to clients instead of exposing APIs that manage work intake and place requests into internal queues.
- Combining too many work request types into a single queue which can exacerbate backlog conditions by spreading resource demand across request types.
- Processing complex and simple requests in the same queue, despite needing different monitoring, timeouts and resource allocations.
- Not validating inputs or using assertions to implement fail fast mechanisms in software that bubble up exceptions to higher level components that can handle errors gracefully.
- Not removing faulty resources from request routing, especially when failures are grey emitting both successes and failures due to crashing and restarting, intermittent dependency failure, reduced capacity, or network packet loss.

## Implementation Guidance
 Fail fast strategies can be coded into software solutions as well as configured into infrastructure. In addition to failing fast, queues are a straightforward yet powerful architectural technique to decouple system components smooth load. [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) provides capabilities to monitor for and alarm on failures. Once a system is known to be failing, mitigation strategies can be invoked, including failing away from impaired resources. When systems implement queues with [Amazon SQS](https://aws.amazon.com/sqs/) and other queue technologies to smooth load, they must consider how to manage queue backlogs, as well as message consumption failures.

## Implementation Steps
- Implement programmatic assertions or specific metrics in your software and use them to explicitly alert on system issues. Amazon CloudWatch helps you create metrics and alarms based on application log pattern and SDK instrumentation.
- Use CloudWatch metrics and alarms to fail away from impaired resources that are adding latency to processing or repeatedly failing to process requests.
- Use asynchronous processing by designing APIs to accept requests and append requests to internal queues using Amazon SQS and then respond to the message-producing client with a success message so the client can release resources and move on with other work while backend queue consumers process requests.
- Measure and monitor for queue processing latency by producing a CloudWatch metric each time you take a message off a queue by comparing now to message timestamp.
- When failures prevent successful message processing or traffic spikes in volumes that cannot be processed within service level agreements, sideline older or excess traffic to a spillover queue. This allows priority processing of new work, and older work when capacity is available. This technique is an approximation of LIFO processing and allows normal system processing for all new work.
- Use dead letter or redrive queues to move messages that can’t be processed out of the backlog into a location that can be researched and resolved later
- Either retry or, when tolerable, drop old messages by comparing now to the message timestamp and discarding messages that are no longer relevant to the requesting client.

## Resources
### Related Best Practices
- [REL04-BP02 Implement loosely coupled dependencies](rel_prevent_interaction_failure_loosely_coupled_system.md)
- [REL05-BP02 Throttle requests](rel_mitigate_interaction_failure_throttle_requests.md)
- [REL05-BP03 Control and limit retry calls](rel_mitigate_interaction_failure_limit_retries.md)
- [REL06-BP02 Define and calculate metrics (Aggregation)](rel_monitor_aws_resources_notification_aggregation.md)
- [REL06-BP07 Monitor end-to-end tracing of requests through your system](rel_monitor_aws_resources_end_to_end.md)
### Related Documents
- [ Avoiding insurmountable queue backlogs ](https://aws.amazon.com/builders-library/avoiding-insurmountable-queue-backlogs/)
- [Fail Fast](https://www.martinfowler.com/ieeeSoftware/failFast.pdf)
- [ How can I prevent an increasing backlog of messages in my Amazon SQS queue? ](https://repost.aws/knowledge-center/sqs-message-backlog)
- [ Elastic Load Balancing: Zonal Shift ](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/zonal-shift.html)
- [ Amazon Application Recovery Controller: Routing control for traffic failover ](https://docs.aws.amazon.com/r53recovery/latest/dg/getting-started-routing-controls.html)
### Related Examples
- [ Enterprise Integration Patterns: Dead Letter Channel ](https://www.enterpriseintegrationpatterns.com/patterns/messaging/DeadLetterChannel.html)
### Related Videos
- [AWS re:Invent 2022 - Operating highly available Multi-AZ applications](https://www.youtube.com/watch?v=mwUV5skJJ0s)
### Related Tools
- [ Amazon SQS ](https://aws.amazon.com/sqs/)
- [ Amazon MQ ](https://aws.amazon.com/amazon-mq/)
- [AWS IoT Core](https://aws.amazon.com/iot-core/)
- [ Amazon CloudWatch ](https://aws.amazon.com/cloudwatch/)
