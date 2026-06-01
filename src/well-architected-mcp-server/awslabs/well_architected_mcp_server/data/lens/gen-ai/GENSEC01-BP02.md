---
id: "GENSEC01-BP02"
title: "Implement private network communication between foundation models and applications"
pillar: "Security"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec01-bp02.html"
---

# GENSEC01-BP02 Implement private network communication between foundation models and applications

Implementing a scoped down data perimeter on foundation model
endpoints helps reduce the surface-area of potential threat vectors
and encourages a zero-trust security architecture. This best
practice describes how to implement private network communications
for your generative AI workloads.

**Desired outcome:** When
implemented, this best practice reduces the risk of unauthorized
access to a foundation model endpoint. It also helps create a
process to grant least privileged access to authorized parties.

**Benefits of establishing this best
practice:**

- [Apply
security at all layers](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - Private network communications
facilitate an additional layer of security within your application.
- [Protect
data in transit and at rest](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - Using private networks instead
of the default public endpoints helps to protect data in transit,
especially when combined with encryption techniques.

**Level of risk exposed if this practice is
not established:** High

## Implementation guidance

Without private network communication between foundation model
endpoints and generative AI applications, access to these
endpoints would be available through the public internet,
increasing exposure. Implementing a private network between a
foundation model and a generative AI application requires full
control over application hosting and network traffic
configuration.

AWS PrivateLink supports a range of AWS generative AI managed
services, including Amazon Bedrock and the Amazon Q family of
services. AWS PrivateLink facilitates private network
communications for customers across the AWS network within
their own account. This capability enables customers to
maintain private network communication between generative AI
managed services and applications making the request without
using the public internet. AWS PrivateLink works for
self-managed services as well, like Amazon SageMaker AI.
Hosted inference endpoints in Amazon SageMaker AI can be
deployed in a Virtual Private Cloud (VPC). In addition to
network controls which help protect and secure infrastructure,
endpoints deployed in a VPC can be made private using AWS PrivateLink. AWS PrivateLink enables VPC instances to
communicate with service resources without the need for public
IP addresses, reducing potential threats from public internet
exposure.

In Amazon SageMaker AI HyperPod using both EKS and Slurm
orchestrators, deploy your clusters within a private VPC and
configure the necessary subnets and security groups to
restrict access. For EKS, place your EKS cluster and SageMaker AI
HyperPod cluster in the same VPC, using private subnets and
security groups that only allow required internal
communication. For Slurm, similarly, launch your HyperPod
cluster in a VPC with private networking, and isolate all
compute nodes and storage (such as FSx for Lustre) from the
public internet. In both orchestrators, you can use AWS PrivateLink (VPC Endpoint, VPCE) to securely connect to
SageMaker AI endpoints, Amazon S3, and other AWS services without
traversing the public internet.

Verify that foundation models have private network access to
supporting infrastructure as well, such as vector stores or
external tools for agents. Retrieval-augmented generation
workflows commonly access data from vector databases, and you
should provide this access over a private network connection.
The same is true for external tools or APIs that may be called
by an agent. Keeping these network connections private helps
reduce exposure to external threats.

### Implementation steps

- Determine the VPC you need to create a private endpoint
in.
- Select the service you wish to create a private route to
from your VPC.
- Configure the endpoint to allow least privilege access
for your services.

- Network access to the interface endpoint is controlled
using security groups and policy documents.

## Resources

**Related best practices:**

- [SEC05-BP01](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_network_protection_create_layers.html)
- [SEC05-BP02](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_network_protection_layered.html)

**Related documents:**

- [AWS Expert Paper on PrivateLink](https://docs.aws.amazon.com/whitepapers/latest/aws-privatelink/aws-privatelink.html)
- [Encryption
best practices for Amazon S3](https://docs.aws.amazon.com/prescriptive-guidance/latest/encryption-best-practices/s3.html)
- [Getting
started with Amazon EKS support in SageMaker AI HyperPod](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-eks-prerequisites.html)
- [Orchestrating
SageMaker AI HyperPod clusters with Slurm](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-slurm.html)

**Related examples:**

- [Use
AWS PrivateLink to Set Up Private Access to Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/use-aws-privatelink-to-set-up-private-access-to-amazon-bedrock/)
- [Overseeing
AI Risk in a Rapidly Changing Landscape](https://aws.amazon.com/blogs/enterprise-strategy/overseeing-ai-risk-in-a-rapidly-changing-landscape/)
