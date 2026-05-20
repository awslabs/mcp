---
id: "COST04-BP04"
title: "Decommission resources automatically"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you decommission resources?"
risk_level: "Low"
---

# COST04-BP04 Decommission resources automatically

## Implementation Guidance
Use automation to reduce or remove the associated costs of the decommissioning process. Designing your workload to perform automated decommissioning will reduce the overall workload costs during its lifetime. You can use [Amazon EC2 Auto Scaling](https://aws.amazon.com/ec2/autoscaling/) or [Application Auto Scaling](https://docs.aws.amazon.com/autoscaling/application/userguide) to perform the decommissioning process. You can also implement custom code using the [API or SDK](https://aws.amazon.com/developer/tools/) to decommission workload resources automatically.

 [Modern applications](https://aws.amazon.com/modern-apps/) are built serverless-first, a strategy that prioritizes the adoption of serverless services. AWS developed [serverless services](https://aws.amazon.com/serverless/) for all three layers of your stack: compute, integration, and data stores. Using serverless architecture will allow you to save costs during low-traffic periods with scaling up and down automatically.

## Implementation Steps
- ** Implement Amazon EC2 Auto Scaling or Application Auto Scaling:** For resources that are supported, configure them with Amazon EC2 Auto Scaling or Application Auto Scaling. These services can help you optimize your utilization and cost efficiencies when consuming AWS services. When demand drops, these services will automatically remove any excess resource capacity so you avoid overspending.
- ** Configure CloudWatch to terminate instances:** Instances can be configured to terminate using [CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/UsingAlarmActions.html#AddingTerminateActions). Using the metrics from the decommissioning process, implement an alarm with an Amazon Elastic Compute Cloud action. Verify the operation in a non-production environment before rolling out.
- **Implement code within the workload:** You can use the AWS SDK or AWS CLI to decommission workload resources. Implement code within the application that integrates with AWS and terminates or removes resources that are no longer used.
- **Use serverless services:** Prioritize building [serverless architectures](https://aws.amazon.com/serverless/) and [event-driven architecture](https://aws.amazon.com/event-driven-architecture/) on AWS to build and run your applications. AWS offers multiple serverless technology services that inherently provide automatically optimized resource utilization and automated decommissioning (scale in and scale out). With serverless applications, resource utilization is automatically optimized and you never pay for over-provisioning.

## Resources
### Related Documents
- [Amazon EC2 Auto Scaling](https://aws.amazon.com/ec2/autoscaling/)
- [Getting Started with Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/GettingStartedTutorial.html)
- [Application Auto Scaling](https://docs.aws.amazon.com/autoscaling/application/userguide)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/trustedadvisor/)
- [Serverless on AWS](https://aws.amazon.com/serverless/)
- [Create Alarms to Stop, Terminate, Reboot, or Recover an Instance](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/UsingAlarmActions.html)
- [Adding terminate actions to Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/UsingAlarmActions.html#AddingTerminateActions)
### Related Examples
- [Scheduling automatic deletion of AWS CloudFormation stacks](https://aws.amazon.com/blogs/infrastructure-and-automation/scheduling-automatic-deletion-of-aws-cloudformation-stacks/)
