---
id: "OPS05-BP04"
title: "Use build and deployment management systems"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you reduce defects, ease remediation, and improve flow into production?"
risk_level: "Medium"
---

# OPS05-BP04 Use build and deployment management systems

## Desired Outcome
Your build and deployment management systems support your organization's continuous integration continuous delivery (CI/CD) system that provide capabilities for automating safe rollouts with the correct configurations.

## Anti-Patterns
- After compiling your code on your development system, you copy the executable onto your production systems and it fails to start. The local log files indicates that it has failed due to missing dependencies.
- You successfully build your application with new features in your development environment and provide the code to quality assurance (QA). It fails QA because it is missing static assets.
- On Friday, after much effort, you successfully built your application manually in your development environment including your newly coded features. On Monday, you are unable to repeat the steps that allowed you to successfully build your application.
- You perform the tests you have created for your new release. Then you spend the next week setting up a test environment and performing all the existing integration tests followed by the performance tests. The new code has an unacceptable performance impact and must be redeveloped and then retested.

## Implementation Guidance
 Build and deployment management systems are used to track and implement change, reduce errors caused by manual processes, and reduce the level of effort required for safe deployments. Fully automate the integration and deployment pipeline from code check-in through build, testing, deployment, and validation. This reduces lead time, decreases cost, encourages increased frequency of change, reduces the level of effort, and increases collaboration.

## Implementation Steps
![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/deployment-pipeline-tooling.png)

1.  Use a version control system to store and manage assets (such as documents, source code, and binary files).

1.  Use CodeBuild to compile your source code, runs unit tests, and produces artifacts that are ready to deploy.

1.  Use CodeDeploy as a deployment service that automates application deployments to [Amazon EC2](https://aws.amazon.com/ec2/) instances, on-premises instances, [serverless AWS Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html), or [Amazon ECS](https://aws.amazon.com/ecs/).

1.  Monitor your deployments.

## Resources
### Related Best Practices
- [OPS06-BP04 Automate testing and rollback](ops_mit_deploy_risks_auto_testing_and_rollback.md)
### Related Documents
- [AWS Developer Tools](https://aws.amazon.com/products/developer-tools/)
- [What is AWS CodeBuild?](https://docs.aws.amazon.com/codebuild/latest/userguide/welcome.html)
- [AWS CodeBuild](https://aws.amazon.com/codebuild/)
- [What is AWS CodeDeploy?](https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html)
### Related Videos
- [AWS re:Invent 2022 - AWS Well-Architected best practices for DevOps on AWS](https://youtu.be/hfXokRAyorA)
