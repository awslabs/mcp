---
id: "GENOPS04-BP02"
title: "Follow GenAIOps practices to optimize the application lifecycle"
pillar: "Operational Excellence"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genops04-bp02.html"
---

# GENOPS04-BP02 Follow GenAIOps practices to optimize the application lifecycle

To optimize generative AI workloads, organizations should implement
[GenAIOps](https://genaiops.ai/), a best
practice that automates the development, deployment, and management
of models. This approach establishes CI/CD pipelines for training,
tuning, and deploying foundation models. GenAIOps enhances
operational efficiency, reduces time-to-market, and enables
consistent, high-quality model performance. It creates a robust,
automated framework that supports the entire generative AI project
lifecycle from development to production deployment. Through
GenAIOps, customers can achieve greater agility, improved model
reliability, and quick adaptation to changing business requirements,
driving innovation and competitive advantage.

**Desired outcome:** After
implementing GenAIOps, organizations can have a robust, automated
framework for managing the entire lifecycle of generative AI
workloads.

**Benefits of establishing this best
practice:**
[Safely
automate where possible](https://docs.aws.amazon.com/wellarchitected/latest/framework/oe-design-principles.html) - automate the lifecycle of your
foundation models.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

GenAIOps is a specialized subset of machine learning operations
(MLOps) that focuses on the processes and techniques for managing
and operationalizing foundation models in production environments.
Organizations can harness the power of foundation models while
reducing risks and optimizing their deployments. There are two
categories under GenAIOps: operationalizing foundation model
consumption and operationalizing foundation model training and
tuning. Common concerns across both categories include CI/CD,
prompt management, versioning of artifacts, model upgrades,
evaluation, and monitoring.

For operationalizing applications that consume foundation models,
the model-consuming applications will follow traditional DevOps
processes. Applications are often built using complex
orchestration patterns such as RAG and agents. Operationalizing
RAG applications involves the choice of vector database, indexing
pipelines, and retrieval strategies.

For operationalizing foundation model training and tuning, it is
essential to perform efficient training, tuning, and deployment of
foundation models using automation. Foundation model operations
(FMOps), which is the operationalization of foundation models, and
large language model operations (LLMOps), which is specifically
the operationalization of LLMs, fall under this category. This
involves model selection, continuous tuning and training of
models, experiment tracking, a central model registry, prompt
management and evaluation, and deployment of the models.

Amazon SageMaker AI Pipelines is a serverless workflow orchestration
service specifically designed for MLOps and LLMOps automation. Set
up SageMaker AI Pipelines to build, run, and monitor repeatable
end-to-end ML workflows for LLMs, from data preparation to model
deployment. The service can scale to run tens of thousands of
concurrent ML workflows in production, which is particularly
useful when working with resource-intensive LLMs. Self-managed
MLFlow or SageMaker AI MLFlow is well-suited for tracking
experiments, cataloging the models, approving them, and deploying
them to production.

Amazon Bedrock provides a managed RAG feature called Knowledge
Bases, which automates the indexing and ingestion into various
vector database options and orchestrates the retrieval process.
Amazon Bedrock Agents use the reasoning of foundation models,
APIs, and data to break down user requests, gather relevant
information, and efficiently complete tasks. Amazon Bedrock has
managed features for continued pretraining and finetuning of
foundation models.

### Implementation steps

- For SageMaker AI, implement pipelines.

Use SageMaker AI SDK to add steps which may include data
preparation, model training, model evaluation, and model
deployment
- Use SageMaker AI Processing to run evaluation scripts on the
trained model with SageMaker AI Clarify
- Automate testing with integration and performance tests.
Consider AWS Step Functions to orchestrate them
- Start the pipeline execution
- Use Amazon SageMaker AI Studio to view the pipeline's
progress
- Set up notifications for pipeline status updates using
Amazon CloudWatch Events
- Integrate this into the larger application's CI/CD
pipeline using AWS CodePipeline, AWS CodeBuild, and AWS CodeDeploy with Amazon SageMaker AI Projects

- Enable MLflow experiment tracking.

In Amazon SageMaker AI Studio, configure MLflow tracking
- Use MLflow to log parameters, metrics, and artifacts
during your model training process
- These will be automatically tracked and stored in your
SageMaker AI-managed MLflow server
- Use the MLflow UI in SageMaker AI Studio to analyze metrics
and artifacts to determine the best model iterations
- Register your best models in the MLflow Model Registry

- Use a version control system.

Use a Git compatible repository to manage code and
configurations effectively
- Set up SageMaker AI Model Registry to catalog and version
models

- Set up monitoring and logging.

Monitor real-time FM metrics with Amazon CloudWatch
- Centralize logging with Amazon CloudWatch Logs

- Create a feedback loop for continuous improvement.

Gather user feedback and model performance data
- Automate retraining and model updates based on new data

## Resources

**Related best practices:**

- [OPS05-BP10](https://docs.aws.amazon.com/wellarchitected/latest/framework/ops_dev_integ_auto_integ_deploy.html)
- [OPS05-BP07](https://docs.aws.amazon.com/wellarchitected/latest/framework/ops_dev_integ_code_quality.html)
- [OPS05-BP01](https://docs.aws.amazon.com/wellarchitected/latest/framework/ops_dev_integ_version_control.html)

**Related documents:**

- [LLM
experimentation at scale using Amazon SageMaker AI Pipelines and
MLflow | AWS Machine Learning Blog](https://aws.amazon.com/blogs/machine-learning/llm-experimentation-at-scale-using-amazon-sagemaker-pipelines-and-mlflow/)
- [Achieve
operational excellence with well-architected generative AI
solutions using Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/achieve-operational-excellence-with-well-architected-generative-ai-solutions-using-amazon-bedrock/)
- [MLOps
– Machine Learning Operations– Amazon Web Services](https://aws.amazon.com/sagemaker/mlops/)

**Related examples:**

- [Amazon SageMaker AI MLOps Workshop](https://github.com/aws-samples/amazon-sagemaker-mlops-workshop)
- [AWS MLOps Framework](https://aws.amazon.com/solutions/implementations/aws-mlops-framework/)
- [Amazon SageMaker AI MLOps Project Template](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-projects-templates-sm.html)

**Related tools:**

- [Amazon SageMaker AI Pipelines](https://aws.amazon.com/sagemaker-pipelines/)
- [AWS CodePipeline](https://aws.amazon.com/codepipeline/)
- [AWS CodeBuild](https://aws.amazon.com/codebuild/)
- [AWS CodeDeploy](https://aws.amazon.com/codedeploy/)
- [AWS Step Functions](https://aws.amazon.com/step-functions/)
- [Amazon CloudWatch](https://aws.amazon.com/cloudwatch)
- [Amazon Elastic Kubernetes Service (Amazon EKS)](https://aws.amazon.com/eks/)
