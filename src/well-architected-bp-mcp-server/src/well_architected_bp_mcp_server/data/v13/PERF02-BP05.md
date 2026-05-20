---
id: "PERF02-BP05"
title: "Scale your compute resources dynamically"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you select and use compute resources in your workload?"
risk_level: "High"
---

# PERF02-BP05 Scale your compute resources dynamically

## Anti-Patterns
- You react to alarms by manually increasing capacity.
- You use the same sizing guidelines (generally static infrastructure) as in on-premises.
- You leave increased capacity after a scaling event instead of scaling back down.

## Implementation Guidance
 AWS provides the flexibility to scale your resources up or down dynamically through a variety of scaling mechanisms in order to meet changes in demand. Combined with compute-related metrics, a dynamic scaling allows workloads to automatically respond to changes and use the optimal set of compute resources to achieve its goal.

 You can use a number of different approaches to match supply of resources with demand.
- **Target-tracking approach**: Monitor your scaling metric and automatically increase or decrease capacity as you need it.
- **Predictive scaling**: Scale in anticipation of daily and weekly trends.
- **Schedule-based approach**: Set your own scaling schedule according to predictable load changes.
- **Service scaling**: Choose services (like serverless) that that automatically scale by design.

 You must ensure that workload deployments can handle both scale-up and scale-down events.

## Implementation Steps
- Compute instances, containers, and functions provide mechanisms for elasticity, either in combination with autoscaling or as a feature of the service. Here are some examples of automatic scaling mechanisms:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/perf_compute_hardware_scale_compute_resources_dynamically.html)
- Scaling is often discussed related to compute services like Amazon EC2 Instances or AWS Lambda functions. Be sure to also consider the configuration of non-compute services like [AWS Glue](https://docs.aws.amazon.com/glue/latest/dg/auto-scaling.html) to match the demand.
- Verify that the metrics for scaling match the characteristics of the workload being deployed. If you are deploying a video transcoding application, 100% CPU utilization is expected and should not be your primary metric. Use the depth of the transcoding job queue instead. You can use a [customized metric](https://aws.amazon.com/blogs/mt/create-amazon-ec2-auto-scaling-policy-memory-utilization-metric-linux/) for your scaling policy if required. To choose the right metrics, consider the following guidance for Amazon EC2:
  - The metric should be a valid utilization metric and describe how busy an instance is.
  - The metric value must increase or decrease proportionally to the number of instances in the Auto Scaling group.
- Make sure that you use [dynamic scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scale-based-on-demand.html) instead of [manual scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-manual-scaling.html) for your Auto Scaling group. We also recommend that you use [target tracking scaling policies](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html) in your dynamic scaling.
- Verify that workload deployments can handle both scaling events (up and down). As an example, you can use [Activity history](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-verify-scaling-activity.html) to verify a scaling activity for an Auto Scaling group.
- Evaluate your workload for predictable patterns and proactively scale as you anticipate predicted and planned changes in demand. With predictive scaling, you can eliminate the need to overprovision capacity. For more detail, see [Predictive Scaling with Amazon EC2 Auto Scaling](https://aws.amazon.com/blogs/compute/introducing-native-support-for-predictive-scaling-with-amazon-ec2-auto-scaling/).

## Resources
### Related Documents
- [Cloud Compute with AWS](https://aws.amazon.com/products/compute/)
- [Amazon EC2 Instance Types](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html)
- [Amazon ECS Containers: Amazon ECS Container Instances](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_instances.html)
- [Amazon EKS Containers: Amazon EKS Worker Nodes](https://docs.aws.amazon.com/eks/latest/userguide/worker.html)
- [Functions: Lambda Function Configuration](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html#function-configuration)
- [Processor State Control for Your Amazon EC2 Instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/processor_state_control.html)
- [Deep Dive on Amazon ECS Cluster Auto Scaling](https://aws.amazon.com/blogs/containers/deep-dive-on-amazon-ecs-cluster-auto-scaling/)
- [Introducing Karpenter – An Open-Source High-Performance Kubernetes Cluster Autoscaler](https://aws.amazon.com/blogs/aws/introducing-karpenter-an-open-source-high-performance-kubernetes-cluster-autoscaler/)
### Related Videos
- [AWS re:Invent 2023 – AWS Graviton: The best price performance for your AWS workloads](https://www.youtube.com/watch?v=T_hMIjKtSr4)
- [AWS re:Invent 2023 – New Amazon EC2 generative AI capabilities in AWS Management Console](https://www.youtube.com/watch?v=sSpJ8tWCEiA)
- [AWS re:Invent 2023 – What’s new with Amazon EC2](https://www.youtube.com/watch?v=mjHw_wgJJ5g)
- [AWS re:Invent 2023 – Smart savings: Amazon EC2 cost-optimization strategies](https://www.youtube.com/watch?v=_AHPbxzIGV0)
- [AWS re:Invent 2021 – Powering next-gen Amazon EC2: Deep dive on the Nitro System](https://www.youtube.com/watch?v=2uc1vaEsPXU)
- [AWS re:Invent 2019 – Amazon EC2 foundations](https://www.youtube.com/watch?v=kMMybKqC2Y0)
### Related Examples
- [Amazon EC2 Auto Scaling Group Examples](https://github.com/aws-samples/amazon-ec2-auto-scaling-group-examples)
- [Amazon EKS Workshop](https://www.eksworkshop.com/)
- [Scale your Amazon EKS workloads by running on IPv6](https://catalog.us-east-1.prod.workshops.aws/workshops/3b06259f-8e17-4f2f-811a-75c9b06a2807/en-US)
