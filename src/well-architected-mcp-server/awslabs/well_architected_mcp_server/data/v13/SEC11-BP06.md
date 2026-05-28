---
id: "SEC11-BP06"
title: "Deploy software programmatically"
framework: "WAF"
domain: "Security"
capability: "How do you incorporate and validate the security properties of applications throughout the design, development, and deployment lifecycle?"
risk_level: "High"
---

# SEC11-BP06 Deploy software programmatically

## Desired Outcome
The version of your workload that you test is the version that you deploy, and the deployment is performed consistently every time. You externalize the configuration of your workload, which helps you deploy to different environments without changes. You employ cryptographic signing of your software packages to verify that nothing changes between environments.

## Anti-Patterns
- Manually deploying software into production.
- Manually performing changes to software to cater to different environments.

## Implementation Guidance
 To maintain a robust and reliable application infrastructure, implement secure and automated deployment practices. This practice involves removing persistent human access from production environments, using CI/CD tools for deployments, and externalizing environment-specific configuration data. By following this approach, you can enhance security, reduce the risk of human errors, and streamline the deployment process.

 You can build your AWS account structure to remove persistent human access from production environments. This practice minimizes the risk of unauthorized changes or accidental modifications, which improves the integrity of your production systems. Instead of direct human access, you can use CI/CD tools like [AWS CodeBuild](https://aws.amazon.com/codebuild/) and [AWS CodePipeline](https://aws.amazon.com/codepipeline/) to perform deployments. You can use these services to automate the build, test, and deployment processes, which reduces manual intervention and increases consistency.

 To further enhance security and traceability, you can sign your application packages after they have been tested and validate these signatures during deployment. To do so, use cryptographic tools such as [AWS Signer](https://docs.aws.amazon.com/signer/latest/developerguide/Welcome.html) or [AWS Key Management Service (AWS KMS)](https://aws.amazon.com/kms/). By signing and verifying packages, you can make sure that you deploy only authorized and validated code to your environments.

 Additionally, your team can architect your workload to obtain environment-specific configuration data from an external source, such as [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html). This practice separates the application code from the configuration data, which helps you manage and update configurations independently without modifying the application code itself.

 To streamline infrastructure provisioning and management, consider using infrastructure as code (IaC) tools like [AWS CloudFormation](https://aws.amazon.com/cloudformation/) or [AWS CDK](https://aws.amazon.com/cdk/). You can use these tools to define your infrastructure as code, which improves the consistency and repeatability of deployments across different environments.

 Consider canary deployments to validate the successful deployment of your software. Canary deployments involve rolling out changes to a subset of instances or users before deploying to the entire production environment. You can then monitor the impact of changes and roll back if necessary, which minimizes the risk of widespread issues.

 Follow the recommendations outlined in the [Organizing Your AWS Environment Using Multiple Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/organizing-your-aws-environment.html) whitepaper. This whitepaper provides guidance on separating environments (such as development, staging, and production) into distinct AWS accounts, which further enhances security and isolation.

## Implementation Steps
1.  **Set up AWS account structure**:
   - Follow the guidance in the [Organizing Your AWS Environment Using Multiple Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/organizing-your-aws-environment.html) whitepaper to create separate AWS accounts for different environments (for exampoe, development, staging, and production).
   - Configure appropriate access controls and permissions for each account to restrict direct human access to production environments.

1.  **Implement a CI/CD pipeline**:
   - Set up a CI/CD pipeline using services like [AWS CodeBuild](https://aws.amazon.com/codebuild/) and [AWS CodePipeline](https://aws.amazon.com/codepipeline/).
   - Configure the pipeline to automatically build, test, and deploy your application code to the respective environments.
   - Integrate code repositories with the CI/CD pipeline for version control and code management.

1.  **Sign and verify application packages**:
   - Use [AWS Signer](https://docs.aws.amazon.com/signer/latest/developerguide/Welcome.html) or [AWS Key Management Service (AWS KMS)](https://aws.amazon.com/kms/) to sign your application packages after they have been tested and validated.
   - Configure the deployment process to verify the signatures of the application packages before you deploy them to the target environments.

1.  **Externalize configuration data**:
   - Store environment-specific configuration data in [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html).
   - Modify your application code to retrieve configuration data from the Parameter Store during deployment or runtime.

1.  **Implement infrastructure as code (IaC)**:
   - Use IaC tools like [AWS CloudFormation](https://aws.amazon.com/cloudformation/) or [AWS CDK](https://aws.amazon.com/cdk/) to define and manage your infrastructure as code.
   - Create CloudFormation templates or CDK scripts to provision and configure the necessary AWS resources for your application.
   - Integrate IaC with your CI/CD pipeline to automatically deploy infrastructure changes alongside application code changes.

1.  **Implement canary deployments**:
   - Configure your deployment process to support canary deployments, where changes are rolled out to a subset of instances or users before you deploy them to the entire production environment.
   - Use services like [AWS CodeDeploy](https://aws.amazon.com/codedeploy/) or [AWS ECS](https://aws.amazon.com/ecs/) to manage canary deployments and monitor the impact of changes.
   - Implement rollback mechanisms to revert to the previous stable version if issues are detected during the canary deployment.

1.  **Monitor and audit**:
   - Set up monitoring and logging mechanisms to track deployments, application performance, and infrastructure changes.
   - Use services like [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) and [AWS CloudTrail](https://aws.amazon.com/cloudtrail/) to collect and analyze logs and metrics.
   - Implement auditing and compliance checks to verify adherence to security best practices and regulatory requirements.

1.  **Continuously improve:**
   - Regularly review and update your deployment practices, and incorporate feedback and lessons learned from previous deployments.
   - Automate as much of the deployment process as possible to reduce manual intervention and potential human errors.
   - Collaborate with cross-functional teams (for example, operations or security) to align and continuously improve deployment practices.

 By following these steps, you can implement secure and automated deployment practices in your AWS environment, which enhances security, reduces the risk of human errors, and streamlines the deployment process.

## Resources
### Related Best Practices
- [SEC11-BP02 Automate testing throughout the development and release lifecycle](sec_appsec_automate_testing_throughout_lifecycle.md)
- [DL.CI.2 Trigger builds automatically upon source code modifications](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.ci.2-trigger-builds-automatically-upon-source-code-modifications.html)
### Related Documents
- [Accelerate deployments on AWS with effective governance](https://aws.amazon.com/blogs/architecture/accelerate-deployments-on-aws-with-effective-governance/)
- [Automating safe, hands-off deployments](https://aws.amazon.com/builders-library/automating-safe-hands-off-deployments/)
- [Code signing using AWS Certificate Manager Private CA and AWS Key Management Service asymmetric keys](https://aws.amazon.com/blogs/security/code-signing-aws-certificate-manager-private-ca-aws-key-management-service-asymmetric-keys/)
- [Code Signing, a Trust and Integrity Control for AWS Lambda](https://aws.amazon.com/blogs/aws/new-code-signing-a-trust-and-integrity-control-for-aws-lambda/)
### Related Videos
- [Hands-off: Automating continuous delivery pipelines at Amazon](https://www.youtube.com/watch?v=ngnMj1zbMPY)
### Related Examples
- [Blue/Green deployments with AWS Fargate](https://catalog.us-east-1.prod.workshops.aws/workshops/954a35ee-c878-4c22-93ce-b30b25918d89/en-US)
