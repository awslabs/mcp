---
id: "OPS06-BP02"
title: "Test deployments"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you mitigate deployment risks?"
risk_level: "High"
effort: "High"
---

# OPS06-BP02 Test deployments

## Desired Outcome
Your organization adopts a test-driven development culture that includes testing deployments. This ensures teams are focused on delivering business value rather than managing releases. Teams are engaged early upon identification of deployment risks to determine the appropriate course of mitigation.

## Anti-Patterns
- During production releases, untested deployments cause frequent issues that require troubleshooting and escalation.
- Your release contains infrastructure as code (IaC) that updates existing resources. You are unsure if the IaC runs successfully or causes impact to the resources.
- You deploy a new feature to your application. It doesn't work as intended and there is no visibility until it gets reported by impacted users.
- You update your certificates. You accidentally install the certificates to the wrong components, which goes undetected and impacts website visitors because a secure connection to the website can't be established.

## Implementation Guidance
 Testing your deployment process is as important as testing the changes that result from your deployment. This can be achieved by testing your deployment steps in a pre-production environment that mirrors production as closely as possible. Common issues, such as incomplete or incorrect deployment steps, or misconfigurations, can be caught as a result before going to production. In addition, you can test your recovery steps.

 **Customer example**

 As part of their continuous integration and continuous delivery (CI/CD) pipeline, AnyCompany Retail performs the defined steps needed to release infrastructure and software updates for its customers in a production-like environment. The pipeline is comprised of pre-checks to detect drift (detecting changes to resources performed outside of your IaC) in resources prior to deployment, as well as validate actions that the IaC takes upon its initiation. It validates deployment steps, like verifying that certain files and configurations are in place and services are in running states and are responding correctly to health checks on local host before re-registering with the load balancer. Additionally, all changes flag a number of automated tests, such as functional, security, regression, integration, and load tests.

## Implementation Steps
1.  Perform pre-install checks to mirror the pre-production environment to production.

   1.  Use [drift detection](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html) to detect when resources have been changed outside of AWS CloudFormation.

   1.  Use [change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html) to validate that the intent of a stack update matches the actions that AWS CloudFormation takes when the change set is initiated.

1.  This triggers a manual approval step in [AWS CodePipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/approvals.html) to authorize the deployment to the pre-production environment.

1.  Use deployment configurations such as [AWS CodeDeploy AppSpec](https://docs.aws.amazon.com/codedeploy/latest/userguide/application-specification-files.html) files to define deployment and validation steps.

1.  Where applicable, [integrate AWS CodeDeploy with other AWS services](https://docs.aws.amazon.com/codedeploy/latest/userguide/integrations-aws.html) or [integrate AWS CodeDeploy with partner product and services](https://docs.aws.amazon.com/codedeploy/latest/userguide/integrations-partners.html).

1.  [Monitor deployments](https://docs.aws.amazon.com/codedeploy/latest/userguide/monitoring.html) using Amazon CloudWatch, AWS CloudTrail, and Amazon SNS event notifications.

1.  Perform post-deployment automated testing, including functional, security, regression, integration, and load testing.

1.  [Troubleshoot](https://docs.aws.amazon.com/codedeploy/latest/userguide/troubleshooting.html) deployment issues.

1.  Successful validation of preceding steps should initiate a manual approval workflow to authorize deployment to production.

## Resources
### Related Best Practices
- [OPS05-BP02 Test and validate changes](ops_dev_integ_test_val_chg.md)
### Related Documents
- [AWS Builders' Library \$1 Automating safe, hands-off deployments \$1 Test Deployments ](https://aws.amazon.com/builders-library/automating-safe-hands-off-deployments/#Test_deployments_in_pre-production_environments)
- [AWS Whitepaper \$1 Practicing Continuous Integration and Continuous Delivery on AWS](https://docs.aws.amazon.com/whitepapers/latest/practicing-continuous-integration-continuous-delivery/testing-stages-in-continuous-integration-and-continuous-delivery.html)
- [ The Story of Apollo - Amazon's Deployment Engine ](https://www.allthingsdistributed.com/2014/11/apollo-amazon-deployment-engine.html)
- [How to test and debug AWS CodeDeploy locally before you ship your code](https://aws.amazon.com/blogs/devops/how-to-test-and-debug-aws-codedeploy-locally-before-you-ship-your-code/)
- [ Integrating Network Connectivity Testing with Infrastructure Deployment ](https://aws.amazon.com/blogs/networking-and-content-delivery/integrating-network-connectivity-testing-with-infrastructure-deployment/)
### Related Videos
- [ re:Invent 2020 \$1 Testing software and systems at Amazon ](https://www.youtube.com/watch?v=o1sc3cK9bMU)
### Related Examples
- [ Tutorial \$1 Deploy and Amazon ECS service with a validation test ](https://docs.aws.amazon.com/codedeploy/latest/userguide/tutorial-ecs-deployment-with-hooks.html)
