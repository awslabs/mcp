---
id: "REL02-BP04"
title: "Prefer hub-and-spoke topologies over many-to-many mesh"
pillar: "Reliability"
risk_level: "MEDIUM"
capability: "How do you plan your network topology?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology_prefer_hub_and_spoke.html"
---

# REL02-BP04 Prefer hub-and-spoke topologies over many-to-many mesh

When connecting multiple private networks, such as Virtual Private
Clouds (VPCs) and on-premises networks, opt for a hub-and-spoke
topology over a meshed one. Unlike meshed topologies, where each
network connects directly to the others and increases the complexity
and management overhead, the hub-and-spoke architecture centralizes
connections through a single hub. This centralization simplifies the
network structure and enhances its operability, scalability, and
control.

AWS Transit Gateway is a managed, scalable, and highly-available
service designed for construction of hub-and-spoke networks on AWS.
It serves as the central hub of your network that provides network
segmentation, centralized routing, and the simplified connection to
both cloud and on-premises environments. The following figure
illustrates how you can use AWS Transit Gateway to build your
hub-and-spoke topology.

**Desired outcome:** You have
connected your Virtual Private Clouds (VPCs) and on-premises
networks through a central hub. You configure your peering
connections through the hub, which acts as a highly scalable cloud
router. Routing is simplified because you do not have to work with
complex peering relationships. Traffic between networks is
encrypted, and you have the ability to isolate networks.

**Common anti-patterns:**

- You build complex network peering rules.
- You provide routes between networks that should not communicate
with one another (for example, separate workloads that have no
interdependencies).
- There is ineffective governance of the hub instance.

**Benefits of establishing this best
practice:** As the number of connected networks increases,
management and expansion of meshed connectivity becomes increasingly
challenging. A mesh architecture introduces additional challenges,
such as additional infrastructure components, configuration
requirements, and deployment considerations. The mesh also
introduces additional overhead to manage and monitor the data plane
and control plane components. You must think about how to provide
high availability of the mesh architecture, how to monitor the mesh
health and performance, and how to handle upgrades of the mesh
components.

A hub-and-spoke model, on the other hand, establishes centralized
traffic routing across multiple networks. It provides a simpler
approach to management and monitoring of the data plane and control
plane components.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Create a Network Services account if one does not exist. Place the
hub in the organization's Network Services account. This approach
allows the hub to be centrally managed by network engineers.

The hub of the hub-and-spoke model acts as a virtual router for
traffic flowing between your Virtual Private Clouds (VPCs) and
on-premises networks. This approach reduces network complexity and
makes it easier to troubleshoot networking issues.

Consider your network design, including the VPCs, AWS Direct Connect, and Site-to-Site VPN connections you want to
interconnect.

Consider using a separate subnet for each transit gateway VPC
attachment. For each subnet, use a small CIDR (for example
/28) so that you have more address space for
compute resources. Additionally, create one network ACL, and
associate it with all of the subnets that are associated with the
hub. Keep the network ACL open in both the inbound and outbound
directions.

Design and implement your routing tables such that routes are
provided only between networks that should communicate. Omit
routes between networks that should not communicate with one
another (for example, between separate workloads that have no
inter-dependencies).

### Implementation steps

- Plan your network. Determine which networks you want to
connect, and verify that they don't share overlapping CIDR
ranges.
- Create an AWS Transit Gateway and attach your VPCs.
- If needed, create VPN connections or Direct Connect
gateways, and associate them with the Transit Gateway.
- Define how traffic is routed between the connected VPCs and
other connections through configuration of your Transit
Gateway route tables.
- Use Amazon CloudWatch to monitor and adjust configurations
as necessary for performance and cost optimization.

## Resources

**Related best practices:**

- [REL02-BP03
Ensure IP subnet allocation accounts for expansion and
availability](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology_ip_subnet_allocation.html)
- [REL02-BP05
Enforce non-overlapping private IP address ranges in all
private address spaces where they are connected](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology_non_overlap_ip.html)

**Related documents:**

- [What
Is a Transit Gateway?](https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html)
- [Transit
gateway design best practices](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-best-design-practices.html)
- [Building
a Scalable and Secure Multi-VPC AWS Network
Infrastructure](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/welcome.html)
- [Building
a global network using AWS Transit Gateway Inter-Region
peering](https://aws.amazon.com/blogs/networking-and-content-delivery/building-a-global-network-using-aws-transit-gateway-inter-region-peering/)
- [Amazon Virtual Private Cloud Connectivity Options](https://docs.aws.amazon.com/whitepapers/latest/aws-vpc-connectivity-options/introduction.html)
- [APN
Partner: partners that can help plan your networking](https://aws.amazon.com/partners/find/results/?keyword=network)
- [AWS Marketplace for Network Infrastructure](https://aws.amazon.com/marketplace/b/2649366011)

**Related videos:**

- [AWS re:Invent 2023 - AWS networking foundations](https://www.youtube.com/watch?v=8nNurTFy-h4)
- [AWS re:Invent 2023 - Advanced VPC designs and new
capabilities](https://www.youtube.com/watch?v=cRdDCkbE4es)

**Related workshops:**

- [AWS Transit Gateway Workshop](https://catalog.workshops.aws/trasitgw/en-US)
