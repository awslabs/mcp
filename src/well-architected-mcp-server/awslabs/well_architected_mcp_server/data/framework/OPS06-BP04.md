---
id: "OPS06-BP04"
title: "Automate testing and rollback"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How do you mitigate deployment risks?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_auto_testing_and_rollback.html"
---

# OPS06-BP04 Automate testing and rollback

To increase the speed, reliability, and confidence of your deployment process, have a strategy for automated testing and rollback capabilities in pre-production and production environments. Automate testing when deploying to production to simulate human and system interactions that verify the changes being deployed. Automate rollback to revert back to a previous known good state quickly. The rollback should be initiated automatically on pre-defined conditions such as when the desired outcome of your change is not achieved or when the automated test fails. Automating these two activities improves your success rate for your deployments, minimizes recovery time, and reduces the potential impact to the business.

**Desired outcome:** Your automated tests and rollback strategies are integrated into your continuous integration, continuous delivery (CI/CD) pipeline. Your monitoring is able to validate against your success criteria and initiate automatic rollback upon failure. This minimizes any impact to end users and customers. For example, when all testing outcomes have been satisfied, you promote your code into the production environment where automated regression testing is initiated, leveraging the same test cases. If regression test results do not match expectations, then automated rollback is initiated in the pipeline workflow.

**Common anti-patterns:**

- Your systems are not architected in a way that allows them to be updated with smaller releases. As a result, you have difficulty in reversing those bulk changes during a failed deployment.
- Your deployment process consists of a series of manual steps. After you deploy changes to your workload, you start post-deployment testing. After testing, you realize that your workload is inoperable and customers are disconnected. You then begin rolling back to the previous version. All of these manual steps delay overall system recovery and cause a prolonged impact to your customers.
- You spent time developing automated test cases for functionality that is not frequently used in your application, minimizing the return on investment in your automated testing capability.
- Your release is comprised of application, infrastructure, patches and configuration updates that are independent from one another. However, you have a single CI/CD pipeline that delivers all changes at once. A failure in one component forces you to revert all changes, making your rollback complex and inefficient.
- Your team completes the coding work in sprint one and begins sprint two work, but your plan did not include testing until sprint three. As a result, automated tests revealed defects from sprint one that had to be resolved before testing of sprint two deliverables could be started and the entire release is delayed, devaluing your automated testing.
- Your automated regression test cases for the production release are complete, but you are not monitoring workload health. Since you have no visibility into whether or not the service has restarted, you are not sure if rollback is needed or if it has already occurred.

**Benefits of establishing this best
practice:** Automated testing increases the transparency of your testing process and your ability to cover more features in a shorter time period. By testing and validating changes in production, you are able to identify issues immediately. Improvement in consistency with automated testing tools allows for better detection of defects. By automatically rolling back to the previous version, the impact on your customers is minimized. Automated rollback ultimately inspires more confidence in your deployment capabilities by reducing business impact. Overall, these capabilities reduce time-to-delivery while ensuring quality.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Automate testing of deployed environments to confirm desired outcomes more quickly. Automate rollback to a previous known good state when pre-defined outcomes are not achieved to minimize recovery time and reduce errors caused by manual processes. Integrate testing tools with your pipeline workflow to consistently test and minimize manual inputs. Prioritize automating test cases, such as those that mitigate the greatest risks and need to be tested frequently with every change. Additionally, automate rollback based on specific conditions that are pre-defined in your test plan.

### Implementation steps

- Establish a testing lifecycle for your development lifecycle that defines each stage of the testing process from requirements planning to test case development, tool configuration, automated testing, and test case closure.

Create a workload-specific testing approach from your overall test strategy.
- Consider a continuous testing strategy where appropriate throughout the development lifecycle.

- Select automated tools for testing and rollback based on your business requirements and pipeline investments.
- Decide which test cases you wish to automate and which should be performed manually. These can be defined based on business value priority of the feature being tested. Align all team members to this plan and verify accountability for performing manual tests.

Apply automated testing capabilities to specific test cases that make sense for automation, such as repeatable or frequently run cases, those that require repetitive tasks, or those that are required across multiple configurations.
- Define test automation scripts as well as the success criteria in the automation tool so continued workflow automation can be initiated when specific cases fail.
- Define specific failure criteria for automated rollback.

- Prioritize test automation to drive consistent results with thorough test case development where complexity and human interaction have a higher risk of failure.
- Integrate your automated testing and rollback tools into your CI/CD pipeline.

Develop clear success criteria for your changes.
- Monitor and observe to detect these criteria and automatically reverse changes when specific rollback criteria are met.

- Perform different types of automated production testing, such as:

A/B testing to show results in comparison to the current version between two user testing groups.
- Canary testing that allows you to roll out your change to a subset of users before releasing it to all.
- Feature-flag testing which allows a single feature of the new version at a time to be flagged on and off from outside the application so that each new feature can be validated one at a time.
- Regression testing to verify new functionality with existing interrelated components.

- Monitor the operational aspects of the application, transactions, and interactions with other applications and components. Develop reports to show success of changes by workload so that you can identify what parts of the automation and workflow can be further optimized.

Develop test result reports that help you make quick decisions on whether or not rollback procedures should be invoked.
- Implement a strategy that allows for automated rollback based upon pre-defined failure conditions that result from one or more of your test methods.

- Develop your automated test cases to allow for reusability across future repeatable changes.

**Level of effort for the implementation plan:** Medium

## Resources

**Related best practices:**

- OPS06-BP01 Plan for unsuccessful changes
- OPS06-BP02 Test deployments

**Related documents:**

- [AWS Builders Library | Ensuring rollback safety during deployments](https://aws.amazon.com/builders-library/ensuring-rollback-safety-during-deployments/)
- [Redeploy
and rollback a deployment with AWS CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-rollback-and-redeploy.html)
- [8 best practices when automating your deployments with AWS CloudFormation](https://aws.amazon.com/blogs/infrastructure-and-automation/best-practices-automating-deployments-with-aws-cloudformation/)

**Related examples:**

- [Serverless UI testing using Selenium, AWS Lambda, AWS Fargate, and AWS Developer Tools](https://aws.amazon.com/blogs/devops/using-aws-codepipeline-aws-codebuild-and-aws-lambda-for-serverless-automated-ui-testing/)

**Related videos:**

- [re:Invent 2020 | Hands-off: Automating continuous delivery pipelines at Amazon](https://www.youtube.com/watch?v=ngnMj1zbMPY)
- [re:Invent 2019 | Amazon's Approach to high-availability deployment](https://www.youtube.com/watch?v=bCgD2bX1LI4)
