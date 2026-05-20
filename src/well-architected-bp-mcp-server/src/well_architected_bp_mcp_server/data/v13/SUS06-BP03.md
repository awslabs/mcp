---
id: "SUS06-BP03"
title: "Keep your workload up-to-date"
framework: "WAF"
domain: "Sustainability"
capability: "How do your organizational processes support your sustainability goals?"
risk_level: "Low"
---

# SUS06-BP03 Keep your workload up-to-date

## Anti-Patterns
- You assume your current architecture is static and will not be updated over time.
- You do not have any systems or a regular cadence to evaluate if updated software and packages are compatible with your workload.

## Implementation Guidance
 Up to date operating systems, runtimes, middlewares, libraries, and applications can improve workload efficiency and make it easier to adopt more efficient technologies. Up to date software might also include features to measure the sustainability impact of your workload more accurately, as vendors deliver features to meet their own sustainability goals. Adopt a regular cadence to keep your workload up to date with the latest features and releases.

## Implementation Steps
- **Define a process:** Use a process and schedule to evaluate new features or instances for your workload. Take advantage of agility in the cloud to quickly test how new features can improve your workload to:
  - Reduce sustainability impacts.
  - Gain performance efficiencies.
  - Remove barriers for a planned improvement.
  - Improve your ability to measure and manage sustainability impacts.
- **Conduct an inventory:** Inventory your workload software and architecture and identify components that need to be updated.
  - You can use [AWS Systems Manager Inventory](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-inventory.html) to collect operating system (OS), application, and instance metadata from your Amazon EC2 instances and quickly understand which instances are running the software and configurations required by your software policy and which instances need to be updated.
- **Learn the update procedure:** Understand how to update the components of your workload.

|  Workload component  |  How to update  |
| --- | --- |
|  Machine images  |  Use [EC2 Image Builder](https://aws.amazon.com/image-builder/) to manage updates to [Amazon Machine Images (AMIs)](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html) for Linux or Windows server images.  |
|  Container images  |  Use [Amazon Elastic Container Registry (Amazon ECR)](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html) with your existing pipeline to [manage Amazon Elastic Container Service (Amazon ECS) images](https://docs.aws.amazon.com/AmazonECR/latest/userguide/ECR_on_ECS.html).  |
|  AWS Lambda  |  AWS Lambda includes [version management features.](https://docs.aws.amazon.com/lambda/latest/dg/configuration-versions.html)  |
- **Use automation:** Automate updates to reduce the level of effort to deploy new features and limit errors caused by manual processes.
  - You can use [CI/CD](https://aws.amazon.com/blogs/devops/complete-ci-cd-with-aws-codecommit-aws-codebuild-aws-codedeploy-and-aws-codepipeline/) to automatically update AMIs, container images, and other artifacts related to your cloud application.
  - You can use tools such as [AWS Systems Manager Patch Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-patch.html) to automate the process of system updates, and schedule the activity using [AWS Systems Manager Maintenance Windows](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-maintenance.html).

## Resources
### Related Documents
- [AWS Architecture Center](https://aws.amazon.com/architecture)
- [What's New with AWS](https://aws.amazon.com/new/?ref=wellarchitected&ref=wellarchitected)
- [AWS Developer Tools](https://aws.amazon.com/products/developer-tools/)
### Related Videos
- [AWS re:Invent 2022 - Optimize your AWS workloads with best-practice guidance](https://www.youtube.com/watch?v=t8yl1TrnuIk)
- [All Things Patch: AWS Systems Manager](https://www.youtube.com/watch?v=PhIiVsCEBu8)
