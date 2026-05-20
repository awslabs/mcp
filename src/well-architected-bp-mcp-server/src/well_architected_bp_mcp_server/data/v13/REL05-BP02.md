---
id: "REL05-BP02"
title: "Throttle requests"
framework: "WAF"
domain: "Reliability"
capability: "How do you design interactions in a distributed system to mitigate or withstand failures?"
risk_level: "High"
---

# REL05-BP02 Throttle requests

## Desired Outcome
Large volume spikes either from sudden customer traffic increases, flooding attacks, or retry storms are mitigated by request throttling, allowing workloads to continue normal processing of supported request volume.

## Anti-Patterns
- API endpoint throttles are not implemented or are left at default values without considering expected volumes.
- API endpoints are not load tested or throttling limits are not tested.
- Throttling request rates without considering request size or complexity.
- Testing maximum request rates or maximum request size, but not testing both together.
- Resources are not provisioned to the same limits established in testing.
- Usage plans have not been configured or considered for application to application (A2A) API consumers.
- Queue consumers that horizontally scale do not have maximum concurrency settings configured.
- Rate limiting on a per IP address basis has not been implemented.

## Implementation Guidance
 Services should be designed to process a known capacity of requests; this capacity can be established through load testing. If request arrival rates exceed limits, the appropriate response signals that a request has been throttled. This allows the consumer to handle the error and retry later.

 When your service requires a throttling implementation, consider implementing the token bucket algorithm, where a token counts for a request. Tokens are refilled at a throttle rate per second and emptied asynchronously by one token per request.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/token-bucket-algorithm.png)

 [Amazon API Gateway](https://aws.amazon.com/api-gateway/) implements the token bucket algorithm according to account and region limits and can be configured per-client with usage plans. Additionally, [Amazon Simple Queue Service (Amazon SQS)](https://aws.amazon.com/sqs/) and [Amazon Kinesis](https://aws.amazon.com/kinesis/) can buffer requests to smooth out the request rate, and allow higher throttling rates for requests that can be addressed. Finally, you can implement rate limiting with [AWS WAF](https://aws.amazon.com/waf/) to throttle specific API consumers that generate unusually high load.

## Implementation Steps
 You can configure API Gateway with throttling limits for your APIs and return `429 Too Many Requests` errors when limits are exceeded. You can use AWS WAF with your AWS AppSync and API Gateway endpoints to enable rate limiting on a per IP address basis. Additionally, where your system can tolerate asynchronous processing, you can put messages into a queue or stream to speed up responses to service clients, which allows you to burst to higher throttle rates.

 With asynchronous processing, when you’ve configured Amazon SQS as an event source for AWS Lambda, you can [configure maximum concurrency](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html#events-sqs-max-concurrency) to avoid high event rates from consuming available account concurrent execution quota needed for other services in your workload or account.

 While API Gateway provides a managed implementation of the token bucket, in cases where you cannot use API Gateway, you can take advantage of language specific open-source implementations (see related examples in Resources) of the token bucket for your services.
- Understand and configure [API Gateway throttling limits](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html) at the account level per region, API per stage, and API key per usage plan levels.
- Apply [AWS WAF rate limiting rules](https://aws.amazon.com/blogs/security/three-most-important-aws-waf-rate-based-rules/) to API Gateway and AWS AppSync endpoints to protect against floods and block malicious IPs. Rate limiting rules can also be configured on AWS AppSync API keys for A2A consumers.
- Consider whether you require more throttling control than rate limiting for AWS AppSync APIs, and if so, configure an API Gateway in front of your AWS AppSync endpoint.
- When Amazon SQS queues are set up as triggers for Lambda queue consumers, set [maximum concurrency](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html#events-sqs-max-concurrency) to a value that processes enough to meet your service level objectives but does not consume concurrency limits impacting other Lambda functions. Consider setting reserved concurrency on other Lambda functions in the same account and region when you consume queues with Lambda.
- Use API Gateway with native service integrations to Amazon SQS or Kinesis to buffer requests.
- If you cannot use API Gateway, look at language specific libraries to implement the token bucket algorithm for your workload. Check the examples section and do your own research to find a suitable library.
- Test limits that you plan to set, or that you plan to allow to be increased, and document the tested limits.
- Do not increase limits beyond what you establish in testing. When increasing a limit, verify that provisioned resources are already equivalent to or greater than those in test scenarios before applying the increase.

## Resources
### Related Best Practices
- [REL04-BP03 Do constant work](rel_prevent_interaction_failure_constant_work.md)
- [REL05-BP03 Control and limit retry calls](rel_mitigate_interaction_failure_limit_retries.md)
### Related Documents
- [Amazon API Gateway: Throttle API Requests for Better Throughput](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)
- [AWS WAF: Rate-based rule statement ](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based.html)
- [ Introducing maximum concurrency of AWS Lambda when using Amazon SQS as an event source ](https://aws.amazon.com/blogs/compute/introducing-maximum-concurrency-of-aws-lambda-functions-when-using-amazon-sqs-as-an-event-source/)
- [AWS Lambda: Maximum Concurrency ](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html#events-sqs-max-concurrency)
### Related Examples
- [ The three most important AWS WAF rate-based rules ](https://aws.amazon.com/blogs/security/three-most-important-aws-waf-rate-based-rules/)
- [ Java Bucket4j ](https://github.com/bucket4j/bucket4j)
- [ Python token-bucket ](https://pypi.org/project/token-bucket/)
- [ Node token-bucket ](https://www.npmjs.com/package/tokenbucket)
- [ .NET System Threading Rate Limiting ](https://www.nuget.org/packages/System.Threading.RateLimiting)
### Related Videos
- [ Implementing GraphQL API security best practices with AWS AppSync](https://www.youtube.com/watch?v=1ASMLeJ_15U)
### Related Tools
- [ Amazon API Gateway ](https://aws.amazon.com/api-gateway/)
- [AWS AppSync](https://aws.amazon.com/appsync/)
- [ Amazon SQS ](https://aws.amazon.com/sqs/)
- [ Amazon Kinesis ](https://aws.amazon.com/kinesis/)
- [AWS WAF](https://aws.amazon.com/waf/)
- [ Virtual Waiting Room on AWS](https://aws.amazon.com/solutions/implementations/virtual-waiting-room-on-aws/)
