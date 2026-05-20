---
id: "SUS05-BP04"
title: "Optimize your use of hardware-based compute accelerators"
framework: "WAF"
domain: "Sustainability"
capability: "How do you select and use cloud hardware and services in your architecture to support your sustainability goals?"
risk_level: "Medium"
---

# SUS05-BP04 Optimize your use of hardware-based compute accelerators

## Anti-Patterns
- You are not monitoring GPU usage.
- You are using a general-purpose instance for workload while a purpose-built instance can deliver higher performance, lower cost, and better performance per watt.
- You are using hardware-based compute accelerators for tasks where they’re more efficient using CPU-based alternatives.

## Implementation Guidance
 If you require high processing capability, you can benefit from using accelerated computing instances, which provide access to hardware-based compute accelerators such as graphics processing units (GPUs) and field programmable gate arrays (FPGAs). These hardware accelerators perform certain functions like graphic processing or data pattern matching more efficiently than CPU-based alternatives. Many accelerated workloads, such as rendering, transcoding, and machine learning, are highly variable in terms of resource usage. Only run this hardware for the time needed, and decommission them with automation when not required to minimize resources consumed.

## Implementation Steps
- **Explore compute accelerators:** Identify which [accelerated computing instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/accelerated-computing-instances.html) can address your requirements.
- **Use purpose-built hardware:** For machine learning workloads, take advantage of purpose-built hardware that is specific to your workload, such as [AWS Trainium](https://aws.amazon.com/machine-learning/trainium/), [AWS Inferentia](https://aws.amazon.com/machine-learning/inferentia/), and [Amazon EC2 DL1](https://aws.amazon.com/ec2/instance-types/dl1/). AWS Inferentia instances such as Inf2 instances offer up to [50% better performance per watt over comparable Amazon EC2 instances](https://aws.amazon.com/machine-learning/inferentia/).
- **Monitor usage metrics:** Collect usage metric for your accelerated computing instances. For example, you can use CloudWatch agent to collect metrics such as `utilization_gpu` and `utilization_memory` for your GPUs as shown in [Collect NVIDIA GPU metrics with Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-NVIDIA-GPU.html).
- **Rightsize:** Optimize the code, network operation, and settings of hardware accelerators to make sure that underlying hardware is fully utilized.
  - [Optimize GPU settings](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/optimize_gpu.html)
  - [GPU Monitoring and Optimization in the Deep Learning AMI](https://docs.aws.amazon.com/dlami/latest/devguide/tutorial-gpu.html)
  - [Optimizing I/O for GPU performance tuning of deep learning training in Amazon SageMaker AI](https://aws.amazon.com/blogs/machine-learning/optimizing-i-o-for-gpu-performance-tuning-of-deep-learning-training-in-amazon-sagemaker/)
- **Keep up to date:** Use the latest high performant libraries and GPU drivers.
- **Release unneeded instances:** Use automation to release GPU instances when not in use.

## Resources
### Related Documents
- [Accelerated Computing](https://aws.amazon.com/ec2/instance-types/#Accelerated_Computing)
- [ Let's Architect\$1 Architecting with custom chips and accelerators ](https://aws.amazon.com/blogs/architecture/lets-architect-custom-chips-and-accelerators/)
- [ How do I choose the appropriate Amazon EC2 instance type for my workload? ](https://aws.amazon.com/premiumsupport/knowledge-center/ec2-instance-choose-type-for-workload/)
- [Amazon EC2 VT1 Instances](https://aws.amazon.com/ec2/instance-types/vt1/)
- [ Choose the best AI accelerator and model compilation for computer vision inference with Amazon SageMaker AI ](https://aws.amazon.com/blogs/machine-learning/choose-the-best-ai-accelerator-and-model-compilation-for-computer-vision-inference-with-amazon-sagemaker/)
### Related Videos
- [AWS re:Invent 2021 - How to select Amazon EC2 GPU instances for deep learning ](https://www.youtube.com/watch?v=4bVrIbgGWEA)
- [AWS Online Tech Talks - Deploying Cost-Effective Deep Learning Inference](https://www.youtube.com/watch?v=WiCougIDRsw)
- [AWS re:Invent 2023 - Cutting-edge AI with AWS and NVIDIA](https://www.youtube.com/watch?v=ud4-z_sb_ps)
- [AWS re:Invent 2022 - [NEW LAUNCH\$1] Introducing AWS Inferentia2-based Amazon EC2 Inf2 instances](https://www.youtube.com/watch?v=jpqiG02Y2H4)
- [AWS re:Invent 2022 - Accelerate deep learning and innovate faster with AWS Trainium](https://www.youtube.com/watch?v=YRqvfNwqUIA)
- [AWS re:Invent 2022 - Deep learning on AWS with NVIDIA: From training to deployment](https://www.youtube.com/watch?v=l8AFfaCkp0E)
