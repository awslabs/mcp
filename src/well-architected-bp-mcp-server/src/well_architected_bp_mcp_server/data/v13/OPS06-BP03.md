---
id: "OPS06-BP03"
title: "Employ safe deployment strategies"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you mitigate deployment risks?"
risk_level: "Medium"
effort: "Medium"
---

# OPS06-BP03 Employ safe deployment strategies

## Desired Outcome
Your organization uses a continuous integration continuous delivery (CI/CD) system that provides capabilities for automating safe rollouts. Teams are required to use appropriate safe roll-out strategies.

## Anti-Patterns
- You deploy an unsuccessful change to all of production all at once. As a result, all customers are impacted simultaneously.
- A defect introduced in a simultaneous deployment to all systems requires an emergency release. Correcting it for all customers takes several days.
- Managing production release requires planning and participation of several teams. This puts constraints on your ability to frequently update features for your customers.
- You perform a mutable deployment by modifying your existing systems. After discovering that the change was unsuccessful, you are forced to modify the systems again to restore the old version, extending your time to recovery.

## Implementation Guidance
 Continuous-delivery failures can lead to reduced service availability and bad customer experiences. To maximize the rate of successful deployments, implement safety controls in the end-to-end release process to minimize deployment errors, with a goal of achieving zero deployment failures.

 **Customer example**

 AnyCompany Retail is on a mission to achieve minimal to zero downtime deployments, meaning that there's no perceivable impact to its users during deployments. To accomplish this, the company has established deployment patterns (see the following workflow diagram), such as rolling and blue/green deployments. All teams adopt one or more of these patterns in their CI/CD pipeline.

| CodeDeploy workflow for Amazon EC2 | CodeDeploy workflow for Amazon ECS | CodeDeploy workflow for Lambda |
| --- | --- | --- |
|  ![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/deployment-process-ec2.png)  |  ![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/deployment-process-ecs.png)  |  ![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/deployment-process-lambda.png)  |

## Implementation Steps
1.  Use an approval workflow to initiate the sequence of production roll-out steps upon promotion to production .

1.  Use an automated deployment system such as [AWS CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html). AWS CodeDeploy [deployment options](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps.html) include in-place deployments for EC2/On-Premises and blue/green deployments for EC2/On-Premises, AWS Lambda, and Amazon ECS (see the preceding workflow diagram).

   1.  Where applicable, [integrate AWS CodeDeploy with other AWS services](https://docs.aws.amazon.com/codedeploy/latest/userguide/integrations-aws.html) or [integrate AWS CodeDeploy with partner product and services](https://docs.aws.amazon.com/codedeploy/latest/userguide/integrations-partners.html).

1.  Use blue/green deployments for databases such as [Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/blue-green-deployments.html) and [Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/blue-green-deployments.html).

1.  [Monitor deployments](https://docs.aws.amazon.com/codedeploy/latest/userguide/monitoring.html) using Amazon CloudWatch, AWS CloudTrail, and Amazon Simple Notification Service (Amazon SNS) event notifications.

1.  Perform post-deployment automated testing including functional, security, regression, integration, and any load tests.

1.  [Troubleshoot](https://docs.aws.amazon.com/codedeploy/latest/userguide/troubleshooting.html) deployment issues.

## Resources
### Related Best Practices
- [OPS05-BP02 Test and validate changes](ops_dev_integ_test_val_chg.md)
- [OPS05-BP09 Make frequent, small, reversible changes](ops_dev_integ_freq_sm_rev_chg.md)
- [OPS05-BP10 Fully automate integration and deployment](ops_dev_integ_auto_integ_deploy.md)
### Related Documents
- [AWS Builders Library \$1 Automating safe, hands-off deployments \$1 Production deployments ](https://aws.amazon.com/builders-library/automating-safe-hands-off-deployments/?did=ba_card&trk=ba_card#Production_deployments)
- [AWS Builders Library \$1 My CI/CD pipeline is my release captain \$1 Safe, automatic production releases](https://aws.amazon.com/builders-library/cicd-pipeline/#Safe.2C_automatic_production_releases)
- [AWS Whitepaper \$1 Practicing Continuous Integration and Continuous Delivery on AWS \$1 Deployment methods](https://docs.aws.amazon.com/whitepapers/latest/practicing-continuous-integration-continuous-delivery/deployment-methods.html)
- [AWS CodeDeploy User Guide](https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html)
- [Working with deployment configurations in AWS CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html)
- [Set up an API Gateway canary release deployment ](https://docs.aws.amazon.com/apigateway/latest/developerguide/canary-release.html)
- [Amazon ECS Deployment Types](https://docs.aws.amazon.com/https://docs.aws.amazon.com/)
- [Fully Managed Blue/Green Deployments in Amazon Aurora and Amazon RDS](https://aws.amazon.com/blogs/aws/new-fully-managed-blue-green-deployments-in-amazon-aurora-and-amazon-rds/)
- [Blue/Green deployments with AWS Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.CNAMESwap.html)
### Related Videos
- [re:Invent 2020 \$1 Hands-off: Automating continuous delivery pipelines at Amazon](https://www.youtube.com/watch?v=ngnMj1zbMPY)
- [re:Invent 2019 \$1 Amazon's Approach to high-availability deployment](https://www.youtube.com/watch?v=bCgD2bX1LI4)
### Related Examples
- [Try a Sample Blue/Green Deployment in AWS CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/applications-create-blue-green.html)
- [ Workshop \$1 Building CI/CD pipelines for Lambda canary deployments using AWS CDK](https://catalog.workshops.aws/cdk-cicd-for-lambda-canary-deployment/en-US)
- [ Workshop \$1 Building your first DevOps Blue/Green pipeline with Amazon ECS ](https://catalog.us-east-1.prod.workshops.aws/workshops/4b59b9fb-48b6-461c-9377-907b2e33c9df/en-US)
- [ Workshop \$1 Building your first DevOps Blue/Green pipeline with Amazon EKS ](https://catalog.us-east-1.prod.workshops.aws/workshops/4eab6682-09b2-43e5-93d4-1f58fd6cff6e/en-US)
- [ Workshop \$1 EKS GitOps with ArgoCD ](https://catalog.workshops.aws/eksgitops-argocd-githubactions)
- [ Workshop \$1 CI/CD on AWS Workshop ](https://catalog.workshops.aws/cicdonaws/en-US)
- [ Implementing cross-account CI/CD with AWS SAM for container-based Lambda functions ](https://aws.amazon.com/blogs/compute/implementing-cross-account-cicd-with-aws-sam-for-container-based-lambda/)
