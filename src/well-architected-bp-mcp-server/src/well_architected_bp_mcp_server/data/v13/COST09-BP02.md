---
id: "COST09-BP02"
title: "Implement a buffer or throttle to manage demand"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you manage demand, and supply resources?"
risk_level: "Medium"
---

# COST09-BP02 Implement a buffer or throttle to manage demand

## Implementation Guidance
 Implementing a buffer or throttle is crucial in cloud computing in order to manage demand and reduce the provisioned capacity required for your workload. For optimal performance, it's essential to gauge the total demand, including peaks, the pace of change in requests, and the necessary response time. When clients have the ability to resend their requests, it becomes practical to apply throttling. Conversely, for clients lacking retry functionalities, the ideal approach is implementing a buffer solution. Such buffers streamline the influx of requests and optimize the interaction of applications with varied operational speeds.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/provisioned-capacity-1.png)

 Assume a workload with the demand curve shown in preceding image. This workload has two peaks, and to handle those peaks, the resource capacity as shown by orange line is provisioned. The resources and energy used for this workload are not indicated by the area under the demand curve, but the area under the provisioned capacity line, as provisioned capacity is needed to handle those two peaks. Flattening the workload demand curve can help you to reduce the provisioned capacity for a workload and reduce its environmental impact. To smooth out the peak, consider to implement throttling or buffering solution.

 To understand them better, let’s explore throttling and buffering.

 **Throttling:** If the source of the demand has retry capability, then you can implement throttling. Throttling tells the source that if it cannot service the request at the current time, it should try again later. The source waits for a period of time, and then retries the request. Implementing throttling has the advantage of limiting the maximum amount of resources and costs of the workload. In AWS, you can use [Amazon API Gateway](https://aws.amazon.com/api-gateway/) to implement throttling.

 **Buffer based:** A buffer-based approach uses *producers* (components that send messages to the queue), *consumers* (components that receive messages from the queue), and a *queue* (which holds messages) to store the messages. Messages are read by consumers and processed, allowing the messages to run at the rate that meets the consumers’ business requirements. By using a buffer-centric methodology, messages from producers are housed in queues or streams, ready to be accessed by consumers at a pace that aligns with their operational demands.

In AWS, you can choose from multiple services to implement a buffering approach. [Amazon Simple Queue Service(Amazon SQS)](https://aws.amazon.com/sqs/) is a managed service that provides queues that allow a single consumer to read individual messages. [Amazon Kinesis](https://aws.amazon.com/kinesis/) provides a stream that allows many consumers to read the same messages.

 Buffering and throttling can smooth out any peaks by modifying the demand on your workload. Use throttling when clients retry actions and use buffering to hold the request and process it later. When working with a buffer-based approach, architect your workload to service the request in the required time, verify that you are able to handle duplicate requests for work. Analyze the overall demand, rate of change, and required response time to right size the throttle or buffer required.

## Implementation Steps
- ** Analyze the client requirements:** Analyze the client requests to determine if they are capable of performing retries. For clients that cannot perform retries, buffers need to be implemented. Analyze the overall demand, rate of change, and required response time to determine the size of throttle or buffer required.
- ** Implement a buffer or throttle:** Implement a buffer or throttle in the workload. A queue such as Amazon Simple Queue Service (Amazon SQS) can provide a buffer to your workload components. Amazon API Gateway can provide throttling for your workload components.

## Resources
### Related Best Practices
- [ SUS02-BP06 Implement buffering or throttling to flatten the demand curve ](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_user_a7.html)
- [ REL05-BP02 Throttle requests ](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_throttle_requests.html)
### Related Documents
- [AWS Auto Scaling](https://aws.amazon.com/autoscaling/)
- [AWS Instance Scheduler](https://aws.amazon.com/answers/infrastructure-management/instance-scheduler/)
- [Amazon API Gateway](https://aws.amazon.com/api-gateway/)
- [Amazon Simple Queue Service](https://aws.amazon.com/sqs/)
- [Getting started with Amazon SQS](https://aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-getting-started.html)
- [Amazon Kinesis](https://aws.amazon.com/kinesis/)
### Related Videos
- [ Choosing the Right Messaging Service for Your Distributed App ](https://www.youtube.com/watch?v=4-JmX6MIDDI)
### Related Examples
- [ Managing and monitoring API throttling in your workloads ](https://aws.amazon.com/blogs/mt/managing-monitoring-api-throttling-in-workloads/)
- [ Throttling a tiered, multi-tenant REST API at scale using API Gateway ](https://aws.amazon.com/blogs/architecture/throttling-a-tiered-multi-tenant-rest-api-at-scale-using-api-gateway-part-1/)
- [ Enabling Tiering and Throttling in a Multi-Tenant Amazon EKS SaaS Solution Using Amazon API Gateway ](https://aws.amazon.com/blogs/apn/enabling-tiering-and-throttling-in-a-multi-tenant-amazon-eks-saas-solution-using-amazon-api-gateway/)
- [ Application integration Using Queues and Messages ](https://aws.amazon.com/blogs/architecture/application-integration-using-queues-and-messages/)
