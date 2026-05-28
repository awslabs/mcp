---
id: "REL04-BP01"
title: "Identify the kind of distributed systems you depend on"
framework: "WAF"
domain: "Reliability"
capability: "How do you design interactions in a distributed system to prevent failures?"
risk_level: "High"
---

# REL04-BP01 Identify the kind of distributed systems you depend on

## Anti-Patterns
- Workload waits indefinitely for a response from its dependencies, which could lead to workload clients timing out, not knowing if their request has been received.
- Workload uses a chain of dependent systems that call each other synchronously. This requires each system to be available and to successfully process a request before the whole chain can succeed, leading to potentially brittle behavior and overall availability.
- Workload communicates with its dependencies asynchronously and rely on the concept of exactly-once guaranteed delivery of messages, when often it is still possible to receive duplicate messages.
- Workload does not use proper batch scheduling tools and allows concurrent execution of the same batch job.

## Implementation Guidance
 The following sections contain both general and specific implementation guidance for each kind of dependency.

 **General guidance**
- Make sure that the performance and reliability service-level objectives (SLOs) that your dependencies offer meet the performance and reliability requirements of your workload.
- Use [AWS observability services](https://aws.amazon.com/cloudops/monitoring-and-observability) to [monitor response times and error rates](https://www.youtube.com/watch?v=or7uFFyHIX0) to make sure your dependency is providing service at the levels needed by your workload.
- Identify the potential challenges that your workload may face when communicating with its dependencies. Distributed systems [come with a wide range of challenges](https://aws.amazon.com/builders-library/challenges-with-distributed-systems/) that might increase architectural complexity, operational burden, and cost. Common challenges include latency, network disruptions, data loss, scaling, and data replication lag.
- Implement robust error handling and [logging](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html) to help you troubleshoot problems when your dependency experiences issues.

 **Synchronous dependency**

 In synchronous communications, your workload sends a request to its dependency and blocks the operation waiting for a response. When its dependency receives the request, it tries to handle it as soon as possible and sends a response back to your workload. A significant challenge with synchronous communication is that it causes temporal coupling, which requires your workload and its dependencies to be available at the same time. When your workload needs to communicate synchronously with its dependencies, consider the following guidance:
- Your workload should not rely on multiple synchronous dependencies to perform a single function. This chain of dependencies increases overall brittleness because all dependencies in the pathway need to be available in order for the request to complete successfully.
- When a dependency is unhealthy or unavailable, determine your error handling and retry strategies. Avoid using bimodal behavior. Bimodal behavior is when your workload exhibits different behavior under normal and failure modes. For more details on bimodal behavior, see [REL11-BP05 Use static stability to prevent bimodal behavior.](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_static_stability.html)
- Keep in mind that failing fast is better than making your workload wait. For instance, the [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/invocation-retries.html) describes how to handle retries and failures when you invoke Lambda functions.
- Set timeouts when your workload calls its dependency. This technique avoids waiting too long or waiting indefinitely for a response. For helpful discussion of this issue, see [Tuning AWS Java SDK HTTP request settings for latency-aware Amazon DynamoDB applications](https://aws.amazon.com/blogs/database/tuning-aws-java-sdk-http-request-settings-for-latency-aware-amazon-dynamodb-applications/).
- Minimize the number of calls made from your workload to its dependency to fulfill a single request. Having chatty calls between them increases coupling and latency.

 **Asynchronous dependency**

 To temporally decouple your workload from its dependency, they should communicate asynchronously. Using an asynchronous approach, your workload can continue with any other processing without having to wait for its dependency, or chain of dependencies, to send a response.

 When your workload needs to communicate asynchronously with its dependency, consider the following guidance:
- Determine whether to use messaging or event streaming based on your use case and requirements. [Messaging](https://aws.amazon.com/messaging/) allows your workload to communicate with its dependency by sending and receiving messages through a message broker. [Event streaming](https://aws.amazon.com/streaming-data/) allows your workload and its dependency to use a streaming service to publish and subscribe to events, delivered as continuous streams of data, that need to be processed as soon as possible.
- Messaging and event streaming handle messages differently so you need to make trade-off decisions based on:
  - **Message priority:** message brokers can process high-priority messages ahead of normal messages. In event streaming, all messages have the same priority.
  - **Message consumption**: message brokers ensure that consumers receive the message. Event streaming consumers must keep track of the last message they have read.
  - **Message ordering**: with messaging, receiving messages in the exact order they are sent is not guaranteed unless you use a first-in-first-out (FIFO) approach. Event streaming always preserves the order in which the data was produced.
  - **Message deletion**: with messaging, the consumer must delete the message after processing it. The event streaming service appends the message to a stream and remains in there until the message's retention period expires. This deletion policy makes event streaming suitable for replaying messages.
- Define how your workload knows when its dependency completes its work. For instance, when your workload invokes a [Lambda function asynchronously](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html), Lambda places the event in a queue and returns a success response without additional information. After processing is complete, the Lambda function can [send the result to a destination](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html#invocation-async-destinations), configurable based on success or failure.
- Build your workload to handle duplicate messages by leveraging idempotency. Idempotency means that the results of your workload do not change even if your workload is generated more than once for the same message. It is important to point out that [messaging](https://aws.amazon.com/sqs/faqs/#FIFO_queues) or [streaming](https://docs.aws.amazon.com/streams/latest/dev/kinesis-record-processor-duplicates.html) services will redeliver a message if a network failure occurs or if an acknowledgement has not been received.
- If your workload does not get a response from its dependency, it needs to resubmit the request. Consider limiting the number of retries to preserve your workload's CPU, memory, and network resources to handle other requests. The [AWS Lambda documentation](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html#invocation-async-errors) shows how to handle errors for asynchronous invocation.
- Leverage suitable observability, debugging, and tracing tools to manage and operate your workload's asynchronous communication with its dependency. You can use [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) to monitor [messaging](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html) and [event streaming](https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html) services. You can also instrument your workload with [AWS X-Ray](https://aws.amazon.com/xray/) to quickly [gain insights](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html) for troubleshooting problems.

 **Batch dependency**

 Batch systems take input data, initiate a series of jobs to process it, and produce some output data, without manual intervention. Depending on the data size, jobs could run from minutes to, in some cases, several days. When your workload communicates with its batch dependency, consider the following guidance:
- Define the time window when your workload should run the batch job. Your workload can set up a recurrence pattern to invoke a batch system, for example, every hour or at the end of every month.
- Determine the location of the data input and the processed data output. Choose a storage service, such as [Amazon Simple Storage Services (Amazon S3)](https://aws.amazon.com/s3/), [Amazon Elastic File System (Amazon EFS)](https://docs.aws.amazon.com/efs/latest/ug/whatisefs.html), and [Amazon FSx for Lustre](https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html), that allows your workload to read and write files at scale.
- If your workload needs to invoke multiple batch jobs, you could leverage [AWS Step Functions](https://aws.amazon.com/step-functions/?step-functions.sort-by=item.additionalFields.postDateTime&step-functions.sort-order=desc) to simplify the orchestration of batch jobs that run in AWS or on-premises. This [sample project](https://github.com/aws-samples/aws-stepfunction-complex-orchestrator-app) demonstrates orchestration of batch jobs using Step Functions, [AWS Batch](https://aws.amazon.com/batch/), and Lambda.
- Monitor batch jobs to look for abnormalities, such as a job taking longer than it should to complete. You could use tools like [CloudWatch Container Insights](https://docs.aws.amazon.com/batch/latest/userguide/cloudwatch-container-insights.html) to monitor AWS Batch environments and jobs. In this instance, your workload would stop the next job from beginning and inform the relevant staff of the exception.

## Resources
### Related Documents
- [AWS Cloud Operations: Monitoring and Observability](https://aws.amazon.com/cloudops/monitoring-and-observability)
- [The Amazon's Builder Library: Challenges with distributed systems](https://aws.amazon.com/builders-library/challenges-with-distributed-systems/)
- [REL11-BP05 Use static stability to prevent bimodal behavior](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_static_stability.html)
- [AWS Lambda Developer Guide: Error handling and automatic retries in AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/invocation-retries.html)
- [Tuning AWS Java SDK HTTP request settings for latency-aware Amazon DynamoDB applications](https://aws.amazon.com/blogs/database/tuning-aws-java-sdk-http-request-settings-for-latency-aware-amazon-dynamodb-applications/)
- [AWS Messaging](https://aws.amazon.com/messaging/)
- [What is streaming data?](https://aws.amazon.com/streaming-data/)
- [AWS Lambda Developer Guide: Asynchronous invocation](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html)
- [Amazon Simple Queue Service FAQ: FIFO queues](https://aws.amazon.com/sqs/faqs/#FIFO_queues)
- [Amazon Kinesis Data Streams Developer Guide: Handling Duplicate Records](https://docs.aws.amazon.com/streams/latest/dev/kinesis-record-processor-duplicates.html)
- [Amazon Simple Queue Service Developer Guide: Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)
- [Amazon Kinesis Data Streams Developer Guide: Monitoring the Amazon Kinesis Data Streams Service with Amazon CloudWatch](https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html)
- [AWS X-Ray Developer Guide: AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)
- [AWS Samples on GitHub: AWS Step functions Complex Orchestrator App](https://github.com/aws-samples/aws-stepfunction-complex-orchestrator-app)
- [AWS Batch User Guide: AWS Batch CloudWatch Container Insights](https://docs.aws.amazon.com/batch/latest/userguide/cloudwatch-container-insights.html)
### Related Videos
- [AWS Summit SF 2022 - Full-stack observability and application monitoring with AWS (COP310)](https://www.youtube.com/watch?v=or7uFFyHIX0)
### Related Tools
- [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/)
- [Amazon CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html)
- [AWS X-Ray](https://aws.amazon.com/xray/)
- [Amazon Simple Storage Services (Amazon S3)](https://aws.amazon.com/s3/)
- [Amazon Elastic File System (Amazon EFS)](https://docs.aws.amazon.com/efs/latest/ug/whatisefs.html)
- [Amazon FSx for Lustre](https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html)
- [AWS Step Functions](https://aws.amazon.com/step-functions/?step-functions.sort-by=item.additionalFields.postDateTime&step-functions.sort-order=desc)
- [AWS Batch](https://aws.amazon.com/batch/)
