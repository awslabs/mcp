---
id: "REL08-BP05"
title: "Deploy changes with automation"
framework: "WAF"
domain: "Reliability"
capability: "How do you implement change?"
risk_level: "Medium"
---

# REL08-BP05 Deploy changes with automation

## Desired Outcome
You build automated deployment safety into the release process with extensive pre-production testing, automatic rollbacks, and staggered production deployments. This automation minimizes the potential impact on production caused by failed deployments, and developers no longer need to actively watch deployments to production.

## Anti-Patterns
- You perform manual changes.
- You skip steps in your automation through manual emergency workflows.
- You don't follow your established plans and processes in favor of accelerated timelines.
- You perform rapid follow-on deployments without allowing for bake time.

## Implementation Guidance
 Automate your deployment pipeline. Deployment pipelines allow you to invoke automated testing and detection of anomalies, and either halt the pipeline at a certain step before production deployment, or automatically roll back a change. An integral part of this is the adoption of the culture of [continuous integration and continuous delivery/deployment](https://en.wikipedia.org/wiki/CI/CD) (CI/CD), where a commit or code change passes through various automated stage gates from build and test stages to deployment on production environments.

 Although conventional wisdom suggests that you keep people in the loop for the most difficult operational procedures, we suggest that you automate the most difficult procedures for that very reason.

## Implementation Steps
 You can automate deployments to remove manual operations by following these steps:
- **Set up a code repository to store your code securely:** Use a hosted source code management system based on a popular technology such as Git to store your source code and infrastructure as code (IaC) configuration.
- **Configure a continuous integration service to compile your source code, run tests, and create deployment artifacts:** To set up a build project for this purpose, see [Getting started with AWS CodeBuild using the console](https://docs.aws.amazon.com/codebuild/latest/userguide/getting-started.html).
- **Set up a deployment service that automates application deployments and handles the complexity of application updates without reliance on error-prone manual deployments:** [AWS CodeDeploy](https://aws.amazon.com/codedeploy/) automates software deployments to a variety of compute services, such as Amazon EC2, [AWS Fargate](https://aws.amazon.com/fargate/), [AWS Lambda](https://aws.amazon.com/lambda), and your on-premise servers. To configure these steps, see [Getting started with CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/getting-started-codedeploy.html).
- **Set up a continuous delivery service that automates your release pipelines for quicker and more reliable application and infrastructure updates:** Consider using [AWS CodePipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/getting-started-codepipeline.html) to help you automate your release pipelines. For more detail, see [CodePipeline tutorials](https://docs.aws.amazon.com/codepipeline/latest/userguide/tutorials.html).

## Resources
### Related Best Practices
- [OPS05-BP04 Use build and deployment management systems](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_dev_integ_build_mgmt_sys.html)
- [OPS05-BP10 Fully automate integration and deployment](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_dev_integ_auto_integ_deploy.html)
- [OPS06-BP02 Test deployments](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_test_val_chg.html)
- [OPS06-BP04 Automate testing and rollback](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_auto_testing_and_rollback.html)
### Related Documents
- [Continuous Delivery of Nested AWS CloudFormation Stacks Using AWS CodePipeline](https://aws.amazon.com/blogs/devops/continuous-delivery-of-nested-aws-cloudformation-stacks-using-aws-codepipeline)
- [APN Partner: partners that can help you create automated deployment solutions](https://aws.amazon.com/partners/find/results/?keyword=devops)
- [AWS Marketplace: products that can be used to automate your deployments](https://aws.amazon.com/marketplace/search/results?searchTerms=DevOps)
- [Automate chat messages with webhooks.](https://docs.aws.amazon.com/chime/latest/ug/webhooks.html)
- [The Amazon Builders' Library: Ensuring rollback safety during deployments](https://aws.amazon.com/builders-library/ensuring-rollback-safety-during-deployments)
- [The Amazon Builders' Library: Going faster with continuous delivery](https://aws.amazon.com/builders-library/going-faster-with-continuous-delivery/)
- [What Is AWS CodePipeline?](https://docs.aws.amazon.com/codepipeline/latest/userguide/welcome.html)
- [What Is CodeDeploy?](https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html)
- [AWS Systems Manager Patch Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-patch.html)
- [What is Amazon SES?](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/Welcome.html)
- [What is Amazon Simple Notification Service?](https://docs.aws.amazon.com/sns/latest/dg/welcome.html)
### Related Videos
- [AWS Summit 2019: CI/CD on AWS](https://youtu.be/tQcF6SqWCoY)
