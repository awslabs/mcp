---
id: "OPS06-BP04"
title: "Automate testing and rollback"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you mitigate deployment risks?"
risk_level: "Medium"
effort: "Medium"
---

# OPS06-BP04 Automate testing and rollback

## Desired Outcome
Your automated tests and rollback strategies are integrated into your continuous integration, continuous delivery (CI/CD) pipeline. Your monitoring is able to validate against your success criteria and initiate automatic rollback upon failure. This minimizes any impact to end users and customers. For example, when all testing outcomes have been satisfied, you promote your code into the production environment where automated regression testing is initiated, leveraging the same test cases. If regression test results do not match expectations, then automated rollback is initiated in the pipeline workflow.

## Anti-Patterns
- Your systems are not architected in a way that allows them to be updated with smaller releases. As a result, you have difficulty in reversing those bulk changes during a failed deployment.
- Your deployment process consists of a series of manual steps. After you deploy changes to your workload, you start post-deployment testing. After testing, you realize that your workload is inoperable and customers are disconnected. You then begin rolling back to the previous version. All of these manual steps delay overall system recovery and cause a prolonged impact to your customers.
- You spent time developing automated test cases for functionality that is not frequently used in your application, minimizing the return on investment in your automated testing capability.
- Your release is comprised of application, infrastructure, patches and configuration updates that are independent from one another. However, you have a single CI/CD pipeline that delivers all changes at once. A failure in one component forces you to revert all changes, making your rollback complex and inefficient.
- Your team completes the coding work in sprint one and begins sprint two work, but your plan did not include testing until sprint three. As a result, automated tests revealed defects from sprint one that had to be resolved before testing of sprint two deliverables could be started and the entire release is delayed, devaluing your automated testing.
- Your automated regression test cases for the production release are complete, but you are not monitoring workload health. Since you have no visibility into whether or not the service has restarted, you are not sure if rollback is needed or if it has already occurred.

## Implementation Guidance
 Automate testing of deployed environments to confirm desired outcomes more quickly. Automate rollback to a previous known good state when pre-defined outcomes are not achieved to minimize recovery time and reduce errors caused by manual processes. Integrate testing tools with your pipeline workflow to consistently test and minimize manual inputs. Prioritize automating test cases, such as those that mitigate the greatest risks and need to be tested frequently with every change. Additionally, automate rollback based on specific conditions that are pre-defined in your test plan.

## Implementation Steps
1.  Establish a testing lifecycle for your development lifecycle that defines each stage of the testing process from requirements planning to test case development, tool configuration, automated testing, and test case closure.

   1.  Create a workload-specific testing approach from your overall test strategy.

   1.  Consider a continuous testing strategy where appropriate throughout the development lifecycle.

1.  Select automated tools for testing and rollback based on your business requirements and pipeline investments.

1.  Decide which test cases you wish to automate and which should be performed manually. These can be defined based on business value priority of the feature being tested. Align all team members to this plan and verify accountability for performing manual tests.

   1.  Apply automated testing capabilities to specific test cases that make sense for automation, such as repeatable or frequently run cases, those that require repetitive tasks, or those that are required across multiple configurations.

   1.  Define test automation scripts as well as the success criteria in the automation tool so continued workflow automation can be initiated when specific cases fail.

   1.  Define specific failure criteria for automated rollback.

1.  Prioritize test automation to drive consistent results with thorough test case development where complexity and human interaction have a higher risk of failure.

1.  Integrate your automated testing and rollback tools into your CI/CD pipeline.

   1.  Develop clear success criteria for your changes.

   1.  Monitor and observe to detect these criteria and automatically reverse changes when specific rollback criteria are met.

1.  Perform different types of automated production testing, such as:

   1.  A/B testing to show results in comparison to the current version between two user testing groups.

   1.  Canary testing that allows you to roll out your change to a subset of users before releasing it to all.

   1.  Feature-flag testing which allows a single feature of the new version at a time to be flagged on and off from outside the application so that each new feature can be validated one at a time.

   1.  Regression testing to verify new functionality with existing interrelated components.

1.  Monitor the operational aspects of the application, transactions, and interactions with other applications and components. Develop reports to show success of changes by workload so that you can identify what parts of the automation and workflow can be further optimized.

   1.  Develop test result reports that help you make quick decisions on whether or not rollback procedures should be invoked.

   1.  Implement a strategy that allows for automated rollback based upon pre-defined failure conditions that result from one or more of your test methods.

1.  Develop your automated test cases to allow for reusability across future repeatable changes.

## Resources
### Related Best Practices
- [OPS06-BP01 Plan for unsuccessful changes](ops_mit_deploy_risks_plan_for_unsucessful_changes.md)
- [OPS06-BP02 Test deployments](ops_mit_deploy_risks_test_val_chg.md)
### Related Documents
- [AWS Builders Library \$1 Ensuring rollback safety during deployments ](https://aws.amazon.com/builders-library/ensuring-rollback-safety-during-deployments/)
- [Redeploy and rollback a deployment with AWS CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-rollback-and-redeploy.html)
- [ 8 best practices when automating your deployments with AWS CloudFormation](https://aws.amazon.com/blogs/infrastructure-and-automation/best-practices-automating-deployments-with-aws-cloudformation/)
### Related Examples
- [ Serverless UI testing using Selenium, AWS Lambda, AWS Fargate, and AWS Developer Tools ](https://aws.amazon.com/blogs/devops/using-aws-codepipeline-aws-codebuild-and-aws-lambda-for-serverless-automated-ui-testing/)
### Related Videos
- [ re:Invent 2020 \$1 Hands-off: Automating continuous delivery pipelines at Amazon ](https://www.youtube.com/watch?v=ngnMj1zbMPY)
- [ re:Invent 2019 \$1 Amazon's Approach to high-availability deployment ](https://www.youtube.com/watch?v=bCgD2bX1LI4)
