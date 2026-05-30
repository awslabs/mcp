---
id: "PERF02-BP01"
title: "Select the best compute options for your workload"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you select and use compute resources in your workload?"
risk_level: "High"
---

# PERF02-BP01 Select the best compute options for your workload

## Anti-Patterns
- You use the same compute option that was used on premises.
- You lack awareness of the cloud compute options, features, and solutions, and how those solutions might improve your compute performance.
- You over-provision an existing compute option to meet scaling or performance requirements when an alternative compute option would align to your workload characteristics more precisely.

## Implementation Guidance
 To optimize your cloud workloads for performance efficiency, it is important to select the most appropriate compute options for your use case and performance requirements. AWS provides a variety of compute options that cater to different workloads in the cloud. For instance, you can use [Amazon EC2](https://docs.aws.amazon.com/ec2/) to launch and manage virtual servers, [AWS Lambda](https://docs.aws.amazon.com/lambda/?icmpid=docs_homepage_featuredsvcs) to run code without having to provision or manage servers, [Amazon ECS](https://aws.amazon.com/ecs/) or [Amazon EKS](https://aws.amazon.com/eks/) to run and manage containers, or [AWS Batch](https://aws.amazon.com/batch/) to process large volumes of data in parallel. Based on your scale and compute needs, you should choose and configure the optimal compute solution for your situation. You can also consider using multiple types of compute solutions in a single workload, as each one has its own advantages and drawbacks.

 The following steps guide you through selecting the right compute options to match your workload characteristics and performance requirements.

## Implementation Steps
- Understand your workload compute requirements. Key requirements to consider include processing needs, traffic patterns, data access patterns, scaling needs, and latency requirements.
- Learn about different [AWS compute services](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/compute-services.html) for your workload. For more information, see [PERF01-BP01 Learn about and understand available cloud services and features](perf_architecture_understand_cloud_services_and_features.md). Here are some key AWS compute options, their characteristics, and common use cases:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/perf_compute_hardware_select_best_compute_options.html)
- Evaluate cost (like hourly charge or data transfer) and management overhead (like patching and scaling) associated to each compute option.
- Perform experiments and benchmarking in a non-production environment to identify which compute option can best address your workload requirements.
- Once you have experimented and identified your new compute solution, plan your migration and validate your performance metrics.
- Use AWS monitoring tools like [Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html) and optimization services like [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/) to continually optimize your compute resources based on real-world usage patterns.

## Resources
### Related Documents
- [Cloud Compute with AWS ](https://aws.amazon.com/products/compute/?ref=wellarchitected)
- [Amazon EC2 Instance Types ](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html?ref=wellarchitected)
- [Amazon EKS Containers: Amazon EKS Worker Nodes ](https://docs.aws.amazon.com/eks/latest/userguide/worker.html?ref=wellarchitected)
- [Amazon ECS Containers: Amazon ECS Container Instances ](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_instances.html?ref=wellarchitected)
- [Functions: Lambda Function Configuration](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html?ref=wellarchitected#function-configuration)
- [Prescriptive Guidance for Containers](https://aws.amazon.com/prescriptive-guidance/?apg-all-cards.sort-by=item.additionalFields.sortText&apg-all-cards.sort-order=desc&awsf.apg-new-filter=*all&awsf.apg-content-type-filter=*all&awsf.apg-code-filter=*all&awsf.apg-category-filter=categories%23containers&awsf.apg-rtype-filter=*all&awsf.apg-isv-filter=*all&awsf.apg-product-filter=*all&awsf.apg-env-filter=*all)
- [Prescriptive Guidance for Serverless](https://aws.amazon.com/prescriptive-guidance/?apg-all-cards.sort-by=item.additionalFields.sortText&apg-all-cards.sort-order=desc&awsf.apg-new-filter=*all&awsf.apg-content-type-filter=*all&awsf.apg-code-filter=*all&awsf.apg-category-filter=categories%23serverless&awsf.apg-rtype-filter=*all&awsf.apg-isv-filter=*all&awsf.apg-product-filter=*all&awsf.apg-env-filter=*all)
### Related Videos
- [AWS re:Invent 2023 - AWS Graviton: The best price performance for your AWS workloads](https://www.youtube.com/watch?v=T_hMIjKtSr4&ab_channel=AWSEvents)
- [AWS re:Invent 2023 - New Amazon Elastic Compute Cloud generative AI capabilities in AMS](https://www.youtube.com/watch?v=sSpJ8tWCEiA)
- [AWS re:Invent 2023 - What’s new with Amazon Elastic Compute Cloud](https://www.youtube.com/watch?v=mjHw_wgJJ5g)
- [AWS re:Invent 2023 - Smart savings: Amazon Elastic Compute Cloud cost-optimization strategies](https://www.youtube.com/watch?v=_AHPbxzIGV0)
- [AWS re:Invent 2021 - Powering next-gen Amazon Elastic Compute Cloud: Deep dive on the Nitro System](https://www.youtube.com/watch?v=2uc1vaEsPXU)
- [AWS re:Invent 2019 - Optimize performance and cost for your AWS compute](https://www.youtube.com/watch?v=zt6jYJLK8sg)
- [AWS re:Invent 2019 - Amazon Elastic Compute Cloud foundations](https://www.youtube.com/watch?v=kMMybKqC2Y0)
- [AWS re:Invent 2022 - Deploy ML models for inference at high performance and low cost](https://www.youtube.com/watch?v=4FqHt5bmS2o)
- [AWS re:Invent 2019 - Optimize performance and cost for your AWS compute ](https://www.youtube.com/watch?v=zt6jYJLK8sg)
- [Amazon EC2 foundations](https://www.youtube.com/watch?v=kMMybKqC2Y0)
- [Deploy ML models for inference at high performance and low cost](https://www.youtube.com/watch?v=4FqHt5bmS2o)
### Related Examples
- [Migrating the Web application to containers](https://application-migration-with-aws.workshop.aws/en/container-migration.html)
- [Run a Serverless Hello World](https://aws.amazon.com/getting-started/hands-on/run-serverless-code/)
- [Amazon EKS Workshop](https://www.eksworkshop.com/)
- [Amazon EC2 Workshop](https://ec2spotworkshops.com/)
- [Efficient and Resilient Workloads with Amazon Elastic Compute Cloud Auto Scaling](https://catalog.us-east-1.prod.workshops.aws/workshops/20c57d32-162e-4ad5-86a6-dff1f8de4b3c/en-US)
- [Migrating to AWS Graviton with Container Services](https://catalog.us-east-1.prod.workshops.aws/workshops/dcab7555-32fc-42d2-97e5-2b7a35cd008f/en-US/)
