---
id: "REL05-BP05"
title: "Set client timeouts"
framework: "WAF"
domain: "Reliability"
capability: "How do you design interactions in a distributed system to mitigate or withstand failures?"
risk_level: "High"
---

# REL05-BP05 Set client timeouts

## Desired Outcome
Client timeouts should consider the cost to the client, server, and workload associated with waiting for requests that take abnormal amounts of time to complete. Since it is not possible to know the exact cause of any timeout, clients must use knowledge of services to develop expectations of probable causes and appropriate timeouts

 Client connections time out based on configured values. After encountering a timeout, clients make decisions to back off and retry or open a [circuit breaker](https://martinfowler.com/bliki/CircuitBreaker.html). These patterns avoid issuing requests that may exacerbate an underlying error condition.

## Anti-Patterns
- Not being aware of system timeouts or default timeouts.
- Not being aware of normal request completion timing.
- Not being aware of possible causes for requests to take abnormally long to complete, or the costs to client, service, or workload performance associated with waiting on these completions.
- Not being aware of the probability of impaired network causing a request to fail only once timeout is reached, and the costs to client and workload performance for not adopting a shorter timeout.
- Not testing timeout scenarios both for connections and requests.
- Setting timeouts too high, which can result in long wait times and increase resource utilization.
- Setting timeouts too low, resulting in artificial failures.
- Overlooking patterns to deal with timeout errors for remote calls like circuit breakers and retries.
- Not considering monitoring for service call error rates, service level objectives for latency, and latency outliers. These metrics can provide insight to aggressive or permissive timeouts

## Implementation Guidance
 Set both a connection timeout and a request timeout on any service dependency call and generally on any call across processes. Many frameworks offer built-in timeout capabilities, but be careful, as some have default values that are infinite or higher than acceptable for your service goals. A value that is too high reduces the usefulness of the timeout because resources continue to be consumed while the client waits for the timeout to occur. A value that is too low can generate increased traffic on the backend and increased latency because too many requests are retried. In some cases, this can lead to complete outages because all requests are being retried.

 Consider the following when determining timeout strategies:
- Requests may take longer than normal to process because of their content, impairments in a target service, or a networking partition failure.
- Requests with abnormally expensive content could consume unnecessary server and client resources. In this case, timing out these requests and not retrying can preserve resources. Services should also protect themselves from abnormally expensive content with throttles and server-side timeouts.
- Requests that take abnormally long due to a service impairment can be timed out and retried. Consideration should be given to service costs for the request and retry, but if the cause is a localized impairment, a retry is not likely to be expensive and will reduce client resource consumption. The timeout may also release server resources depending on the nature of the impairment.
- Requests that take a long time to complete because the request or response has failed to be delivered by the network can be timed out and retried. Because the request or response was not delivered, failure would have been the outcome regardless of the length of timeout. Timing out in this case will not release server resources, but it will release client resources and improve workload performance.

 Take advantage of well-established design patterns like retries and circuit breakers to handle timeouts gracefully and support fail-fast approaches. [AWS SDKs](https://docs.aws.amazon.com/index.html#sdks) and [AWS CLI](https://aws.amazon.com/cli/) allow for configuration of both connection and request timeouts and for retries with exponential backoff and jitter. [AWS Lambda](https://aws.amazon.com/lambda/) functions support configuration of timeouts, and with [AWS Step Functions](https://aws.amazon.com/step-functions/), you can build low code circuit breakers that take advantage of pre-built integrations with AWS services and SDKs. [AWS App Mesh](https://aws.amazon.com/app-mesh/) Envoy provides timeout and circuit breaker capabilities.

## Implementation Steps
- Configure timeouts on remote service calls and take advantage of built-in language timeout features or open source timeout libraries.
- When your workload makes calls with an AWS SDK, review the documentation for language specific timeout configuration.
  - [ Python ](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html)
  - [ PHP ](https://docs.aws.amazon.com/aws-sdk-php/v3/api/class-Aws.DefaultsMode.Configuration.html)
  - [ .NET ](https://docs.aws.amazon.com/sdk-for-net/v3/developer-guide/retries-timeouts.html)
  - [ Ruby ](https://docs.aws.amazon.com/sdk-for-ruby/v3/developer-guide/timeout-duration.html)
  - [ Java ](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/best-practices.html#bestpractice5)
  - [ Go ](https://aws.github.io/aws-sdk-go-v2/docs/configuring-sdk/retries-timeouts/#timeouts)
  - [ Node.js ](https://docs.aws.amazon.com/AWSJavaScriptSDK/latest/AWS/Config.html)
  - [ C\$1\$1 ](https://docs.aws.amazon.com/sdk-for-cpp/v1/developer-guide/client-config.html)
- When using AWS SDKs or AWS CLI commands in your workload, configure default timeout values by setting the AWS [configuration defaults](https://docs.aws.amazon.com/sdkref/latest/guide/feature-smart-config-defaults.html) for `connectTimeoutInMillis` and `tlsNegotiationTimeoutInMillis`.
- Apply [command line options](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-options.html) `cli-connect-timeout` and `cli-read-timeout` to control one-off AWS CLI commands to AWS services.
- Monitor remote service calls for timeouts, and set alarms on persistent errors so that you can proactively handle error scenarios.
- Implement [CloudWatch Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html) and [CloudWatch anomaly detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html) on call error rates, service level objectives for latency, and latency outliers to provide insight into managing overly aggressive or permissive timeouts.
- Configure timeouts on [Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/configuration-function-common.html#configuration-timeout-console).
- API Gateway clients must implement their own retries when handling timeouts. API Gateway supports a [50 millisecond to 29 second integration timeout](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html#api-gateway-execution-service-limits-table) for downstream integrations and does not retry when integration requests timeout.
- Implement the [circuit breaker](https://martinfowler.com/bliki/CircuitBreaker.html) pattern to avoid making remote calls when they are timing out. Open the circuit to avoid failing calls and close the circuit when calls are responding normally.
- For container based workloads, review [App Mesh Envoy](https://docs.aws.amazon.com/app-mesh/latest/userguide/envoy.html) features to leverage built in timeouts and circuit breakers.
- Use AWS Step Functions to build low code circuit breakers for remote service calls, especially where calling AWS native SDKs and supported Step Functions integrations to simplify your workload.

## Resources
### Related Best Practices
- [REL05-BP03 Control and limit retry calls](rel_mitigate_interaction_failure_limit_retries.md)
- [REL05-BP04 Fail fast and limit queues](rel_mitigate_interaction_failure_fail_fast.md)
- [REL06-BP07 Monitor end-to-end tracing of requests through your system](rel_monitor_aws_resources_end_to_end.md)
### Related Documents
- [AWS SDK: Retries and Timeouts](https://docs.aws.amazon.com/sdk-for-net/v3/developer-guide/retries-timeouts.html)
- [The Amazon Builders' Library: Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [ Amazon API Gateway quotas and important notes ](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html)
- [AWS Command Line Interface: Command line options ](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-options.html)
- [AWS SDK for Java 2.x: Configure API Timeouts ](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/best-practices.html#bestpractice5)
- [AWS Botocore using the config object and Config Reference ](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#using-the-config-object)
- [AWS SDK for .NET: Retries and Timeouts ](https://docs.aws.amazon.com/sdk-for-net/v3/developer-guide/retries-timeouts.html)
- [AWS Lambda: Configuring Lambda function options ](https://docs.aws.amazon.com/lambda/latest/dg/configuration-function-common.html)
### Related Examples
- [ Using the circuit breaker pattern with AWS Step Functions and Amazon DynamoDB ](https://aws.amazon.com/blogs/compute/using-the-circuit-breaker-pattern-with-aws-step-functions-and-amazon-dynamodb/)
- [ Martin Fowler: CircuitBreaker ](https://martinfowler.com/bliki/CircuitBreaker.html?ref=wellarchitected)
### Related Tools
- [AWS SDKs ](https://docs.aws.amazon.com/index.html#sdks)
- [AWS Lambda](https://aws.amazon.com/lambda/)
- [ Amazon SQS ](https://aws.amazon.com/sqs/)
- [AWS Step Functions](https://aws.amazon.com/step-functions/)
- [AWS Command Line Interface](https://aws.amazon.com/cli/)
