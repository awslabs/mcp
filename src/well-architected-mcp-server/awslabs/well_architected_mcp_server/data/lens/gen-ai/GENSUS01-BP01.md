---
id: "GENSUS01-BP01"
title: "Implement auto scaling and serverless architectures to optimize resource utilization"
pillar: "Sustainability"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensus01-bp01.html"
---

# GENSUS01-BP01 Implement auto scaling and serverless architectures to optimize resource utilization

Adopt efficient and sustainable AI/ML practices to minimize resource
usage, reduce costs, and lower environmental impact. Use serverless
architectures, auto scaling, and specialized hardware to optimize
resource utilization. This approach enhances performance efficiency,
aligns with cost optimization, and supports sustainability goals.
Implementing these practices enables responsible and economical
deployment of generative AI workloads and promotes effective scaling
without unnecessary resource waste.

**Desired outcome:** After
implementing this best practice, customers can improve the
elasticity of their generative AI workloads and benefit from the
efficiencies of scale of the AWS Cloud.

**Benefits of establishing this best
practice:**
[Optimize
resource utilization](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sustainability-pillar.html) - Minimize environmental impact by
maximizing the efficiency of generative AI resources.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Adopting serverless architectures and auto-scaling capabilities is
essential for verifying that resources are provisioned and
consumed only when needed. This approach minimizes idle
consumption and reduces the associated environmental impact. While
training jobs may run overnight, the notebook and ML development
instances that are not in use can be shut down either through
configuring an idle time-out or through scheduling. You can
further enhance the efficiency of your workload's resource
utilization by using AWS managed services and managed offerings.

Amazon Bedrock and Amazon Q are fully-managed services, which
means that AWS handles the infrastructure management, scaling, and
maintenance. As a result, users can focus on model development
rather than infrastructure utilization. Similarly,
[Amazon SageMaker AI Inference Recommender](https://docs.aws.amazon.com/sagemaker/latest/dg/inference-recommender.html) helps optimize the
deployment of machine learning models by automating load testing.
It assists in selecting the best instance type by considering
factors like instance count, container parameters, and model
optimizations. This tool provides recommendations for both
real-time and serverless inference endpoints, which helps you
verify that models are deployed with the best performance at the
lowest resource consumption.

For hosting and running generative AI models efficiently, consider
using Amazon EC2 Inferentia instances. These instances deliver
some of the highest compute power and accelerator memory in among
EC2 instance families, which is crucial for handling large
language models and other generative AI workloads. Inferentia
instances support scale-out distributed inference to optimize
compute consumption. The improved performance per watt translates
to more efficient use of resources. By integrating these AWS
services and features, organizations can achieve a more
sustainable and cost-effective approach to generative AI
workloads.

In SageMaker AI HyperPod with both Amazon EKS and Slurm
orchestration, use the system's managed infrastructure
capabilities and built-in scaling mechanisms to minimize
resource waste while maintaining optimal performance.

Self-hosted models can scale to zero when not in use.
Implement scale-to-zero for periods of low-utilization,
configuring autoscaling policies to scale back up quickly
where appropriate.

### Implementation steps

- Adopt serverless or fully-managed architectures.

Use Amazon Bedrock for generative AI tasks to alleviate
server management overhead
- Use Amazon Q Business-related AI applications to
streamline operations
- Use Amazon SageMaker AI Serverless Inference for on-demand
ML inference without managing servers

- Configure auto scaling capabilities.

Set up auto scaling for Amazon SageMaker AI Endpoints to
handle varying loads efficiently
- Set up EC2 Auto Scaling for custom ML infrastructure to
match resource allocation with demand

- Optimize ML development environments.

For
[SageMaker AI
notebook instances](https://docs.aws.amazon.com/sagemaker/latest/dg/nbi.html), configure idle time-out to
release resources when not in use
- For ML development instances, schedule automatic
shutdown for unused instances to conserve resources

- Use SageMaker AI Inference Recommender.

Conduct automated load testing to assess model
deployments under various loads
- Select optimal instance types based on recommendations
for cost-effective and performance
- Consider both real-time and serverless inference

- Implement efficient model hosting.

For model deployments, consider EC2 Inferentia instances
for enhanced performance and efficiency
- For large models, scale and distribute the load across
multiple instances

- Perform continuous monitoring and optimization.

Use Amazon CloudWatch to track resource metrics and
identify optimization opportunities
- Track token lengths of prompts and model responses to
measure utilization
- Identify idle time periods to scale down or suspend the
inference endpoints
- Set up SageMaker AI Model Monitor to continuously monitor
model performance and data quality

- Educate your team on sustainable AI practices.

Provide training to foster a culture of sustainability
- Encourage the use of pre-trained models to reduce
training time and resource consumption

## Resources

**Related best practices:**

- [SUS02-BP01](https://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_user_a2.html)
- [SUS05-BP02](https://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_hardware_a3.html)
- [SUS02-BP03](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_user_a4.html)

**Related documents:**

- [Sustainability pillar – Best practices](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/sustainability-pillar-best-practices-5.html)
- [Automatic
scaling of Amazon SageMaker AI models](https://docs.aws.amazon.com/sagemaker/latest/dg/endpoint-auto-scaling.html)
- [Amazon SageMaker AI Best Practices](https://docs.aws.amazon.com/sagemaker/latest/dg/best-practices.html)
- [Deploy
models with Amazon SageMaker AI Serverless Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoints.html)
- [Optimizing Costs for Machine Learning with Amazon SageMaker AI](https://aws.amazon.com/blogs/machine-learning/optimizing-costs-for-machine-learning-with-amazon-sagemaker/)
- [The
executive's guide to generative AI for sustainability](https://aws.amazon.com/blogs/machine-learning/the-executives-guide-to-generative-ai-for-sustainability/)
- [Optimize
generative AI workloads for environmental
sustainability](https://aws.amazon.com/blogs/machine-learning/optimize-generative-ai-workloads-for-environmental-sustainability/)
- [Integrating
generative AI effectively into sustainability
strategies](https://www.youtube.com/watch?v=8vAMOPLnN-w)
- [Optimize
your AI/ML workloads with Amazon EC2 Graviton](https://www.youtube.com/watch?v=QIAaMlW1fVo)
- [Orchestrating
SageMaker AI HyperPod clusters with Amazon](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-eks.html)
- [Orchestrating
SageMaker AI HyperPod clusters with Slurm](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-slurm.html)
- [Deploy models for inference](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html)

**Related examples:**

- [Supercharge
your auto scaling for generative AI inference – Introducing
Container Caching in SageMaker AI Inference](https://aws.amazon.com/blogs/machine-learning/supercharge-your-auto-scaling-for-generative-ai-inference-introducing-container-caching-in-sagemaker-inference/)
- [SageMaker AI
Inference Recommender Example](https://github.com/aws/amazon-sagemaker-examples/tree/main/sagemaker-inference-recommender)
- [AWS can help reduce the carbon footprint of AI workloads by up to
99%](https://www.aboutamazon.com/news/aws/aws-carbon-footprint-ai-workload)
- [Carrier Uses
Amazon Bedrock to Help Customers Achieve Their Sustainability Goals](https://aws.amazon.com/solutions/case-studies/carrier-bedrock-sustainability-testimonial/)
- [Introducing
Amazon SageMaker AI HyperPod, a purpose-built infrastructure for
distributed training at scale](https://aws.amazon.com/blogs/aws/introducing-amazon-sagemaker-hyperpod-a-purpose-built-infrastructure-for-distributed-training-at-scale/)

**Related tools:**

- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [Amazon SageMaker AI](https://aws.amazon.com/sagemaker/)
- [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/)
- [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
- [Amazon EC2 Auto Scaling](https://aws.amazon.com/ec2/autoscaling/)
- [AWS Inferentia](https://aws.amazon.com/ai/machine-learning/inferentia/)
- [New – Customer
Carbon Footprint Tool](https://aws.amazon.com/blogs/aws/new-customer-carbon-footprint-tool/)
