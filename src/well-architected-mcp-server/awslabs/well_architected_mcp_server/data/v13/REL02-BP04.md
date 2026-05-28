---
id: "REL02-BP04"
title: "Prefer hub-and-spoke topologies over many-to-many mesh"
framework: "WAF"
domain: "Reliability"
capability: "How do you plan your network topology?"
risk_level: "Medium"
---

# REL02-BP04 Prefer hub-and-spoke topologies over many-to-many mesh

## Desired Outcome
You have connected your Virtual Private Clouds (VPCs) and on-premises networks through a central hub. You configure your peering connections through the hub, which acts as a highly scalable cloud router. Routing is simplified because you do not have to work with complex peering relationships. Traffic between networks is encrypted, and you have the ability to isolate networks.

## Anti-Patterns
- You build complex network peering rules.
- You provide routes between networks that should not communicate with one another (for example, separate workloads that have no interdependencies).
- There is ineffective governance of the hub instance.

## Implementation Guidance
 Create a Network Services account if one does not exist. Place the hub in the organization's Network Services account. This approach allows the hub to be centrally managed by network engineers.

 The hub of the hub-and-spoke model acts as a virtual router for traffic flowing between your Virtual Private Clouds (VPCs) and on-premises networks. This approach reduces network complexity and makes it easier to troubleshoot networking issues.

 Consider your network design, including the VPCs, AWS Direct Connect, and Site-to-Site VPN connections you want to interconnect.

 Consider using a separate subnet for each transit gateway VPC attachment. For each subnet, use a small CIDR (for example /28) so that you have more address space for compute resources. Additionally, create one network ACL, and associate it with all of the subnets that are associated with the hub. Keep the network ACL open in both the inbound and outbound directions.

 Design and implement your routing tables such that routes are provided only between networks that should communicate. Omit routes between networks that should not communicate with one another (for example, between separate workloads that have no inter-dependencies).

## Implementation Steps
1.  Plan your network. Determine which networks you want to connect, and verify that they don't share overlapping CIDR ranges.

1.  Create an AWS Transit Gateway and attach your VPCs.

1.  If needed, create VPN connections or Direct Connect gateways, and associate them with the Transit Gateway.

1.  Define how traffic is routed between the connected VPCs and other connections through configuration of your Transit Gateway route tables.

1.  Use Amazon CloudWatch to monitor and adjust configurations as necessary for performance and cost optimization.

## Resources
### Related Best Practices
- [REL02-BP03 Ensure IP subnet allocation accounts for expansion and availability](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology_ip_subnet_allocation.html)
- [REL02-BP05 Enforce non-overlapping private IP address ranges in all private address spaces where they are connected](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology_non_overlap_ip.html)
### Related Documents
- [What Is a Transit Gateway?](https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html)
- [Transit gateway design best practices](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-best-design-practices.html)
- [Building a Scalable and Secure Multi-VPC AWS Network Infrastructure](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/welcome.html)
- [Building a global network using AWS Transit Gateway Inter-Region peering](https://aws.amazon.com/blogs/networking-and-content-delivery/building-a-global-network-using-aws-transit-gateway-inter-region-peering/)
- [Amazon Virtual Private Cloud Connectivity Options](https://docs.aws.amazon.com/whitepapers/latest/aws-vpc-connectivity-options/introduction.html)
- [APN Partner: partners that can help plan your networking](https://aws.amazon.com/partners/find/results/?keyword=network)
- [AWS Marketplace for Network Infrastructure](https://aws.amazon.com/marketplace/b/2649366011)
### Related Videos
- [AWS re:Invent 2023 - AWS networking foundations](https://www.youtube.com/watch?v=8nNurTFy-h4)
- [AWS re:Invent 2023 - Advanced VPC designs and new capabilities](https://www.youtube.com/watch?v=cRdDCkbE4es)
### Related Workshops
- [AWS Transit Gateway Workshop](https://catalog.workshops.aws/trasitgw/en-US)
