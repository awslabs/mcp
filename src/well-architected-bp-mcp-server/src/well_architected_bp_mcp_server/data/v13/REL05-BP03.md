---
id: "REL05-BP03"
title: "Control and limit retry calls"
framework: "WAF"
domain: "Reliability"
capability: "How do you design interactions in a distributed system to mitigate or withstand failures?"
risk_level: "High"
---

# REL05-BP03 Control and limit retry calls

## Desired Outcome
Typical components in a distributed software system include servers, load balancers, databases, and DNS servers. During normal operation, these components can respond to requests with errors that are temporary or limited, and also errors that would be persistent regardless of retries. When clients make requests to services, the requests consume resources including memory, threads, connections, ports, or any other limited resources. Controlling and limiting retries is a strategy to release and minimize consumption of resources so that system components under strain are not overwhelmed.

 When client requests time out or receive error responses, they should determine whether or not to retry. If they do retry, they do so with exponential backoff with jitter and a maximum retry value. As a result, backend services and processes are given relief from load and time to self-heal, resulting in faster recovery and successful request servicing.

## Anti-Patterns
- Implementing retries without adding exponential backoff, jitter, and maximum retry values. Backoff and jitter help avoid artificial traffic spikes due to unintentionally coordinated retries at common intervals.
- Implementing retries without testing their effects or assuming retries are already built into an SDK without testing retry scenarios.
- Failing to understand published error codes from dependencies, leading to retrying all errors, including those with a clear cause that indicates lack of permission, configuration error, or another condition that predictably will not resolve without manual intervention.
- Not addressing observability practices, including monitoring and alerting on repeated service failures so that underlying issues are made known and can be addressed.
- Developing custom retry mechanisms when built-in or third-party retry capabilities suffice.
- Retrying at multiple layers of your application stack in a manner which compounds retry attempts further consuming resources in a retry storm. Be sure to understand how these errors affect your application the dependencies you rely on, then implement retries at only one level.
- Retrying service calls that are not idempotent, causing unexpected side effects like duplicated results.

## Implementation Guidance
 Control and limit retry calls. Use exponential backoff to retry after progressively longer intervals. Introduce jitter to randomize retry intervals and limit the maximum number of retries.

 Some AWS SDKs implement retries and exponential backoff by default. Use these built-in AWS implementations where applicable in your workload. Implement similar logic in your workload when calling services that are idempotent and where retries improve your client availability. Decide what the timeouts are and when to stop retrying based on your use case. Build and exercise testing scenarios for those retry use cases.

## Implementation Steps
- Determine the optimal layer in your application stack to implement retries for the services your application relies on.
- Be aware of existing SDKs that implement proven retry strategies with exponential backoff and jitter for your language of choice, and favor these over writing your own retry implementations.
- Verify that [services are idempotent](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) before implementing retries. Once retries are implemented, be sure they are both tested and regularly exercise in production.
- When calling AWS service APIs, use the [AWS SDKs](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html) and [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-retries.html) and understand the retry configuration options. Determine if the defaults work for your use case, test, and adjust as needed.

## Resources
### Related Best Practices
- [REL04-BP04 Make mutating operations idempotent](rel_prevent_interaction_failure_idempotent.md)
- [REL05-BP02 Throttle requests](rel_mitigate_interaction_failure_throttle_requests.md)
- [REL05-BP04 Fail fast and limit queues](rel_mitigate_interaction_failure_fail_fast.md)
- [REL05-BP05 Set client timeouts](rel_mitigate_interaction_failure_client_timeouts.md)
- [REL11-BP01 Monitor all components of the workload to detect failures](rel_withstand_component_failures_monitoring_health.md)
### Related Documents
- [Error Retries and Exponential Backoff in AWS](https://docs.aws.amazon.com/general/latest/gr/api-retries.html)
- [The Amazon Builders' Library: Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [ Exponential Backoff and Jitter ](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [ Making retries safe with idempotent APIs ](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
### Related Examples
- [ Spring Retry ](https://github.com/spring-projects/spring-retry)
- [ Resilience4j Retry ](https://resilience4j.readme.io/docs/retry)
### Related Videos
- [Retry, backoff, and jitter: AWS re:Invent 2019: Introducing The Amazon Builders’ Library (DOP328)](https://youtu.be/sKRdemSirDM?t=1884)
### Related Tools
- [AWS SDKs and Tools: Retry behavior ](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)
- [AWS Command Line Interface: AWS CLI retries ](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-retries.html)
