---
id: "REL08-BP02"
title: "Integrate functional testing as part of your deployment"
pillar: "Reliability"
risk_level: "HIGH"
capability: "How do you implement change?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_tracking_change_management_functional_testing.html"
---

# REL08-BP02 Integrate functional testing as part of your deployment

Use techniques such as unit tests and integration tests that
validate required functionality.

Unit testing is the process where you test the smallest functional
unit of code to validate its behavior. Integration testing seeks to
validate that each application feature works according to the
software requirements. While unit tests focus on testing part of an
application in isolation, integration tests consider side effects
(for example, the effect of data being changed through a mutation
operation). In either case, tests should be integrated into a
deployment pipeline, and if success criteria are not met, the
pipeline is halted or rolled back. These tests are run in a
pre-production environment, which is staged prior to production in
the pipeline.

You achieve the best outcomes when these tests are run automatically
as part of build and deployment actions. For instance, with AWS CodePipeline, developers commit changes to a source repository where
CodePipeline automatically detects the changes. The application is
built, and unit tests are run. After the unit tests have passed, the
built code is deployed to staging servers for testing. From the
staging server, CodePipeline runs more tests, such as integration or
load tests. Upon the successful completion of those tests,
CodePipeline deploys the tested and approved code to production
instances.

**Desired outcome:** You use
automation to perform unit and integration tests to validate that
your code behaves as expected. These tests are integrated into the
deployment process, and a test failure aborts the deployment.

**Common anti-patterns:**

- You ignore or bypass test failures and plans during the
deployment process in order to accelerate the deployment
timeline.
- You manually perform tests outside the deployment pipeline.
- You skip testing steps in the automation through manual
emergency workflows.
- You run automated tests in an environment that does not closely
resemble the production environment.
- You build a test suite that is insufficiently flexible and is
difficult to maintain, update, or scale as the application
evolves.

**Benefits of establishing this best
practice:** Automated testing during the deployment process
catches issues early, which reduces the risk of a release to
production with bugs or unexpected behavior. Unit tests validate the
code behaves as desired and API contracts are honored. Integration
tests validate that the system operates according to specified
requirements. These types of tests verify the intended working order
of components such as user interfaces, APIs, databases, and source
code.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Adopt a test-driven development (TDD) approach to writing
software, where you develop test cases to specify and validate
your code. To start, create test cases for each function. If the
test fails, you write new code to pass the test. This approach
helps you validate the expected result of each function. Run unit
tests and validate that they pass before you commit code to a
source code repository.

Implement both unit and integration tests as part of the build,
test, and deployment stages of the CI/CD pipeline. Automate
testing, and automatically initiate tests whenever a new version
of the application is ready to be deployed. If success criteria
are not met, the pipeline is halted or rolled back.

If the application is a web or mobile app, perform automated
integration testing on multiple desktop browsers or real devices.
This approach is particularly useful to validate the compatibility
and functionality of mobile apps across a diverse range of
devices.

### Implementation steps

- Write unit tests before you write functional code
(*test-driven development*, or TDD).
Establish code guidelines so that writing and running unit
tests are a non-functional coding requirement.
- Create a suite of automated integration tests that cover the
identified testable functionalities. These tests should
simulate user interactions and validate the expected
outcomes.
- Create the necessary test environment to run the integration
tests. This may include staging or pre-production
environments that closely mimic the production environment.
- Set up your source, build, test, and deploy stages using the
AWS CodePipeline console or AWS Command Line Interface
(CLI).
- Deploy the application once the code has been built and
tested. AWS CodeDeploy can deploy it to your staging
(testing) and production environments. These environments
may include Amazon EC2 instances, AWS Lambda functions, or
on-premises servers. The same deployment mechanism should be
used to deploy the application to all environments.
- Monitor the progress of your pipeline and the status of each
stage. Use quality checks to block the pipeline based on the
status of your tests. You can also receive notifications for
any pipeline stage failure or pipeline completion.
- Continually monitor the results of the tests, and look for
patterns, regressions or areas that require more attention.
Use this information to improve the test suite, identify
areas of the application that need more robust testing, and
optimize the deployment process.

## Resources

**Related best practices:**

- [REL07-BP04
Load test your workload](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_adapt_to_changes_load_tested_adapt.html)
- [REL08-BP03
Integrate resiliency testing as part of your deployment](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_tracking_change_management_resiliency_testing.html)
- [REL12-BP04
Test resiliency using chaos engineering](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_testing_resiliency_failure_injection_resiliency.html)

**Related documents:**

- [AWS Prescriptive Guidance: Test automation](https://docs.aws.amazon.com/prescriptive-guidance/latest/performance-engineering-aws/test-automation.html)
- [Continuous
Delivery and Continuous Integration](https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts-continuous-delivery-integration.html)
- [Indicators
for functional testing](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/indicators-for-functional-testing.html)
- [Monitoring
pipelines](https://docs.aws.amazon.com/codepipeline/latest/userguide/monitoring.html)
- [Use AWS CodePipeline with AWS CodeBuild to test code and run builds](https://docs.aws.amazon.com/codebuild/latest/userguide/how-to-create-pipeline.html)
- [AWS Device Farm](https://docs.aws.amazon.com/codepipeline/latest/userguide/action-reference-DeviceFarm.html)
