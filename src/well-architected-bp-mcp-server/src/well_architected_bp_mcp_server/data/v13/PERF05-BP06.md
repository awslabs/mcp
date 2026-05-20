---
id: "PERF05-BP06"
title: "Keep your workload and services up-to-date"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do your organizational practices and culture contribute to performance efficiency in your workload?"
risk_level: "Low"
---

# PERF05-BP06 Keep your workload and services up-to-date

## Anti-Patterns
- You assume your current architecture is static and will not be updated over time.
- You do not have any systems or a regular cadence to evaluate if updated software and packages are compatible with your workload.

## Implementation Guidance
 Evaluate ways to improve performance as new services, design patterns, and product features become available. Determine which of these could improve performance or increase the efficiency of the workload through evaluation, internal discussion, or external analysis. Define a process to evaluate updates, new features, and services relevant to your workload. For example, build a proof of concept that uses new technologies or consult with an internal group. When trying new ideas or services, run performance tests to measure the impact that they have on the performance of the workload.

## Implementation Steps
- **Inventory your workload:** Inventory your workload software and architecture and identify components that need to be updated.
- **Identify update sources:** Identify news and update sources related to your workload components. As an example, you can subscribe to the [What’s New at AWS blog](https://aws.amazon.com/new/) for the products that match your workload component. You can subscribe to the RSS feed or manage your [email subscriptions](https://pages.awscloud.com/communication-preferences.html).
- **Define an update schedule:** Define a schedule to evaluate new services and features for your workload.
  - You can use [AWS Systems Manager Inventory](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-inventory.html) to collect operating system (OS), application, and instance metadata from your Amazon EC2 instances and quickly understand which instances are running the software and configurations required by your software policy and which instances need to be updated.
- **Assess the new update:** Understand how to update the components of your workload. Take advantage of agility in the cloud to quickly test how new features can improve your workload to gain performance efficiency.
- **Use automation:** Use automation for the update process to reduce the level of effort to deploy new features and limit errors caused by manual processes.
  - You can use [CI/CD](https://aws.amazon.com/blogs/devops/complete-ci-cd-with-aws-codecommit-aws-codebuild-aws-codedeploy-and-aws-codepipeline/) to automatically update AMIs, container images, and other artifacts related to your cloud application.
  - You can use tools such as [AWS Systems Manager Patch Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-patch.html) to automate the process of system updates, and schedule the activity using [AWS Systems Manager Maintenance Windows](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-maintenance.html).
- **Document the process:** Document your process for evaluating updates and new services. Provide your owners the time and space needed to research, test, experiment, and validate updates and new services. Refer back to the documented business requirements and KPIs to help prioritize which update will make a positive business impact.

## Resources
### Related Documents
- [AWS Blog](https://aws.amazon.com/blogs/)
- [What's New with AWS](https://aws.amazon.com/new/?ref=wellarchitected)
- [ Implementing up-to-date images with automated EC2 Image Builder pipelines ](https://aws.amazon.com/blogs/compute/implementing-up-to-date-images-with-automated-ec2-image-builder-pipelines/)
### Related Videos
- [AWS re:Inforce 2022 - Automating patch management and compliance using AWS](https://www.youtube.com/watch?v=gL3baXQJvc0)
- [ All Things Patch: AWS Systems Manager \$1 AWS Events ](https://www.youtube.com/watch?v=PhIiVsCEBu8)
### Related Examples
- [ Inventory and Patch Management ](https://mng.workshop.aws/ssm/use-case-labs/inventory_patch_management.html)
- [ One Observability Workshop ](https://catalog.workshops.aws/observability/en-US)
