---
id: "GENSEC01-BP03"
title: "Implement least privilege access permissions for foundation models accessing data stores"
pillar: "Security"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec01-bp03.html"
---

# GENSEC01-BP03 Implement least privilege access permissions for foundation models accessing data stores

Foundation models can aggregate and generate rich insights from data
they have been trained on or interact with from the APIs providing
inputs and outputs. It is important to treat generative AI systems
and their foundation models just as you would treat privileged users
when providing access to data. This best practice describes how to
provide generative AI APIs and services with appropriate access to
data.

**Desired outcome:** When
implemented, this best practice reduces the risk of accidentally
using unauthorized internal data when training and fine-tuning
foundation models. Additionally, a process will be implemented to
make sure that foundation models and workloads are granted only the
minimum necessary access to data, following the principle of least
privilege

**Benefits of establishing this best
practice:**

- [Implement
a strong identity foundation](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - least privilege access
permissions foster model access to only the required data.
- [Apply
security at all layers](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - least privilege data access for
foundation models provides an identity-based layer of data security.
- [Protect
data in transit and at rest](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - least privilege data access
for foundation models offers an added protection for data via access
controls.
- [Keep
people away from data](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - least privilege data access for
foundation offers helps prevent sweeping access to data for
foundation models.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Generative AI architecture patterns like Retrieval Augmented
Generation (RAG) or generative business intelligence (BI) use
external data to correlate with the foundation models output
and address user prompts. In many cases, a single vector
database may store data intended for several use cases, some
of which require additional authorizations to access. While
controls can be implemented at the foundation model layer,
this approach alone is insufficient. Addressing access to data
requires a multi-layered strategy. This is necessary not only
for RAG use cases but also for model customization and
pre-training processes.

When securing foundation models and protecting sensitive data,
customers should deploy data stores in a VPC with strong
access controls. Implementing zero-trust security principles
and enforcing least privilege access for users and
applications reduces the risks of unauthorized access. In the
software layer, customers should regularly update data stores
with the latest security patches to stay protected. Using
temporary, least privilege credentials for application access
reduces the risk of unauthorized access even if credentials
are unintentionally exposed. Keeping data store drivers and
SDKs up to date maintains compatibility and helps to mitigate
known issues. For the data layer, implementing granular
controls over foundational model elements allows for precise
management of sensitive information like personally
identifiable information (PII) using controls such as
guardrails in both Amazon Bedrock and Amazon SageMaker AI.

When using data for model training, especially in generative
AI scenarios, applying robust data obfuscation and
anonymization techniques can avoid unintended exposure of
sensitive data through model outputs. Vector databases
supported with services such as Amazon OpenSearch Service
offers efficient ways to sanitize and manage large-scale data
for AI workloads, improving both performance and security. At
the application layer, customers should regularly review and
refine Access Control Lists to stop unauthorized access to
data. Utilizing metadata filtering capabilities in vector
stores and knowledge bases can enable more granular access
control, allowing for data segregation based on user roles or
project requirements. For Identity and Access Management,
creating IAM roles with precision, such as attribute based
access controls, helps maintain the principle of least
privilege. Designing IAM policy documents with properly scoped
permissions can help stop improper access. Amazon Bedrock
Knowledge Bases can add a layer of abstraction to data access,
simplifying permission management across multiple data
sources.

When designing the overall architecture, aligning data access
permissions with data architecture decisions can lead to a
more coherent and manageable security posture. This approach
simplifies auditing and reduces the risk of misconfiguration.
Setting up a dedicated process for preparing training data and
using separate data stores and classification designed for
generative AI workloads, helps isolate sensitive data and
provides an additional layer of protection against
unauthorized access or misuse.

When using Amazon SageMaker AI HyperPod on both Amazon EKS and
Slurm, assign IAM roles to each workload or user that grant
only the specific permissions needed to access required data
stores, such as S3 buckets or databases.

For Amazon EKS, use Kubernetes service accounts mapped to IAM
roles (IRSA) to verify that pods have only the minimum access
needed.

In Slurm, configure IAM roles for each compute group or job,
and restrict permissions to only the necessary resources.

Regularly audit these roles and policies using tools like AWS
IAM Access Analyzer and update them as requirements evolve.
Apply resource-level policies on S3 buckets and databases to
further limit access, and use security groups to control
network communication between nodes and data sources. Verify
that both users and foundation models in SageMaker AI HyperPod
clusters can only access the data they are explicitly
authorized for, reducing the risk of accidental or malicious
data exposure.

### Implementation steps

- Classify data by its usage. Data can belong to several
usage patterns such as training, RAG, analytics, etc.
Classification of data helps to prevent and identify
misuse.
- Deploy a vector data store into a secure VPC, setting
appropriate access controls on the datastore for various
roles (for example, administrator, read-only, or
power-user). Consider extending role definitions to
encompass generative AI workloads (like
model-XX-RAG).
- Develop a data ingestion pipeline which obfuscates or
removes data that should not be processed by a
foundation model. Examples of this data might be
personal information. The scope of this data is informed
largely by the workload use case. Ingest this data from
your data lake into the vector store lake house.

A use case for a customer service assistant may require
access to handbooks, documentation, and customer service
material, not company financials, staff information or
HR policies.
- Sanitizing for prohibited material should happen before
the model accesses the data, at time of ingestion.

- Create least-privilege access policies for foundation
model and generated AI workloads. This Policy Document
should contain resource identifiers granting explicit
access to specific data in the vector datastore.
- Test access to data using curated prompts designed to
confirm models are not allowed to access sensitive
information.
- Similar principles apply for model training and model
customization workloads, though data used for model
training and model customization typically resides in a
data lake, separate from a compute engine.

## Resources

**Related best practices:**

- SEC03-BP01
- SEC03-BP02
- SEC07-BP01
- SEC07-BP02
- SEC08-BP04

**Related documents:**

- [AWS re:Invent 2023 - Use new IAM Access Analyzer features on your
journey to least privilege](https://www.youtube.com/watch?v=JpemUkU8INA)
- [AWS re:Inforce 2022 - Strategies for achieving least privilege
(IAM303)](https://www.youtube.com/watch?v=j57tBC6U4kk)
- [AWS Prescriptive Guidance: Creating a data strategy on AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-aws-data/aws-architecture.html)
- [Identity
and Access Management in Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ac.html)
- [Fine-Grained
Access Control in Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/fgac.html)
- [Amazon Bedrock Knowledge Bases Meta-Data Filtering](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-config.html)
- [Protect
Data at Rest Using Encryption](https://docs.aws.amazon.com/sagemaker/latest/dg/encryption-at-rest.html)
- [Data Protection in Amazon SageMaker AI](https://docs.aws.amazon.com/sagemaker/latest/dg/data-protection.html)

**Related examples:**

- [Techniques
for Writing Least Privilege IAM Policies](https://aws.amazon.com/blogs/security/techniques-for-writing-least-privilege-iam-policies/)
- [When
and Where to use IAM Permissions Boundaries](https://aws.amazon.com/blogs/security/when-and-where-to-use-iam-permissions-boundaries/)
- [Example
Permissions Boundaries](https://github.com/aws-samples/example-permissions-boundary)
- [Overseeing
AI Risk in a Rapidly Changing Landscape](https://aws.amazon.com/blogs/enterprise-strategy/overseeing-ai-risk-in-a-rapidly-changing-landscape/)
