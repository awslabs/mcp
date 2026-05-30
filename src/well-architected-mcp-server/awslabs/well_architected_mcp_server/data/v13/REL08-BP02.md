---
id: "REL08-BP02"
title: "Integrate functional testing as part of your deployment"
framework: "WAF"
domain: "Reliability"
capability: "How do you implement change?"
risk_level: "High"
---

# REL08-BP02 Integrate functional testing as part of your deployment

## Desired Outcome
You use automation to perform unit and integration tests to validate that your code behaves as expected. These tests are integrated into the deployment process, and a test failure aborts the deployment.

## Anti-Patterns
- You ignore or bypass test failures and plans during the deployment process in order to accelerate the deployment timeline.
- You manually perform tests outside the deployment pipeline.
- You skip testing steps in the automation through manual emergency workflows.
- You run automated tests in an environment that does not closely resemble the production environment.
- You build a test suite that is insufficiently flexible and is difficult to maintain, update, or scale as the application evolves.

## Implementation Guidance
 Adopt a test-driven development (TDD) approach to writing software, where you develop test cases to specify and validate your code. To start, create test cases for each function. If the test fails, you write new code to pass the test. This approach helps you validate the expected result of each function. Run unit tests and validate that they pass before you commit code to a source code repository.

 Implement both unit and integration tests as part of the build, test, and deployment stages of the CI/CD pipeline. Automate testing, and automatically initiate tests whenever a new version of the application is ready to be deployed. If success criteria are not met, the pipeline is halted or rolled back.

 If the application is a web or mobile app, perform automated integration testing on multiple desktop browsers or real devices. This approach is particularly useful to validate the compatibility and functionality of mobile apps across a diverse range of devices.

## Implementation Steps
1.  Write unit tests before you write functional code (*test-driven development*, or TDD). Establish code guidelines so that writing and running unit tests are a non-functional coding requirement.

1.  Create a suite of automated integration tests that cover the identified testable functionalities. These tests should simulate user interactions and validate the expected outcomes.

1.  Create the necessary test environment to run the integration tests. This may include staging or pre-production environments that closely mimic the production environment.

1.  Set up your source, build, test, and deploy stages using the AWS CodePipeline console or AWS Command Line Interface (CLI).

1.  Deploy the application once the code has been built and tested. AWS CodeDeploy can deploy it to your staging (testing) and production environments. These environments may include Amazon EC2 instances, AWS Lambda functions, or on-premises servers. The same deployment mechanism should be used to deploy the application to all environments.

1.  Monitor the progress of your pipeline and the status of each stage. Use quality checks to block the pipeline based on the status of your tests. You can also receive notifications for any pipeline stage failure or pipeline completion.

1.  Continually monitor the results of the tests, and look for patterns, regressions or areas that require more attention. Use this information to improve the test suite, identify areas of the application that need more robust testing, and optimize the deployment process.

## Resources
### Related Best Practices
- [REL07-BP04 Load test your workload](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_adapt_to_changes_load_tested_adapt.html)
- [REL08-BP03 Integrate resiliency testing as part of your deployment](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_tracking_change_management_resiliency_testing.html)
- [REL12-BP04 Test resiliency using chaos engineering](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_testing_resiliency_failure_injection_resiliency.html)
### Related Documents
- [AWS Prescriptive Guidance: Test automation](https://docs.aws.amazon.com/prescriptive-guidance/latest/performance-engineering-aws/test-automation.html)
- [Continuous Delivery and Continuous Integration](https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts-continuous-delivery-integration.html)
- [Indicators for functional testing](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/indicators-for-functional-testing.html)
- [Monitoring pipelines](https://docs.aws.amazon.com/codepipeline/latest/userguide/monitoring.html)
- [Use AWS CodePipeline with AWS CodeBuild to test code and run builds](https://docs.aws.amazon.com/codebuild/latest/userguide/how-to-create-pipeline.html)
- [AWS Device Farm](https://docs.aws.amazon.com/codepipeline/latest/userguide/action-reference-DeviceFarm.html)
