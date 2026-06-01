---
id: "GENREL02-BP01"
title: "Implement redundant network connections between model endpoints and supporting infrastructure"
pillar: "Reliability"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genrel02-bp01.html"
---

# GENREL02-BP01 Implement redundant network connections between model endpoints and supporting infrastructure

Implement network connection redundancy among components in your
generative AI application.

**Desired outcome:** When
implemented, this best practice improves the reliability of your
generative AI workload by reducing the likelihood of performance
degradation due to network issues.

**Benefits of establishing this best
practice:**
[Scale
horizontally to increase aggregate workload availability](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html)
across multiple components using a reliable network backbone.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Implement network connection redundancy between components in
your generative AI application to provide high availability
and fault tolerance. This involves creating multiple network
paths between critical components, using technologies such as
multi-AZ deployments, cross-Region connectivity, and
software-defined networking. Consider implementing load
balancers to distribute traffic across redundant connections
and automatically route around failures.

Deploy your generative AI application across multiple subnets
within a VPC. Use AWS PrivateLink or a similar network
technology to facilitate secure, private network
communications between VPC-hosted applications and other AWS
services. Use a multi-AZ architecture, with applications
deployed across at least two Availability Zones.

In addition to deploying applications with high availability,
deploy vector databases and agentic systems across multiple
Availability Zones as well. With vector database solutions
like Amazon OpenSearch Service Serverless, you can configure
your OpenSearch cluster deployment across multiple
Availability Zones, creating VPC Endpoints to have reliable
network connectivity to the cluster.

Similar considerations should be extended to agentic
workflows. On Amazon Bedrock, agent workflows make calls to
API endpoints and AWS Lambda functions. Consider deploying
these capabilities in a multi-AZ deployment as well.

For multi-Region deployments, implement a global traffic
management solution to route requests to the nearest available
endpoint. Use private network connections where possible to
improve security and reduce latency. Implement automatic
failover mechanisms to reroute traffic in case of network
issues. Continue deploying resources into VPCs, but consider
using one of the various multi-Region VPC communication
services to facilitate secure, reliable network connectivity
for your services and applications.

Use network configuration tools like VPC peering, AWS Transit Gateway, or Amazon VPC Lattice to connect your applications
and services in VPCs across Regions. Consider combining this
capability with Amazon Bedrock's cross-Region inference
capabilities for high availability network connectivity across
Regions.

### Implementation steps

- Identify critical network paths in your generative AI architecture:

Map dependencies between foundation models, databases, and other components
- Determine required bandwidth and latency for each connection

- Design redundant network topology:

Implement multi-AZ deployments for high availability
- Set up cross-Region connectivity for disaster recovery
- Configure load balancers for traffic distribution

- Implement private networking:

Use VPC peering or transit gateways for secure inter-component communication
- Set up VPN or direct connect for on-premises integration if required

- Configure automatic failover:

Implement health checks for network paths
- Set up automated failover mechanisms using DNS or overlay networking

- Test and validate redundancy:

Conduct failure simulations to verify failover effectiveness
- Perform regular failover drills to verify operational readiness

## Resources

**Related best practices:**

- REL02-BP01
- REL02-BP02

**Related documents:**

- [Securely Access Services Over AWS PrivateLink](https://docs.aws.amazon.com/whitepapers/latest/aws-privatelink/aws-privatelink.html)

**Related examples:**

- [Connect
to Amazon services using AWS PrivateLink in Amazon SageMaker AI](https://aws.amazon.com/blogs/machine-learning/connect-to-amazon-services-using-aws-privatelink-in-amazon-sagemaker/)
- [Use AWS PrivateLink to set up private access to Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/use-aws-privatelink-to-set-up-private-access-to-amazon-bedrock/)
- [Overseeing
AI Risk in a Rapidly Changing Landscape](https://aws.amazon.com/blogs/enterprise-strategy/overseeing-ai-risk-in-a-rapidly-changing-landscape/)
