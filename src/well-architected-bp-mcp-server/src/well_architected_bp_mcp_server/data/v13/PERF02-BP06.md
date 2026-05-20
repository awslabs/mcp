---
id: "PERF02-BP06"
title: "Use optimized hardware-based compute accelerators"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you select and use compute resources in your workload?"
risk_level: "Medium"
---

# PERF02-BP06 Use optimized hardware-based compute accelerators

## Anti-Patterns
- In your workload, you haven't benchmarked a general-purpose instance against a purpose-built instance that can deliver higher performance and lower cost.
- You are using hardware-based compute accelerators for tasks that can be more efficient using CPU-based alternatives.
- You are not monitoring GPU usage.

## Implementation Guidance
 Accelerated computing instances provide access to hardware-based compute accelerators such as GPUs and FPGAs. These hardware accelerators perform certain functions like graphic processing or data pattern matching more efficiently than CPU-based alternatives. Many accelerated workloads, such as rendering, transcoding, and machine learning, are highly variable in terms of resource usage. Only run this hardware for the time needed, and decommission them with automation when not required to improve overall performance efficiency.

## Implementation Steps
- Identify which [accelerated computing instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/accelerated-computing-instances.html) can address your requirements.
- For machine learning workloads, take advantage of purpose-built hardware that is specific to your workload, such as [AWS Trainium](https://aws.amazon.com/machine-learning/trainium/), [AWS Inferentia](https://aws.amazon.com/machine-learning/inferentia/), and [Amazon EC2 DL1](https://aws.amazon.com/ec2/instance-types/dl1/). AWS Inferentia instances such as Inf2 instances [offer up to 50% better performance/watt over comparable Amazon EC2 instances](https://aws.amazon.com/machine-learning/inferentia/).
- Collect usage metrics for your accelerated computing instances. For example, you can use CloudWatch agent to collect metrics such as `utilization_gpu` and `utilization_memory` for your GPUs as shown in [Collect NVIDIA GPU metrics with Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-NVIDIA-GPU.html).
- Optimize the code, network operation, and settings of hardware accelerators to make sure that underlying hardware is fully utilized.
  - [Optimize GPU settings](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/optimize_gpu.html)
  - [GPU Monitoring and Optimization in the Deep Learning AMI](https://docs.aws.amazon.com/dlami/latest/devguide/tutorial-gpu.html)
  - [Optimizing I/O for GPU performance tuning of deep learning training in Amazon SageMaker AI](https://aws.amazon.com/blogs/machine-learning/optimizing-i-o-for-gpu-performance-tuning-of-deep-learning-training-in-amazon-sagemaker/)
- Use the latest high performant libraries and GPU drivers.
- Use automation to release GPU instances when not in use.

## Resources
### Related Documents
- [Working with GPUs on Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-gpu.html)
- [GPU instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/accelerated-computing-instances.html#gpu-instances)
- [Instances with AWS Trainium](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/accelerated-computing-instances.html#aws-trainium-instances)
- [Instances with AWS Inferentia](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/accelerated-computing-instances.html#aws-inferentia-instances)
- [Let’s Architect\$1 Architecting with custom chips and accelerators](https://aws.amazon.com/blogs/architecture/lets-architect-custom-chips-and-accelerators/)
- [Accelerated Computing](https://aws.amazon.com/ec2/instance-types/#Accelerated_Computing)
- [Amazon EC2 VT1 Instances](https://aws.amazon.com/ec2/instance-types/vt1/)
- [How do I choose the appropriate Amazon EC2 instance type for my workload?](https://aws.amazon.com/premiumsupport/knowledge-center/ec2-instance-choose-type-for-workload/)
- [Choose the best AI accelerator and model compilation for computer vision inference with Amazon SageMaker AI](https://aws.amazon.com/blogs/machine-learning/choose-the-best-ai-accelerator-and-model-compilation-for-computer-vision-inference-with-amazon-sagemaker/)
### Related Videos
- AWS re:Invent 2021 - [How to select Amazon Elastic Compute Cloud GPU instances for deep learning](https://www.youtube.com/watch?v=4bVrIbgGWEA&ab_channel=AWSEvents)
- [AWS re:Invent 2022 - [NEW LAUNCH\$1] Introducing AWS Inferentia2-based Amazon EC2 Inf2 instances](https://www.youtube.com/watch?v=jpqiG02Y2H4&ab_channel=AWSEvents)
- [AWS re:Invent 2022 - Accelerate deep learning and innovate faster with AWS Trainium](https://www.youtube.com/watch?v=YRqvfNwqUIA&ab_channel=AWSEvents)
- [AWS re:Invent 2022 - Deep learning on AWS with NVIDIA: From training to deployment](https://www.youtube.com/watch?v=l8AFfaCkp0E&ab_channel=AWSEvents)
### Related Examples
- [Amazon SageMaker AI and NVIDIA GPU Cloud (NGC)](https://github.com/aws-samples/amazon-sagemaker-nvidia-ngc-examples)
- [Use SageMaker AI with Trainium and Inferentia for optimized deep learning training and inferencing workloads](https://github.com/aws-samples/sagemaker-trainium-inferentia)
- [Optimizing NLP models with Amazon Elastic Compute Cloud Inf1 instances in Amazon SageMaker AI](https://github.com/aws-samples/aws-inferentia-huggingface-workshop)
