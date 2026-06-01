---
id: "GENSEC01-BP01"
title: "Grant least privilege access to foundation model endpoints"
pillar: "Security"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec01-bp01.html"
---

# GENSEC01-BP01 Grant least privilege access to foundation model endpoints

Granting least privilege access to foundation model endpoints helps
limit unintended access and encourages a zero-trust security
framework. This best practice describes how to secure foundation
model endpoints associated with generative AI workloads.

**Desired outcome:** When
implemented, this best practice reduces the risk of unauthorized
access to a foundation model endpoint and helps create a process to
verify continuous adherence to least-privilege principle.

**Benefits of establishing this best
practice:**

- [Implement
a strong identity foundation](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - Least privilege access
permissions foster access to foundation model endpoints only for
authorized identities.
- [Apply
security at all layers](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-design.html) - Least privilege access permissions
on endpoints provides an identity-based layer of security,
regardless of the hosting paradigm.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Least privilege access is important to establish an
identity-based layer of security for generative AI workloads.
It helps verify that access to foundation model endpoints is
granted to authorized identities only while also helping
verify the data received matches the authorization boundary of
their role in their organization. Organization AI policy
documents should describe permission boundaries for AI
systems, related data stores, and other related components to
a generative AI workflow. This policy document should be
reviewed as part of a regular access review for AI workloads.

Amazon Bedrock, the Amazon Q family of applications, and
Amazon SageMaker AI feature endpoint APIs. Client applications
can access the APIs directly through SDKs, open source
frameworks or custom abstraction layers. You can use AWS Identity and Access Management to limit access to foundation
model endpoints to IAM roles. These roles should be granted
least privilege access and utilize session durations and
permissions boundaries to further control access.

[AWS PrivateLink](https://aws.amazon.com/privatelink/) connections can be established from
customer VPCs to Amazon generative AI services to further
secure communication. For endpoints hosted on an Amazon SageMaker AI inference endpoint, employ least privileged network
access to the inference endpoint, and verify that only the
systems allowed to perform inference on the endpoint can do
so.

Amazon SageMaker AI Hyperpod defines two primary roles: cluster
admin users and data scientist users.

Cluster admins are responsible for creating, configuring, and
managing HyperPod clusters, including setting up IAM roles,
orchestrator access (EKS or Slurm), and permissions for
cluster resources.

Data scientist users focus on running ML workloads, connecting
to clusters, and submitting jobs using the orchestrator CLI or
HyperPod CLI.

To help protect these roles following the best practice of
least privilege, each role should be granted only the
permissions necessary for their tasks. Cluster admins should
have granular IAM policies that allow them to manage clusters
and assign roles, but not unrestricted access to all AWS
resources. Data scientists should be assigned roles that
permit only the actions needed to submit and monitor jobs,
such as starting sessions or accessing specific S3 buckets.

HyperPod clusters themselves must assume roles with the
minimum required permissions (like
AmazonSageMaker AIHyperPodServiceRolePolicy)
to interact with AWS services such as Amazon S3, Amazon CloudWatch, and Amazon EC2 Systems Manager. Using IAM condition keys, RBAC (for
EKS), and resource tagging further refines access control,
verifying that both cluster admins and data scientists operate
within tightly scoped permissions and reducing the risk of
unauthorized access to foundation model endpoints and
sensitive resources.

Additionally, model access can be controlled at the
organization layer through other policy types such as service
control policies, resource control policies, session policies,
and permission boundaries. These policy types can provide ways
to block or restrict models your organization has not approved
in addition to services you may want to restrict by accounts,
Regions, organization, and the maximum permissible boundary
allowed for IAM users.

[Other
policy types](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html#security_iam_access-manage) offered by Amazon Q Developer manage
access through a subscription model. When provisioning
subscription-level access to a generative AI service, confirm
that the user needs that access and that subscription level
matches the required access level to the service.
Identity-based permissions and subscription-based service
access can be managed through single-sign-on (SSO) to
integrate with your enterprise identity provider.

### Implementation steps

- Create a custom policy document granting least-privilege
access to set of specific foundation model endpoints.

Limit access to specific resource ARNs and to a specific
set of actions.
- Consider defining conditions to further restrict the
allowable traffic, such as requests coming from a specific
VPC.

- Create an IAM role to be used by users or services to access
the endpoint and attach the custom policy to it. If more
permissions are needed for this role, attach the required
policies on as-needed bases.

Utilize permission boundaries at the role level to set the
maximum permissions that an identity-based policy can
grant.
- Conditions can be added to a role's trust policy to
further limit access to who can assume the role.

- Verify the new role for API calls to endpoints are protected
by this policy.

An example of an endpoint to protect might be a production
Amazon Bedrock endpoint servicing real-time inference
through a VPC-Hosted application.

- For a generative AI subscription based generative AI
application such as Amazon Q Developer, provision
subscription-level access matching the subscriber's business
needs.

## Resources

**Related best practices:**

- SEC02-BP01
- SEC02-BP02
- SEC02-BP06
- SEC03-BP01
- SEC03-BP02

**Related documents:**

- [AWS re:Invent 2023-Use new IAM Access Analyzer features on your
jouney to least privilege](https://www.youtube.com/watch?v=JpemUkU8INA)
- [Understanding
Subscriptions in Amazon Q Developer](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/q-admin-setup-subscribe-understanding.html)
- [Amazon Q Business Subscription Tiers and Index Types](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/tiers.html)
- [OWASP
Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [AWS Identity and Access Management for SageMaker AI HyperPod](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-prerequisites-iam.html)
- [IAM users for cluster admin](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-prerequisites-iam.html#sagemaker-hyperpod-prerequisites-iam-cluster-admin)
- [IAM users for scientists](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-prerequisites-iam.html#sagemaker-hyperpod-prerequisites-iam-cluster-user)
- [IAM
role for SageMaker AI HyperPod](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-prerequisites-iam.html#sagemaker-hyperpod-prerequisites-iam-role-for-hyperpod)

**Related examples:**

- [Techniques
for Writing Least Privilege IAM Policies](https://aws.amazon.com/blogs/security/techniques-for-writing-least-privilege-iam-policies/)
- [When
and Where to use IAM Permissions Boundaries](https://aws.amazon.com/blogs/security/when-and-where-to-use-iam-permissions-boundaries/)
- [Example
Permissions Boundaries](https://github.com/aws-samples/example-permissions-boundary)
- [Overseeing
AI Risk in a Rapidly Changing Landscape](https://aws.amazon.com/blogs/enterprise-strategy/overseeing-ai-risk-in-a-rapidly-changing-landscape/)
- [Configure
Amazon Q Business with AWS IAM Identity Center trusted
identity propagation](https://aws.amazon.com/blogs/machine-learning/configuring-amazon-q-business-with-aws-iam-identity-center-trusted-identity-propagation/)
