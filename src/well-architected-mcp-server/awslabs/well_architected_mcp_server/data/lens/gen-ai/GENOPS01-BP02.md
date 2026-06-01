---
id: "GENOPS01-BP02"
title: "Collect and monitor user feedback"
pillar: "Operational Excellence"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genops01-bp02.html"
---

# GENOPS01-BP02 Collect and monitor user feedback

Supplement model performance evaluation with direct feedback from
users. Implement continuous feedback loops to optimize application
performance and enhance user satisfaction. Systematically collect,
analyze, and act on user feedback to drive continuous improvement.
By integrating this approach, you can achieve higher operational
excellence and reliability, which keeps applications performant and
aligned with user expectations. This proactive strategy helps to
improve user satisfaction and foster a culture of ongoing
enhancement and innovation.

**Desired outcome:** When
implemented, this best practice improves the ability to surface
performance degradation issues with foundation models as they happen
without requiring ground truth data.

**Benefits this practice helps
achieve:**

- [Implement
observability for actionable insights](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - User feedback
from model responses to prompts can inform the efficacy of a
model, a prompt, or both in addressing a customer problem.
- [Anticipate
failure](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - Periodic review of the user feedback helps you
proactively identify deviations in subjective evaluation of a
model's performance. This is because foundation models are
inherently non-deterministic with a realistic chance
of failure.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Collect and monitor user feedback to establish continuous
improvement and optimization of your applications. User feedback
can be as simple as thumbs up or thumbs down, which you can
capture in your application and store in a database. This approach
helps detect issues early in the process and serves as a feedback
mechanism for prompt engineering.

Regularly review monitoring data, user feedback, and incident
reports related to your application's integration with Amazon Bedrock and Amazon SageMaker AI models. Use these insights to
identify potential improvements, such as optimizing data
pipelines, refining integration patterns, or exploring new model
capabilities.

[Amazon Q Business](https://aws.amazon.com/q/business/) offers tools to monitor and analyze user feedback.
These include an analytics dashboard in the console that provides
usage trends, user conversations, query trends, and user feedback.
Use these insights to optimize your application and identify areas
for improvement. Use the PutFeedback API action
to allow end users to provide feedback on chat responses. This
captures user sentiment and helps improve response quality.

Consult your organization’s AI policy document for guidance on how to use user feedback for workload improvements. Direct techniques for incorporating user feedback like reinforcement learning through human feedback may not be applicable for all workloads. Workload owners may be best positioned to identify the appropriate feedback incorporation strategy for a given task.

### Implementation steps

- For Amazon Q Business, set up user feedback collection.

Integrate simple feedback options within the application
- Use the PutFeedback API action
through AWS SDK for application integration
- Use Amazon Q Business usage trends and query analysis
- Consider storing feedback in Amazon DynamoDB for
scalable, low-latency storage
- Enable conversation logging to get more insights from
user interactions

Configure log delivery (choose between Amazon S3,
CloudWatch Logs, or Amazon Data Firehose)
- Set up filtering if you need to exclude sensitive
information
- Enable logging to start streaming conversation and
feedback data

- For Amazon Bedrock, set up user feedback collection.

Create an Amazon S3 bucket to store user feedback
- Develop a web form or API endpoint to collect user
feedback
- Create an AWS Lambda function to process incoming
feedback
- Set up an Amazon EventBridge rule to run the Lambda
function when new feedback is added to the S3 bucket

- Establish a regular review process.

Schedule periodic reviews of monitoring data, user
feedback, and incident reports
- Create an AWS Step Functions workflow to manage the
feedback processing pipeline
- Consider Amazon Bedrock's large language models to
analyze the feedback
- Consider Quick to create dashboards and
visualizations of the feedback data

- Implement and test improvements.

Identify optimizations in data pipelines, integration
patterns, or model capabilities
- Track KPIs before and after improvements
- Develop and deploy optimizations
- Validate improvements using A/B testing

## Resources

**Related best practices:**

- OPS04-BP03

**Related documents:**

- [Guidance
for Capturing and Analyzing Unstructured Customer Feedback on
AWS](https://aws.amazon.com/solutions/guidance/capturing-and-analyzing-unstructured-customer-feedback-on-aws/)
- [Build
an automated insight extraction framework for customer
feedback analysis with Amazon Bedrock and Quick](https://aws.amazon.com/blogs/machine-learning/build-an-automated-insight-extraction-framework-for-customer-feedback-analysis-with-amazon-bedrock-and-amazon-quicksight/)
- [Guidance
for Automated Customer Feedback Analysis with Amazon Bedrock](https://aws.amazon.com/solutions/guidance/automated-customer-feedback-analysis-with-amazon-bedrock/)

**Related examples:**

- [PutFeedback
- Amazon Q Business](https://docs.aws.amazon.com/amazonq/latest/api-reference/API_PutFeedback.html)
- [Configure
agent to request information from user to increase accuracy of
function prediction - Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-user-input.html)

**Related tools:**

- [Amazon Q Business](https://aws.amazon.com/q/business/)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [Amazon DynamoDB](https://aws.amazon.com/dynamodb/)
- [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/)
- [Quick](https://aws.amazon.com/quicksight/)
- [AWS Step Functions](https://aws.amazon.com/step-functions/)
