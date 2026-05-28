---
id: "SEC11-BP07"
title: "Regularly assess security properties of the pipelines"
framework: "WAF"
domain: "Security"
capability: "How do you incorporate and validate the security properties of applications throughout the design, development, and deployment lifecycle?"
risk_level: "High"
---

# SEC11-BP07 Regularly assess security properties of the pipelines

## Desired Outcome
The pipelines you use to build and deploy your software follow the same recommended practices as any other workload in your environment. The tests that you implement in your pipelines are not editable by the teams who use them. You give the pipelines only the permissions needed for the deployments they are doing using temporary credentials. You implement safeguards to prevent pipelines from deploying to the wrong environments. You configure your pipelines to emit state so that the integrity of your build environments can be validated.

## Anti-Patterns
- Security tests that can be bypassed by builders.
- Overly broad permissions for deployment pipelines.
- Pipelines not being configured to validate inputs.
- Not regularly reviewing the permissions associated with your CI/CD infrastructure.
- Use of long-term or hardcoded credentials.

## Implementation Guidance
 Your deployment pipelines are a critical component of your software development lifecycle and should follow the same security principles and practices as any other workload in your environment. This includes implementing proper access controls, validating inputs, and regularly reviewing and auditing the permissions associated with your CI/CD infrastructure.

 Verify that the teams responsible for building and deploying applications do not have the ability to edit or bypass the security tests and checks implemented in your pipelines. This separation of concerns helps maintain the integrity of your build and deployment processes.

 As a starting point, consider employing the [AWS Deployment Pipelines Reference Architecture](https://aws.amazon.com/blogs/aws/new_deployment_pipelines_reference_architecture_and_-reference_implementations/). This reference architecture provides a secure and scalable foundation for building your CI/CD pipelines on AWS.

 Additionally, you can use services like [AWS Identity and Access Management Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html) to generate least-privilege IAM policies for both your pipeline permissions and as a step in your pipeline to verify workload permissions. This helps verify that your pipelines and workloads have only the necessary permissions required for their specific functions, which reduces the risk of unauthorized access or actions.

## Implementation Steps
- Start with the [AWS Deployment Pipelines Reference Architecture](https://aws.amazon.com/blogs/aws/new_deployment_pipelines_reference_architecture_and_-reference_implementations/).
- Consider using [AWS IAM Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html) to programmatically generate least privilege IAM policies for the pipelines.
- Integrate your pipelines with monitoring and alerting so that you are notified of unexpected or abnormal activity, for AWS managed services [Amazon EventBridge](https://aws.amazon.com/eventbridge/) allows you to route data to targets such as [AWS Lambda](https://aws.amazon.com/lambda/) or [Amazon Simple Notification Service](https://aws.amazon.com/sns/) (Amazon SNS).

## Resources
### Related Documents
- [AWS Deployment Pipelines Reference Architecture](https://aws.amazon.com/blogs/aws/new_deployment_pipelines_reference_architecture_and_-reference_implementations/)
- [Monitoring AWS CodePipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/monitoring.html)
- [Security best practices for AWS CodePipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/security-best-practices.html)
### Related Examples
- [DevOps monitoring dashboard](https://github.com/aws-solutions/aws-devops-monitoring-dashboard) (GitHub)
